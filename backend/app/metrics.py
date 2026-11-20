from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy.orm import Session

from .jsonutil import dumps, loads
from .models import AnalyticsEvent, ChatMessage, Event, EventCall, EventMember, Profile, Query, QueryMatch, User, utcnow

TRACKED_EVENTS = frozenset(
    {
        "page_view",
        "login_google",
        "login_email",
        "register_email",
        "register_google",
        "join_link_opened",
        "join_event",
        "profile_completed",
        "query_posted",
        "query_matched",
        "call_accepted",
        "call_completed",
        "call_no_show",
        "chat_sent",
        "resume_uploaded",
        "connection_requested",
        "connection_accepted",
    }
)
PROP_KEYS = frozenset({"slug", "method", "path", "query_type", "status", "source"})
MAX_PROPS_BYTES = 2048
MAX_BATCH = 40


def pct(n: int, d: int) -> float:
    if d <= 0:
        return 0.0
    return round(100.0 * n / d, 1)


def _clip(value: object, limit: int = 120) -> str:
    text = str(value or "").strip()
    return text[:limit]


def track(
    db: Session,
    name: str,
    *,
    user_id: int | None = None,
    event_id: int | None = None,
    session_id: str = "",
    path: str = "",
    properties: dict | None = None,
) -> AnalyticsEvent | None:
    if name not in TRACKED_EVENTS:
        return None
    props = {key: _clip(properties[key]) for key in PROP_KEYS if properties and key in properties}
    blob = dumps(props)
    if len(blob.encode()) > MAX_PROPS_BYTES:
        blob = "{}"
    row = AnalyticsEvent(
        name=name,
        user_id=user_id,
        event_id=event_id,
        session_id=_clip(session_id, 64),
        path=_clip(path, 240),
        properties_json=blob,
    )
    db.add(row)
    return row


def ingest(db: Session, payload: dict, user_id: int | None) -> int:
    items = payload.get("events")
    if items is None and payload.get("name"):
        items = [payload]
    if not isinstance(items, list) or not items:
        return 0
    written = 0
    for item in items[:MAX_BATCH]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if name not in TRACKED_EVENTS:
            continue
        event_id = item.get("event_id")
        try:
            event_id = int(event_id) if event_id is not None else None
        except (TypeError, ValueError):
            event_id = None
        track(
            db,
            name,
            user_id=user_id,
            event_id=event_id,
            session_id=str(item.get("session_id") or ""),
            path=str(item.get("path") or ""),
            properties=item.get("properties") if isinstance(item.get("properties"), dict) else {},
        )
        written += 1
    return written


def _profile_completed(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if user is None or not (user.headline or "").strip():
        return False
    if profile is None:
        return False
    tags = loads(profile.skill_tags)
    return bool(tags)


def funnel_for(db: Session, event: Event) -> dict:
    members = db.query(EventMember).filter(EventMember.event_id == event.id, EventMember.accepted_join.is_(True)).all()
    profiles_completed = sum(1 for member in members if _profile_completed(db, member.user_id))
    queries = db.query(Query).filter(Query.event_id == event.id).all()
    qids = [q.id for q in queries]
    matched = db.query(QueryMatch.query_id).filter(QueryMatch.query_id.in_(qids)).distinct().count() if qids else 0
    calls = db.query(EventCall).filter(EventCall.query_id.in_(qids)).all() if qids else []
    accepted = [c for c in calls if c.status in {"scheduled", "completed"}]
    completed = [c for c in calls if c.status == "completed"]
    no_show = [c for c in calls if c.status == "no_show"]
    chat_n = db.query(ChatMessage).filter(ChatMessage.event_id == event.id).count()
    posters = (
        db.query(ChatMessage.author_id)
        .filter(ChatMessage.event_id == event.id, ChatMessage.author_id.isnot(None))
        .distinct()
        .count()
    )
    member_ids = [m.user_id for m in members]
    prior = (
        db.query(EventMember.user_id)
        .join(Event, Event.id == EventMember.event_id)
        .filter(
            Event.organizer_id == event.organizer_id,
            Event.id != event.id,
            EventMember.user_id.in_(member_ids),
            EventMember.accepted_join.is_(True),
        )
        .distinct()
        .count()
        if member_ids
        else 0
    )
    link_opens = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.name == "join_link_opened", AnalyticsEvent.event_id == event.id)
        .count()
    )
    google_logins = (
        db.query(AnalyticsEvent).filter(AnalyticsEvent.name == "login_google", AnalyticsEvent.event_id == event.id).count()
    )
    email_logins = (
        db.query(AnalyticsEvent).filter(AnalyticsEvent.name == "login_email", AnalyticsEvent.event_id == event.id).count()
    )
    joined = len(members)
    posted = len(queries)
    accepted_n = len(accepted)
    completed_n = len(completed)
    steps = [
        {"id": "link_opened", "label": "Join link opened", "count": link_opens or joined},
        {"id": "joined", "label": "Joined event", "count": joined},
        {"id": "profile", "label": "Profile completed", "count": profiles_completed},
        {"id": "query", "label": "Queries posted", "count": posted},
        {"id": "matched", "label": "Queries matched", "count": matched},
        {"id": "accepted", "label": "Calls accepted", "count": accepted_n},
        {"id": "completed", "label": "Calls completed", "count": completed_n},
    ]
    for i, step in enumerate(steps):
        prev = steps[i - 1]["count"] if i else max(step["count"], 1)
        step["conversion_from_prev_pct"] = pct(step["count"], prev)
        step["conversion_from_join_pct"] = pct(step["count"], joined)
    drop = None
    worst = 101.0
    for i in range(1, len(steps)):
        rate = steps[i]["conversion_from_prev_pct"]
        if steps[i - 1]["count"] > 0 and rate < worst:
            worst = rate
            drop = {
                "from": steps[i - 1]["id"],
                "to": steps[i]["id"],
                "from_label": steps[i - 1]["label"],
                "to_label": steps[i]["label"],
                "conversion_pct": rate,
            }
    insights = _insights(
        joined=joined,
        profiles_completed=profiles_completed,
        posted=posted,
        matched=matched,
        accepted_n=accepted_n,
        completed_n=completed_n,
        chat_n=chat_n,
        prior=prior,
        google_logins=google_logins,
        email_logins=email_logins,
        no_show=len(no_show),
        drop=drop,
    )
    return {
        "profiles_completed": profiles_completed,
        "profiles_completed_pct": round(100 * profiles_completed / max(joined, 1)),
        "chat_messages": chat_n,
        "unique_posters": posters,
        "queries_posted": posted,
        "queries_matched": matched,
        "calls_accepted": accepted_n,
        "calls_completed": completed_n,
        "calls_no_show": len(no_show),
        "repeat_attendees": prior,
        "member_count": joined,
        "join_link_opens": link_opens,
        "match_rate_pct": pct(matched, posted),
        "accept_rate_pct": pct(accepted_n, matched),
        "complete_rate_pct": pct(completed_n, accepted_n),
        "login_methods": {"google": google_logins, "email": email_logins},
        "funnel": steps,
        "drop_off": drop,
        "insights": insights,
    }


def _insights(
    *,
    joined: int,
    profiles_completed: int,
    posted: int,
    matched: int,
    accepted_n: int,
    completed_n: int,
    chat_n: int,
    prior: int,
    google_logins: int,
    email_logins: int,
    no_show: int,
    drop: dict | None,
) -> list[dict]:
    out: list[dict] = []
    profile_pct = pct(profiles_completed, joined)
    if joined and profile_pct < 50:
        out.append(
            {
                "severity": "warn",
                "text": f"Only {profile_pct}% of attendees finished a portable profile. The feed will match on thin tags.",
            }
        )
    if posted and pct(matched, posted) >= 50 and pct(accepted_n, matched) < 25:
        out.append(
            {
                "severity": "warn",
                "text": "Matches are landing, but people are not taking the 5-minute slot. Tighten the ask or pre-fill a slot.",
            }
        )
    if accepted_n and pct(completed_n, accepted_n) < 50:
        out.append(
            {
                "severity": "warn",
                "text": f"Only {pct(completed_n, accepted_n)}% of accepted calls completed ({no_show} no-shows). Send the Jitsi link at join time.",
            }
        )
    if joined and posted == 0:
        out.append({"severity": "warn", "text": "The room joined but nobody posted a query. Pin an example skill ask."})
    if chat_n == 0:
        out.append({"severity": "info", "text": "Chat is unused. A recap prompt in the last hour of the event usually moves this."})
    if prior == 0:
        out.append({"severity": "info", "text": "No repeat attendees yet — the graph does not compound until event #2."})
    if google_logins + email_logins:
        gshare = pct(google_logins, google_logins + email_logins)
        out.append({"severity": "ok", "text": f"Sign-in mix: {gshare}% Google / {100 - gshare}% email."})
    if drop and drop["conversion_pct"] < 40:
        out.append(
            {
                "severity": "warn",
                "text": f"Biggest drop-off: {drop['from_label']} → {drop['to_label']} ({drop['conversion_pct']}% converted).",
            }
        )
    if not out:
        out.append({"severity": "ok", "text": "Funnel looks healthy. Watch complete-rate and repeats next."})
    return out


def activity(db: Session, days: int = 14, event_id: int | None = None) -> dict:
    since = utcnow() - timedelta(days=days)
    q = db.query(AnalyticsEvent).filter(AnalyticsEvent.created_at >= since)
    if event_id is not None:
        q = q.filter((AnalyticsEvent.event_id == event_id) | (AnalyticsEvent.event_id.is_(None)))
    rows = q.all()
    by_day: dict[str, Counter] = defaultdict(Counter)
    by_name: Counter = Counter()
    pages: Counter = Counter()
    for row in rows:
        day = row.created_at.date().isoformat() if row.created_at else "unknown"
        by_day[day][row.name] += 1
        by_name[row.name] += 1
        if row.name == "page_view" and row.path:
            pages[row.path] += 1
    series = [{"day": day, "events": dict(counts), "total": sum(counts.values())} for day, counts in sorted(by_day.items())]
    return {
        "days": days,
        "totals": dict(by_name),
        "by_day": series,
        "top_pages": pages.most_common(8),
        "tracked_event_names": sorted(TRACKED_EVENTS),
    }
