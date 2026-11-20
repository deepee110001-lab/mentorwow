from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import CONNECT_INCOMING_PENDING_LIMIT, CONNECT_OUTGOING_PENDING_LIMIT
from ..connections import (
    get_connection,
    other_id,
    pair_ids,
    pending_incoming_count,
    pending_outgoing_count,
    serialize_person,
    viewer_state,
)
from ..database import get_db
from ..deps import get_current_user
from ..metrics import track
from ..models import Connection, User, utcnow
from ..notify import notify
from ..privacy import member_of, require_member
from .events import get_event_by_slug

router = APIRouter(prefix="/api", tags=["connections"])


def _other_user(db: Session, row: Connection, viewer_id: int) -> User:
    return db.query(User).filter(User.id == other_id(row, viewer_id)).one()


def _require_co_member(db: Session, event, current: User, target_id: int) -> User:
    require_member(db, event, current)
    if target_id == current.id:
        raise HTTPException(status_code=400, detail="You cannot connect with yourself")
    target = db.query(User).filter(User.id == target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Person not found")
    their_seat = member_of(db, event.id, target.id)
    if their_seat is None or not their_seat.accepted_join:
        raise HTTPException(status_code=403, detail="They are not in this room")
    return target


@router.get("/connections")
def list_connections(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = (
        db.query(Connection)
        .filter((Connection.user_low_id == current.id) | (Connection.user_high_id == current.id))
        .order_by(Connection.created_at.desc())
        .all()
    )
    connected = []
    incoming = []
    outgoing = []
    for row in rows:
        other = _other_user(db, row, current.id)
        payload = serialize_person(db, other, row, current.id)
        if row.status == "accepted":
            connected.append(payload)
        elif row.status == "pending" and row.requester_id == current.id:
            outgoing.append(payload)
        elif row.status == "pending":
            incoming.append(payload)
    return {"connected": connected, "incoming": incoming, "outgoing": outgoing}


@router.post("/events/{slug}/connect")
def request_connect(slug: str, payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    try:
        target_id = int(payload.get("user_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="user_id is required")
    target = _require_co_member(db, event, current, target_id)
    existing = get_connection(db, current.id, target.id)
    state = viewer_state(existing, current.id)["state"]
    if state == "connected":
        raise HTTPException(status_code=400, detail="Already connected")
    if state == "pending_out":
        raise HTTPException(status_code=400, detail="Connection already requested")
    if state == "pending_in":
        existing.status = "accepted"
        existing.accepted_at = utcnow()
        if existing.event_id is None:
            existing.event_id = event.id
        track(db, "connection_accepted", user_id=current.id, event_id=event.id, properties={"slug": event.slug, "source": "native"})
        notify(db, existing.requester_id, f"/{current.handle} accepted", "You are connected. They stay on your list.", "/connected")
        db.commit()
        db.refresh(existing)
        return serialize_person(db, target, existing, current.id)

    if pending_outgoing_count(db, current.id) >= CONNECT_OUTGOING_PENDING_LIMIT:
        raise HTTPException(status_code=429, detail="Too many pending connection requests")
    if pending_incoming_count(db, target.id) >= CONNECT_INCOMING_PENDING_LIMIT:
        raise HTTPException(status_code=429, detail="That person already has too many pending requests")

    if existing is None:
        low, high = pair_ids(current.id, target.id)
        existing = Connection(
            user_low_id=low,
            user_high_id=high,
            requester_id=current.id,
            event_id=event.id,
            status="pending",
            source="native",
        )
        db.add(existing)
        db.flush()
    else:
        existing.status = "pending"
        existing.requester_id = current.id
        existing.source = "native"
        existing.event_id = event.id
        existing.accepted_at = None

    track(db, "connection_requested", user_id=current.id, event_id=event.id, properties={"slug": event.slug, "source": "native"})
    notify(db, target.id, f"/{current.handle} wants to connect", "Accept and they stay on your list after this event.", "/connected")
    db.commit()
    db.refresh(existing)
    return serialize_person(db, target, existing, current.id)


@router.post("/connections/{connection_id}/respond")
def respond_connect(connection_id: int, payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    row = db.query(Connection).filter(Connection.id == connection_id).first()
    if row is None or current.id not in {row.user_low_id, row.user_high_id}:
        raise HTTPException(status_code=404, detail="Request not found")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="This request is no longer pending")
    if row.requester_id == current.id:
        raise HTTPException(status_code=400, detail="Wait for them to respond")
    action = (payload.get("response") or "").strip().lower()
    if action not in {"accepted", "declined"}:
        raise HTTPException(status_code=400, detail="response must be accepted or declined")
    row.status = action
    if action == "accepted":
        row.accepted_at = utcnow()
        track(db, "connection_accepted", user_id=current.id, event_id=row.event_id, properties={"source": "native"})
        notify(db, row.requester_id, f"/{current.handle} accepted", "You are connected. They stay on your list.", "/connected")
    db.commit()
    other = _other_user(db, row, current.id)
    return serialize_person(db, other, row, current.id)


@router.post("/connections/{connection_id}/disconnect")
def disconnect(connection_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    row = db.query(Connection).filter(Connection.id == connection_id).first()
    if row is None or current.id not in {row.user_low_id, row.user_high_id}:
        raise HTTPException(status_code=404, detail="Connection not found")
    if row.status != "accepted":
        raise HTTPException(status_code=400, detail="Not connected")
    row.status = "disconnected"
    db.commit()
    other = _other_user(db, row, current.id)
    return serialize_person(db, other, row, current.id)
