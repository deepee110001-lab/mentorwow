import csv
import io
import re
import secrets
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import APP_URL, ORGANIZER_EMAIL, PILOT_GATE
from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..jsonutil import loads
from ..metrics import activity, funnel_for
from ..models import Event, EventMember, Profile, User, utcnow
from ..notify import send_email_stub
from ..privacy import audit, refresh_status
from .events import event_out

router = APIRouter(prefix="/api", tags=["organizer"])


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:60] or "event"


def require_org_event(db: Session, event_id: int, user: User) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your event")
    refresh_status(event)
    return event


def metrics_for(db: Session, event: Event) -> dict:
    data = funnel_for(db, event)
    members = db.query(EventMember).filter(EventMember.event_id == event.id, EventMember.accepted_join.is_(True)).all()
    visible = [m for m in members if m.attendance_visibility == "visible"]
    skills: Counter = Counter()
    advise: Counter = Counter()
    collab: Counter = Counter()
    for member in visible:
        profile = db.query(Profile).filter(Profile.user_id == member.user_id).first()
        if not profile:
            continue
        skills.update(loads(profile.skill_tags))
        advise.update(loads(profile.can_advise_on))
        collab.update(loads(profile.open_to_collaborate_on))
    data["group_strengths"] = {
        "skill_tags": skills.most_common(8),
        "can_advise_on": advise.most_common(8),
        "open_to_collaborate_on": collab.most_common(8),
    }
    data["activity"] = activity(db, days=14, event_id=event.id)
    return data


@router.get("/organizer/events")
def list_events(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = db.query(Event).filter(Event.organizer_id == current.id).order_by(Event.created_at.desc()).all()
    return [event_out(row) for row in rows]


@router.post("/organizer/events")
def create_event(payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    starts = datetime.fromisoformat(payload["starts_at"].replace("Z", "+00:00"))
    ends = datetime.fromisoformat(payload["ends_at"].replace("Z", "+00:00"))
    slug = slugify(name)
    if db.query(Event).filter(Event.slug == slug).first():
        slug = f"{slug}-{secrets.token_hex(2)}"
    event = Event(
        organizer_id=current.id,
        name=name,
        slug=slug,
        join_link_token=secrets.token_urlsafe(12),
        starts_at=starts,
        ends_at=ends,
        chat_opens_at=starts,
        chat_closes_at=ends + timedelta(hours=24),
        feed_closes_at=ends + timedelta(days=7),
        status="live",
    )
    db.add(event)
    db.flush()
    db.add(
        EventMember(
            event_id=event.id,
            user_id=current.id,
            accepted_join=True,
            attendance_visibility="visible",
        )
    )
    audit(db, current.id, "create_event", "event", str(event.id), {"name": name})
    db.commit()
    db.refresh(event)
    return event_out(event)


@router.get("/organizer/events/{event_id}")
def dashboard(event_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = require_org_event(db, event_id, current)
    data = event_out(event)
    data["join_url"] = f"{APP_URL}/join/{event.join_link_token}"
    data["metrics"] = metrics_for(db, event)
    return data


@router.post("/organizer/events/{event_id}/close-chat")
def close_chat(event_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = require_org_event(db, event_id, current)
    event.chat_closes_at = utcnow()
    event.status = "chat_closed"
    db.commit()
    return event_out(event)


@router.post("/organizer/events/{event_id}/close-feed")
def close_feed(event_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = require_org_event(db, event_id, current)
    event.feed_closes_at = utcnow()
    event.status = "feed_closed"
    db.commit()
    return event_out(event)


@router.get("/organizer/events/{event_id}/csv")
def attendees_csv(event_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = require_org_event(db, event_id, current)
    members = db.query(EventMember).filter(EventMember.event_id == event.id).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["handle", "email", "headline", "attendance_visibility", "resume_visible"])
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).one()
        writer.writerow(
            [user.handle, user.email, user.headline, member.attendance_visibility, member.resume_visible_this_event]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={event.slug}-attendees.csv"},
    )


@router.post("/organizer/events/{event_id}/ask-event-2")
def ask_event_2(event_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = require_org_event(db, event_id, current)
    send_email_stub(current.id, f"Ask for event #2: {event.name}", "Validation signal", "")
    audit(db, current.id, "ask_event_2", "event", str(event.id), {})
    db.commit()
    return {"ok": True}


@router.get("/pilot/metrics")
def pilot_metrics(gate: str | None = None, db: Session = Depends(get_db), current: User | None = Depends(get_optional_user)):
    admin = bool(current and current.email.lower() == ORGANIZER_EMAIL)
    if not admin and gate != PILOT_GATE:
        raise HTTPException(status_code=403, detail="Pilot metrics are gated")
    events = db.query(Event).all()
    funnel = {
        "profiles_completed": 0,
        "chat_messages": 0,
        "queries_posted": 0,
        "queries_matched": 0,
        "calls_accepted": 0,
        "calls_completed": 0,
        "repeat_attendees": 0,
        "member_count": 0,
        "calls_no_show": 0,
        "events": [],
    }
    insights: list[dict] = []
    for event in events:
        m = metrics_for(db, event)
        for key in (
            "profiles_completed",
            "chat_messages",
            "queries_posted",
            "queries_matched",
            "calls_accepted",
            "calls_completed",
            "repeat_attendees",
            "member_count",
            "calls_no_show",
        ):
            funnel[key] += m.get(key, 0)
        insights.extend(m.get("insights") or [])
        funnel["events"].append({"name": event.name, "slug": event.slug, **m})
    posted = funnel["queries_posted"]
    matched = funnel["queries_matched"]
    accepted = funnel["calls_accepted"]
    completed = funnel["calls_completed"]
    members = funnel["member_count"]
    funnel["profiles_completed_pct"] = round(100 * funnel["profiles_completed"] / max(members, 1))
    funnel["match_rate_pct"] = round(100.0 * matched / posted, 1) if posted else 0.0
    funnel["accept_rate_pct"] = round(100.0 * accepted / matched, 1) if matched else 0.0
    funnel["complete_rate_pct"] = round(100.0 * completed / accepted, 1) if accepted else 0.0
    funnel["insights"] = insights[:8]
    funnel["activity"] = activity(db, days=14)
    funnel["funnel"] = [
        {"id": "joined", "label": "Joined event", "count": members, "conversion_from_prev_pct": 100.0, "conversion_from_join_pct": 100.0},
        {"id": "profile", "label": "Profile completed", "count": funnel["profiles_completed"], "conversion_from_prev_pct": funnel["profiles_completed_pct"], "conversion_from_join_pct": funnel["profiles_completed_pct"]},
        {"id": "query", "label": "Queries posted", "count": posted, "conversion_from_prev_pct": round(100.0 * posted / max(members, 1), 1), "conversion_from_join_pct": round(100.0 * posted / max(members, 1), 1)},
        {"id": "matched", "label": "Queries matched", "count": matched, "conversion_from_prev_pct": funnel["match_rate_pct"], "conversion_from_join_pct": round(100.0 * matched / max(members, 1), 1)},
        {"id": "accepted", "label": "Calls accepted", "count": accepted, "conversion_from_prev_pct": funnel["accept_rate_pct"], "conversion_from_join_pct": round(100.0 * accepted / max(members, 1), 1)},
        {"id": "completed", "label": "Calls completed", "count": completed, "conversion_from_prev_pct": funnel["complete_rate_pct"], "conversion_from_join_pct": round(100.0 * completed / max(members, 1), 1)},
    ]
    return funnel
