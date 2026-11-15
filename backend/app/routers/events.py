import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..ai import parse_resume
from ..config import STORAGE_DIR
from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..jsonutil import dumps, loads
from ..models import Event, EventMember, Profile, User, as_utc, utcnow
from ..privacy import (
    audit,
    get_or_create_profile,
    get_visible_profile,
    is_organizer,
    member_of,
    refresh_status,
    require_member,
    visible_on_people,
)

router = APIRouter(prefix="/api", tags=["events"])


def event_out(event: Event) -> dict:
    refresh_status(event)
    return {
        "id": event.id,
        "name": event.name,
        "slug": event.slug,
        "join_link_token": event.join_link_token,
        "starts_at": event.starts_at,
        "ends_at": event.ends_at,
        "chat_opens_at": event.chat_opens_at,
        "chat_closes_at": event.chat_closes_at,
        "feed_closes_at": event.feed_closes_at,
        "status": event.status,
        "organizer_id": event.organizer_id,
        "chat_open": as_utc(event.chat_opens_at) <= utcnow() <= as_utc(event.chat_closes_at),
        "feed_open": utcnow() <= as_utc(event.feed_closes_at),
    }


def get_event_by_slug(db: Session, slug: str) -> Event:
    event = db.query(Event).filter(Event.slug == slug).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    refresh_status(event)
    return event


@router.get("/join/{token}")
def resolve_join(token: str, db: Session = Depends(get_db), viewer: User | None = Depends(get_optional_user)):
    event = db.query(Event).filter(Event.join_link_token == token).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Invalid join link")
    refresh_status(event)
    if event.status == "archived":
        raise HTTPException(status_code=410, detail="This event is archived")
    member = member_of(db, event.id, viewer.id) if viewer else None
    return {
        "event": event_out(event),
        "joined": bool(member and member.accepted_join),
        "authenticated": viewer is not None,
    }


@router.post("/join/{token}")
def join_event(
    token: str,
    payload: dict,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    event = db.query(Event).filter(Event.join_link_token == token).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Invalid join link")
    if not payload.get("accepted_join"):
        raise HTTPException(status_code=400, detail="You must accept attendance consent to join")
    attendance = "visible" if payload.get("show_attendance", True) else "hidden"
    resume_vis = bool(payload.get("resume_visible_this_event", False))
    contact = bool(payload.get("show_contact_after_call", True))
    if payload.get("name"):
        current.name = payload["name"].strip()
    if payload.get("headline") is not None:
        current.headline = payload["headline"].strip()
    profile = get_or_create_profile(db, current)
    for key in ("skill_tags", "can_advise_on", "open_to_collaborate_on"):
        if key in payload and isinstance(payload[key], list):
            setattr(profile, key, dumps(payload[key]))
    member = member_of(db, event.id, current.id)
    if member is None:
        member = EventMember(event_id=event.id, user_id=current.id)
        db.add(member)
    member.accepted_join = True
    member.attendance_visibility = attendance
    member.resume_visible_this_event = resume_vis
    member.show_contact_after_call = contact
    current.show_contact_after_call = contact
    audit(
        db,
        current.id,
        "join_event",
        "event",
        str(event.id),
        {"attendance": attendance, "resume": resume_vis, "contact": contact},
    )
    db.commit()
    return {"ok": True, "event": event_out(event), "slug": event.slug}


@router.get("/events/{slug}")
def event_home(slug: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    member = require_member(db, event, current)
    return {
        "event": event_out(event),
        "member": {
            "attendance_visibility": member.attendance_visibility,
            "resume_visible_this_event": member.resume_visible_this_event,
            "show_contact_after_call": member.show_contact_after_call,
        },
        "is_organizer": is_organizer(event, current),
    }


@router.get("/events/{slug}/people")
def people(slug: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    members = db.query(EventMember).filter(EventMember.event_id == event.id, EventMember.accepted_join.is_(True)).all()
    out = []
    for member in members:
        if not visible_on_people(member, current, event):
            continue
        target = db.query(User).filter(User.id == member.user_id).one()
        visible = get_visible_profile(db, current, target, event)
        if visible:
            out.append(visible)
    return out


@router.get("/events/{event_id}/members/{user_id}/resume")
def resume_file(
    event_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    require_member(db, event, current)
    member = member_of(db, event.id, user_id)
    if member is None or not member.resume_visible_this_event:
        raise HTTPException(status_code=403, detail="Resume is not visible for this event")
    profile = get_or_create_profile(db, db.query(User).filter(User.id == user_id).one())
    if not profile.resume_url:
        raise HTTPException(status_code=404, detail="No resume uploaded")
    path = Path(profile.resume_url)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Resume missing")
    return FileResponse(path, filename=path.name, media_type="application/pdf")


@router.post("/me/resume")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    dest = STORAGE_DIR / f"{current.id}.pdf"
    dest.write_bytes(data)
    tags = parse_resume(data)
    profile = get_or_create_profile(db, current)
    profile.resume_url = str(dest)
    profile.skill_tags = dumps(tags["skill_tags"])
    profile.can_advise_on = dumps(tags["can_advise_on"])
    profile.open_to_collaborate_on = dumps(tags["open_to_collaborate_on"])
    db.commit()
    return {"ok": True, **tags, "resume_url": f"/api/me/resume-file"}


@router.get("/me/profile")
def my_profile(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    profile = get_or_create_profile(db, current)
    return {
        "id": current.id,
        "email": current.email,
        "name": current.name,
        "headline": current.headline,
        "photo_url": current.photo_url,
        "handle": current.handle,
        "default_profile_visibility": current.default_profile_visibility,
        "show_contact_after_call": current.show_contact_after_call,
        "skill_tags": loads(profile.skill_tags),
        "can_advise_on": loads(profile.can_advise_on),
        "open_to_collaborate_on": loads(profile.open_to_collaborate_on),
        "resume_uploaded": bool(profile.resume_url),
        "resume_visible_default": profile.resume_visible_default,
    }


@router.put("/me/profile")
def update_profile(payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    profile = get_or_create_profile(db, current)
    for field in ("name", "headline", "photo_url", "default_profile_visibility"):
        if field in payload and payload[field] is not None:
            setattr(current, field, payload[field])
    if "show_contact_after_call" in payload:
        current.show_contact_after_call = bool(payload["show_contact_after_call"])
    for key in ("skill_tags", "can_advise_on", "open_to_collaborate_on"):
        if key in payload and isinstance(payload[key], list):
            setattr(profile, key, dumps(payload[key]))
    if "resume_visible_default" in payload:
        profile.resume_visible_default = bool(payload["resume_visible_default"])
    db.commit()
    return {"ok": True}


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    from ..models import Notification

    rows = (
        db.query(Notification)
        .filter(Notification.user_id == current.id)
        .order_by(Notification.created_at.desc())
        .limit(40)
        .all()
    )
    return [
        {"id": row.id, "title": row.title, "body": row.body, "link": row.link, "read": row.read, "created_at": row.created_at}
        for row in rows
    ]
