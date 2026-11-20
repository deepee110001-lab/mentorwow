from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .jsonutil import dumps, loads
from .models import AuditLog, Event, EventCall, EventMember, Profile, User, as_utc, utcnow


def refresh_status(event: Event) -> None:
    now = utcnow()
    if event.status in {"archived", "draft"}:
        return
    if now > as_utc(event.feed_closes_at):
        event.status = "feed_closed"
    elif now > as_utc(event.chat_closes_at):
        event.status = "chat_closed"
    else:
        event.status = "live"


def member_of(db: Session, event_id: int, user_id: int) -> EventMember | None:
    return (
        db.query(EventMember)
        .filter(EventMember.event_id == event_id, EventMember.user_id == user_id)
        .first()
    )


def require_member(db: Session, event: Event, user: User) -> EventMember:
    row = member_of(db, event.id, user.id)
    if row is None or not row.accepted_join:
        raise HTTPException(status_code=403, detail="Join this event first")
    return row


def is_organizer(event: Event, user: User) -> bool:
    return event.organizer_id == user.id


def visible_on_people(member: EventMember, viewer: User, event: Event) -> bool:
    if member.user_id == viewer.id:
        return True
    return member.attendance_visibility == "visible"


def call_unlocks_contact(db: Session, a: int, b: int) -> bool:
    row = (
        db.query(EventCall)
        .filter(
            EventCall.status.in_(("scheduled", "completed")),
            (
                ((EventCall.requester_id == a) & (EventCall.responder_id == b))
                | ((EventCall.requester_id == b) & (EventCall.responder_id == a))
            ),
        )
        .first()
    )
    return row is not None


def get_or_create_profile(db: Session, user: User) -> Profile:
    row = db.query(Profile).filter(Profile.user_id == user.id).first()
    if row is None:
        row = Profile(user_id=user.id)
        db.add(row)
        db.flush()
    return row


def audit(db: Session, user_id: int | None, action: str, target_type: str, target_id: str, metadata: dict | None = None):
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            metadata_json=dumps(metadata or {}),
        )
    )


def get_visible_profile(db: Session, viewer: User, target: User, event: Event) -> dict | None:
    member = member_of(db, event.id, target.id)
    if member is None:
        return None
    if not visible_on_people(member, viewer, event) and viewer.id != target.id:
        return None
    profile = get_or_create_profile(db, target)
    show_resume = member.resume_visible_this_event and member_of(db, event.id, viewer.id) is not None
    show_email = False
    if viewer.id == target.id:
        show_email = True
    elif member.show_contact_after_call and target.show_contact_after_call:
        show_email = call_unlocks_contact(db, viewer.id, target.id)
    return {
        "user_id": target.id,
        "handle": target.handle,
        "name": target.handle,
        "headline": target.headline,
        "photo_url": "",
        "skill_tags": loads(profile.skill_tags),
        "can_advise_on": loads(profile.can_advise_on),
        "open_to_collaborate_on": loads(profile.open_to_collaborate_on),
        "resume_visible": show_resume,
        "resume_url": f"/api/events/{event.id}/members/{target.id}/resume" if show_resume else None,
        "email": target.email if show_email else None,
        "attendance_visibility": member.attendance_visibility,
        "is_self": viewer.id == target.id,
    }


def pending_incoming_count(db: Session, user_id: int) -> int:
    from .models import QueryMatch

    week = utcnow() - timedelta(days=7)
    return (
        db.query(QueryMatch)
        .filter(
            QueryMatch.matched_user_id == user_id,
            QueryMatch.response == "pending",
            QueryMatch.notified_at >= week,
        )
        .count()
    )


def outgoing_query_count(db: Session, user_id: int) -> int:
    from .models import Query

    week = utcnow() - timedelta(days=7)
    return db.query(Query).filter(Query.author_id == user_id, Query.created_at >= week).count()
