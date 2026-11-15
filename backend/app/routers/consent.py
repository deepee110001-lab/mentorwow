from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Event, EventMember, User
from ..privacy import audit, member_of, require_member
from .events import get_event_by_slug

router = APIRouter(prefix="/api", tags=["consent"])


@router.post("/consent")
def update_consent(payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    slug = payload.get("slug") or payload.get("event_slug")
    if not slug:
        raise HTTPException(status_code=400, detail="event slug required")
    event = get_event_by_slug(db, slug)
    member = require_member(db, event, current)
    changes = {}
    if "attendance_visibility" in payload:
        value = payload["attendance_visibility"]
        if value not in {"visible", "hidden"}:
            raise HTTPException(status_code=400, detail="attendance_visibility must be visible or hidden")
        member.attendance_visibility = value
        changes["attendance_visibility"] = value
    if "resume_visible_this_event" in payload:
        member.resume_visible_this_event = bool(payload["resume_visible_this_event"])
        changes["resume_visible_this_event"] = member.resume_visible_this_event
    if "show_contact_after_call" in payload:
        member.show_contact_after_call = bool(payload["show_contact_after_call"])
        current.show_contact_after_call = member.show_contact_after_call
        changes["show_contact_after_call"] = member.show_contact_after_call
    audit(db, current.id, "consent_update", "event_member", str(member.id), changes)
    db.commit()
    return {
        "ok": True,
        "attendance_visibility": member.attendance_visibility,
        "resume_visible_this_event": member.resume_visible_this_event,
        "show_contact_after_call": member.show_contact_after_call,
    }
