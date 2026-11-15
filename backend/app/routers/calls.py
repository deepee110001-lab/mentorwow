import time

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..config import CALL_SECONDS, GURU_SEEK_COST
from ..database import SessionLocal, get_db
from ..deps import get_current_user
from ..guru import close_call, credit
from ..hub import hub
from ..models import Call, User
from ..schemas import QueueIn
from ..security import decode_access_token

router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.post("/enter")
async def enter_queue(payload: QueueIn, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    topic = payload.topic.strip().lower()
    if payload.side == "seek" and current.guru_balance < GURU_SEEK_COST:
        raise HTTPException(status_code=400, detail=f"Need {GURU_SEEK_COST} GURU to sit as a seeker")
    result = await hub.enter(current.id, topic, payload.side)
    if result["status"] == "matched":
        if payload.side == "seek":
            credit(db, current, -GURU_SEEK_COST, "seek", topic)
        else:
            partner = db.query(User).filter(User.id == hub.rooms[result["room_id"]].seeker_id).one()
            credit(db, partner, -GURU_SEEK_COST, "seek", topic)
        call = Call(
            room_id=result["room_id"],
            topic=topic,
            giver_id=hub.rooms[result["room_id"]].giver_id,
            seeker_id=hub.rooms[result["room_id"]].seeker_id,
            status="live",
        )
        db.add(call)
        db.commit()
    db.refresh(current)
    result["guru_balance"] = current.guru_balance
    return result


@router.get("/status")
async def queue_status(current: User = Depends(get_current_user)):
    return hub.snapshot(current.id)


@router.post("/leave")
async def leave_queue(current: User = Depends(get_current_user)):
    await hub.leave_queue(current.id)
    return {"ok": True}


@router.websocket("/ws/{room_id}")
async def call_socket(websocket: WebSocket, room_id: str):
    token = websocket.query_params.get("token", "")
    user_id = decode_access_token(token)
    if user_id is None:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    room = await hub.connect(room_id, user_id, websocket)
    if room is None:
        await websocket.close(code=4404)
        return
    await websocket.send_json(
        {
            "type": "joined",
            "room_id": room_id,
            "side": "give" if user_id == room.giver_id else "seek",
            "topic": room.topic,
            "seconds": CALL_SECONDS,
            "observer": True,
        }
    )
    await hub.broadcast(
        room,
        {
            "type": "observer",
            "message": "Quality room sat down. Five minutes. No names.",
            "peers": len(room.peers),
            "started": bool(room.started_at),
        },
    )
    if room.started_at:
        await hub.broadcast(
            room,
            {
                "type": "ready",
                "seconds": CALL_SECONDS,
                "initiator_side": "give",
            },
        )
    try:
        while True:
            data = await websocket.receive_json()
            kind = data.get("type")
            if kind == "signal":
                await hub.broadcast(room, {"type": "signal", "from": user_id, "payload": data.get("payload")}, skip=user_id)
            elif kind == "stats":
                room.stats.append(
                    {
                        "user_id": user_id,
                        "loss": float(data.get("loss") or 0),
                        "rtt": float(data.get("rtt") or 0),
                    }
                )
            elif kind == "hangup":
                await finish_room(room, user_id)
                break
    except WebSocketDisconnect:
        await hub.disconnect(room_id, user_id)
        await hub.broadcast(room, {"type": "peer-left"})


async def finish_room(room, user_id: int) -> None:
    if room.closed:
        return
    room.closed = True
    score, notes = hub.quality_score(room)
    duration = int(max(0, (time.time() - room.started_at) if room.started_at else 0))
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.room_id == room.room_id).first()
        give_delta = receive_delta = 0
        if call and call.status != "completed":
            give_delta, receive_delta = close_call(db, call, duration, score, notes)
        payload = {
            "type": "ended",
            "quality_score": score,
            "notes": notes,
            "duration_seconds": duration,
            "give_delta": give_delta,
            "receive_delta": receive_delta,
        }
        await hub.broadcast(room, payload)
    finally:
        db.close()
        await hub.disconnect(room.room_id, user_id)
