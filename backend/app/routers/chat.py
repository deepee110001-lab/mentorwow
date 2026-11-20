from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai import moderate_message, summarize_chat
from ..database import get_db
from ..deps import get_current_user
from ..metrics import track
from ..models import ChatMessage, ChatPollVote, Event, User, as_utc, utcnow
from ..privacy import is_organizer, refresh_status, require_member
from .events import get_event_by_slug

router = APIRouter(prefix="/api", tags=["chat"])


def serialize(msg: ChatMessage, db: Session, viewer_id: int | None = None) -> dict:
    author = db.query(User).filter(User.id == msg.author_id).first() if msg.author_id else None
    kind = msg.kind or "message"
    deleted = msg.deleted_at is not None
    poll = None
    if kind == "poll" and not deleted:
        votes = db.query(ChatPollVote).filter(ChatPollVote.message_id == msg.id).all()
        yay = sum(1 for row in votes if row.choice == "yay")
        nay = sum(1 for row in votes if row.choice == "nay")
        mine = next((row.choice for row in votes if row.user_id == viewer_id), None)
        poll = {"yay": yay, "nay": nay, "total": len(votes), "my_vote": mine}
    return {
        "id": msg.id,
        "body": "This message was deleted" if deleted else msg.body,
        "kind": kind,
        "is_pinned": msg.is_pinned and not deleted,
        "is_system": msg.is_system,
        "parent_id": msg.parent_id,
        "created_at": msg.created_at,
        "deleted": deleted,
        "author": {"handle": author.handle if author else "system", "name": author.handle if author else "System", "user_id": msg.author_id},
        "poll": poll,
    }


@router.get("/me/polls")
def my_polls(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.author_id == current.id,
            ChatMessage.kind == "poll",
            ChatMessage.deleted_at.is_(None),
        )
        .order_by(ChatMessage.created_at.desc())
        .all()
    )
    event_ids = {msg.event_id for msg in rows}
    events = (
        {row.id: row for row in db.query(Event).filter(Event.id.in_(event_ids)).all()} if event_ids else {}
    )
    out = []
    for msg in rows:
        payload = serialize(msg, db, current.id)
        event = events.get(msg.event_id)
        payload["event"] = {"id": event.id, "slug": event.slug, "name": event.name} if event else None
        out.append(payload)
    return out


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
        "messages": [serialize(row, db, current.id) for row in rows],
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
    kind = payload.get("kind") or "message"
    if kind not in {"message", "poll"}:
        raise HTTPException(status_code=400, detail="kind must be message or poll")
    if kind == "poll" and len(body) > 180:
        raise HTTPException(status_code=400, detail="Poll question must be 1–180 characters")
    mod = moderate_message(body)
    msg = ChatMessage(
        event_id=event.id,
        author_id=current.id,
        body=body,
        kind=kind,
        parent_id=payload.get("parent_id") if kind == "message" else None,
        flagged=bool(mod.get("flagged")),
        flag_reason=mod.get("reason"),
    )
    db.add(msg)
    track(db, "chat_sent", user_id=current.id, event_id=event.id, properties={"slug": event.slug})
    db.commit()
    db.refresh(msg)
    return serialize(msg, db, current.id)


@router.post("/events/{slug}/chat/{message_id}/vote")
def vote_poll(slug: str, message_id: int, payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    if utcnow() > as_utc(event.chat_closes_at):
        raise HTTPException(status_code=403, detail="Chat closed")
    choice = (payload.get("choice") or "").strip().lower()
    if choice not in {"yay", "nay"}:
        raise HTTPException(status_code=400, detail="choice must be yay or nay")
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id, ChatMessage.event_id == event.id).first()
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Message was deleted")
    if (msg.kind or "message") != "poll":
        raise HTTPException(status_code=400, detail="Not a poll")
    row = (
        db.query(ChatPollVote)
        .filter(ChatPollVote.message_id == msg.id, ChatPollVote.user_id == current.id)
        .first()
    )
    if row is None:
        db.add(ChatPollVote(message_id=msg.id, user_id=current.id, choice=choice))
    else:
        row.choice = choice
    db.commit()
    db.refresh(msg)
    return serialize(msg, db, current.id)


@router.delete("/events/{slug}/chat/{message_id}")
def delete_chat(slug: str, message_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id, ChatMessage.event_id == event.id).first()
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Already deleted")
    owner = msg.author_id == current.id
    if not owner and not is_organizer(event, current):
        raise HTTPException(status_code=403, detail="You can only delete your own messages")
    msg.deleted_at = utcnow()
    msg.is_pinned = False
    db.commit()
    db.refresh(msg)
    return serialize(msg, db, current.id)


@router.post("/events/{slug}/chat/{message_id}/pin")
def pin_chat(slug: str, message_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    if not is_organizer(event, current):
        raise HTTPException(status_code=403, detail="Only the organizer can pin")
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id, ChatMessage.event_id == event.id).first()
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Message was deleted")
    msg.is_pinned = not msg.is_pinned
    db.commit()
    return serialize(msg, db, current.id)


@router.post("/events/{slug}/chat/recap")
def recap_chat(slug: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    if utcnow() > as_utc(event.chat_closes_at):
        raise HTTPException(status_code=403, detail="Chat closed")
    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.event_id == event.id,
            ChatMessage.is_system.is_(False),
            ChatMessage.deleted_at.is_(None),
        )
        .all()
    )
    packed = []
    for row in rows:
        author = db.query(User).filter(User.id == row.author_id).first() if row.author_id else None
        packed.append({"name": author.handle if author else "member", "body": row.body})
    summary = summarize_chat(packed)
    msg = ChatMessage(event_id=event.id, author_id=None, body=summary, is_system=True, is_pinned=True, kind="message")
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return serialize(msg, db, current.id)
