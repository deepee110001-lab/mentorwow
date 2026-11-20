from sqlalchemy.orm import Session

from .ai import match_query
from .config import INCOMING_PENDING_LIMIT
from .jsonutil import loads
from .models import Event, EventMember, Profile, Query, QueryMatch, User, utcnow
from .notify import notify
from .privacy import pending_incoming_count


def matchable_members(db: Session, event: Event, author_id: int) -> list[dict]:
    rows = (
        db.query(EventMember, User, Profile)
        .join(User, User.id == EventMember.user_id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .filter(EventMember.event_id == event.id, EventMember.accepted_join.is_(True))
        .all()
    )
    members = []
    for member, user, profile in rows:
        if user.id == author_id:
            continue
        if member.attendance_visibility != "visible":
            continue
        if pending_incoming_count(db, user.id) >= INCOMING_PENDING_LIMIT:
            continue
        members.append(
            {
                "user_id": user.id,
                "headline": user.headline,
                "skill_tags": loads(profile.skill_tags) if profile else [],
                "can_advise_on": loads(profile.can_advise_on) if profile else [],
                "open_to_collaborate_on": loads(profile.open_to_collaborate_on) if profile else [],
            }
        )
    return members


def create_matches(db: Session, query: Query, event: Event) -> list[QueryMatch]:
    members = matchable_members(db, event, query.author_id)
    payload = {"id": query.id, "type": query.type, "body": query.body, "author_id": query.author_id}
    picked = match_query(payload, members)
    seen: set[int] = set()
    created: list[QueryMatch] = []
    for row in picked:
        uid = int(row["user_id"])
        if uid in seen or uid == query.author_id:
            continue
        if pending_incoming_count(db, uid) >= INCOMING_PENDING_LIMIT:
            continue
        seen.add(uid)
        match = QueryMatch(
            query_id=query.id,
            matched_user_id=uid,
            notified_at=utcnow(),
            response="pending",
            reason=row.get("reason") or "",
        )
        db.add(match)
        created.append(match)
        if len(created) >= 5:
            break
    db.flush()
    author = db.query(User).filter(User.id == query.author_id).one()
    for match in created:
        notify(
            db,
            match.matched_user_id,
            f"{author.handle} asked for 5 min",
            f"{query.type}: {query.body}",
            f"/e/{event.slug}/feed",
        )
    return created
