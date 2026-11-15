from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai import moderate_message, summarize_chat
from ..database import get_db
from ..deps import get_current_user
from ..models import ChatMessage, User, as_utc, utcnow
from ..privacy import is_organizer, refresh_status, require_member
from .events import get_event_by_slug

router = APIRouter(prefix="/api", tags=["chat"])


def serialize(msg: ChatMessage, db: Session) -> dict:
    author = db.query(User).filter(User.id == msg.author_id).first() if msg.author_id else None
    return {
        "id": msg.id,
        "body": msg.body,
        "is_pinned": msg.is_pinned,
        "is_system": msg.is_system,
        "flagged": msg.flagged,
        "flag_reason": msg.flag_reason,
        "parent_id": msg.parent_id,
        "created_at": msg.created_at,
        "author": {"name": (author.name or author.handle) if author else "System", "user_id": msg.author_id},
    }


@router.get("/events/{slug}/chat")
def list_chat(slug: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.event_id == event.id)
        .order_by(ChatMessage.is_pinned.desc(), ChatMessage.created_at.asc())
        .all()
    )
    return {
        "open": utcnow() <= as_utc(event.chat_closes_at),
        "closes_at": event.chat_closes_at,
        "messages": [serialize(row, db) for row in rows],
    }


@router.post("/events/{slug}/chat")
def post_chat(slug: str, payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    refresh_status(event)
    if utcnow() > as_utc(event.chat_closes_at):
        raise HTTPException(status_code=403, detail="Chat closed")
    body = (payload.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Empty message")
    mod = moderate_message(body)
    msg = ChatMessage(
        event_id=event.id,
        author_id=current.id,
        body=body,
        parent_id=payload.get("parent_id"),
        flagged=bool(mod.get("flagged")),
        flag_reason=mod.get("reason"),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return serialize(msg, db)


@router.post("/events/{slug}/chat/{message_id}/pin")
def pin_chat(slug: str, message_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    if not is_organizer(event, current):
        raise HTTPException(status_code=403, detail="Only the organizer can pin")
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id, ChatMessage.event_id == event.id).first()
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.is_pinned = not msg.is_pinned
    db.commit()
    return serialize(msg, db)


@router.post("/events/{slug}/chat/{message_id}/report")
def report_chat(slug: str, message_id: int, payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id, ChatMessage.event_id == event.id).first()
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.flagged = True
    msg.flag_reason = payload.get("reason") or "reported"
    db.commit()
    return serialize(msg, db)


@router.post("/events/{slug}/chat/recap")
def recap_chat(slug: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    if utcnow() > as_utc(event.chat_closes_at):
        raise HTTPException(status_code=403, detail="Chat closed")
    rows = db.query(ChatMessage).filter(ChatMessage.event_id == event.id, ChatMessage.is_system.is_(False)).all()
    packed = []
    for row in rows:
        author = db.query(User).filter(User.id == row.author_id).first() if row.author_id else None
        packed.append({"name": (author.name or author.handle) if author else "member", "body": row.body})
    summary = summarize_chat(packed)
    msg = ChatMessage(event_id=event.id, author_id=None, body=summary, is_system=True, is_pinned=True)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return serialize(msg, db)
