from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..jsonutil import dumps, loads
from ..matching import create_matches
from ..models import EventCall, Query, QueryMatch, User, as_utc, utcnow
from ..config import INCOMING_PENDING_LIMIT, OUTGOING_QUERY_LIMIT
from ..privacy import outgoing_query_count, pending_incoming_count, refresh_status, require_member
from .events import get_event_by_slug

router = APIRouter(prefix="/api", tags=["queries"])


def serialize_query(item: Query, matches: list[QueryMatch], viewer: User, db, event) -> dict:
    author = db.query(User).filter(User.id == item.author_id).one()
    my_match = next((m for m in matches if m.matched_user_id == viewer.id), None)
    return {
        "id": item.id,
        "type": item.type,
        "body": item.body,
        "available_slots": loads(item.available_slots),
        "status": item.status,
        "created_at": item.created_at,
        "expires_at": item.expires_at,
        "author": {
            "user_id": author.id,
            "name": author.name or author.handle,
            "headline": author.headline,
        },
        "matched": my_match is not None or item.author_id == viewer.id,
        "my_response": my_match.response if my_match else None,
        "match_reason": my_match.reason if my_match else None,
        "match_count": len(matches),
    }


@router.get("/events/{slug}/queries")
def list_queries(slug: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    items = (
        db.query(Query)
        .filter(Query.event_id == event.id)
        .order_by(Query.created_at.desc())
        .all()
    )
    out = []
    mine = []
    rest = []
    for item in items:
        matches = db.query(QueryMatch).filter(QueryMatch.query_id == item.id).all()
        payload = serialize_query(item, matches, current, db, event)
        if payload["matched"] and item.author_id != current.id:
            mine.append(payload)
        else:
            rest.append(payload)
    return mine + rest


@router.post("/events/{slug}/queries")
def create_query(slug: str, payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    refresh_status(event)
    if utcnow() > as_utc(event.feed_closes_at) or event.status in {"feed_closed", "archived"}:
        raise HTTPException(status_code=403, detail="Feed is closed")
    if outgoing_query_count(db, current.id) >= OUTGOING_QUERY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit: max 2 outgoing queries per week",
        )
    body = (payload.get("body") or "").strip()
    qtype = payload.get("type")
    if qtype not in {"skill", "collaboration"}:
        raise HTTPException(status_code=400, detail="type must be skill or collaboration")
    if not body or len(body) > 280:
        raise HTTPException(status_code=400, detail="Body must be 1–280 characters")
    slots = payload.get("available_slots") or []
    if not isinstance(slots, list) or not (1 <= len(slots) <= 3):
        raise HTTPException(status_code=400, detail="Pick 1–3 available slots")
    target_id = payload.get("target_user_id")
    if target_id and pending_incoming_count(db, int(target_id)) >= INCOMING_PENDING_LIMIT:
        raise HTTPException(status_code=429, detail="That person already has 5 pending incoming requests this week")
    item = Query(
        event_id=event.id,
        author_id=current.id,
        type=qtype,
        body=body,
        available_slots=dumps(slots),
        status="open",
        expires_at=event.feed_closes_at,
    )
    db.add(item)
    db.flush()
    if target_id:
        match = QueryMatch(
            query_id=item.id,
            matched_user_id=int(target_id),
            notified_at=utcnow(),
            response="pending",
            reason="direct request from People tab",
        )
        db.add(match)
        from ..notify import notify

        notify(
            db,
            int(target_id),
            f"{current.name or current.handle} asked for 5 min",
            body,
            f"/e/{event.slug}/feed",
        )
    else:
        created = create_matches(db, item, event)
        if not created:
            pass
    db.commit()
    matches = db.query(QueryMatch).filter(QueryMatch.query_id == item.id).all()
    return serialize_query(item, matches, current, db, event)


@router.post("/queries/{query_id}/respond")
def respond_query(query_id: int, payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    match = (
        db.query(QueryMatch)
        .filter(QueryMatch.query_id == query_id, QueryMatch.matched_user_id == current.id)
        .first()
    )
    if match is None:
        raise HTTPException(status_code=404, detail="You were not matched to this query")
    query = db.query(Query).filter(Query.id == query_id).one()
    action = payload.get("response")
    if action not in {"accepted", "declined"}:
        raise HTTPException(status_code=400, detail="response must be accepted or declined")
    match.response = action
    match.responded_at = utcnow()
    call_payload = None
    if action == "accepted":
        slot = payload.get("slot") or {}
        start = slot.get("start")
        if not start:
            raise HTTPException(status_code=400, detail="Pick a slot")
        scheduled = datetime.fromisoformat(start.replace("Z", "+00:00"))
        room = f"https://meet.jit.si/mentorwow-{query.id}-{current.id}-{secrets_hex()}"
        call = EventCall(
            query_id=query.id,
            requester_id=query.author_id,
            responder_id=current.id,
            scheduled_at=scheduled,
            duration_minutes=5,
            meeting_url=room,
            status="scheduled",
        )
        db.add(call)
        db.flush()
        call_payload = {
            "id": call.id,
            "scheduled_at": call.scheduled_at,
            "meeting_url": call.meeting_url,
            "status": call.status,
        }
    db.commit()
    return {"ok": True, "response": action, "call": call_payload}


def secrets_hex() -> str:
    import secrets

    return secrets.token_hex(4)
