from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..jsonutil import dumps, loads
from ..models import EventCall, Query, User
from ..privacy import call_unlocks_contact, get_visible_profile
from .events import get_event_by_slug
from ..privacy import require_member

router = APIRouter(prefix="/api", tags=["event-calls"])


def party(db: Session, user: User) -> dict:
    return {"user_id": user.id, "name": user.name or user.handle, "headline": user.headline, "email": None}


@router.get("/events/{slug}/calls")
def list_calls(slug: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    query_ids = [row.id for row in db.query(Query.id).filter(Query.event_id == event.id)]
    rows = (
        db.query(EventCall)
        .filter(
            (EventCall.requester_id == current.id) | (EventCall.responder_id == current.id),
            (EventCall.query_id.in_(query_ids)) | (EventCall.query_id.is_(None)),
        )
        .order_by(EventCall.scheduled_at.desc())
        .all()
    )
    out = []
    for call in rows:
        other_id = call.responder_id if call.requester_id == current.id else call.requester_id
        other = db.query(User).filter(User.id == other_id).one()
        email = other.email if call.status in {"scheduled", "completed"} and call_unlocks_contact(db, current.id, other.id) else None
        out.append(
            {
                "id": call.id,
                "status": call.status,
                "scheduled_at": call.scheduled_at,
                "duration_minutes": call.duration_minutes,
                "meeting_url": call.meeting_url if call.status in {"scheduled", "completed"} else None,
                "role": "requester" if call.requester_id == current.id else "responder",
                "other": {
                    "user_id": other.id,
                    "name": other.name or other.handle,
                    "headline": other.headline,
                    "email": email,
                },
                "feedback_requester": loads(call.feedback_requester, {}),
                "feedback_responder": loads(call.feedback_responder, {}),
            }
        )
    return out


@router.post("/calls/{call_id}/complete")
def complete_call(call_id: int, payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    call = db.query(EventCall).filter(EventCall.id == call_id).first()
    if call is None or current.id not in {call.requester_id, call.responder_id}:
        raise HTTPException(status_code=404, detail="Call not found")
    if call.status == "cancelled":
        raise HTTPException(status_code=400, detail="Call cancelled")
    call.status = payload.get("status", "completed")
    if call.status not in {"completed", "no_show"}:
        call.status = "completed"
    feedback = {
        "usefulness": payload.get("usefulness"),
        "takeaway": payload.get("takeaway") or "",
    }
    blob = dumps(feedback)
    if current.id == call.requester_id:
        call.feedback_requester = blob
    else:
        call.feedback_responder = blob
    db.commit()
    return {"ok": True, "status": call.status}
