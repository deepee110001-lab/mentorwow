from __future__ import annotations

import asyncio
import json
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import WebSocket

from .config import CALL_SECONDS


@dataclass
class Waiter:
    user_id: int
    topic: str
    side: str
    room_id: str | None = None


@dataclass
class Peer:
    user_id: int
    socket: WebSocket
    side: str


@dataclass
class Room:
    room_id: str
    topic: str
    giver_id: int
    seeker_id: int
    peers: dict[int, Peer] = field(default_factory=dict)
    stats: list[dict] = field(default_factory=list)
    started_at: float = 0.0
    closed: bool = False


class Hub:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.waiting: dict[tuple[str, str], list[Waiter]] = defaultdict(list)
        self.by_user: dict[int, Waiter] = {}
        self.rooms: dict[str, Room] = {}
        self.user_room: dict[int, str] = {}

    def snapshot(self, user_id: int) -> dict:
        waiter = self.by_user.get(user_id)
        if waiter and waiter.room_id:
            room = self.rooms.get(waiter.room_id)
            if room:
                return {
                    "status": "matched",
                    "room_id": room.room_id,
                    "side": waiter.side,
                    "topic": room.topic,
                    "seconds": CALL_SECONDS,
                }
        if waiter:
            return {"status": "waiting", "side": waiter.side, "topic": waiter.topic, "seconds": CALL_SECONDS}
        room_id = self.user_room.get(user_id)
        if room_id and room_id in self.rooms:
            room = self.rooms[room_id]
            side = "give" if room.giver_id == user_id else "seek"
            return {
                "status": "matched",
                "room_id": room.room_id,
                "side": side,
                "topic": room.topic,
                "seconds": CALL_SECONDS,
            }
        return {"status": "idle"}

    async def enter(self, user_id: int, topic: str, side: str) -> dict:
        async with self.lock:
            self._leave_locked(user_id)
            other = "give" if side == "seek" else "seek"
            opp = self.waiting[(topic, other)]
            if opp:
                partner = opp.pop(0)
                self.by_user.pop(partner.user_id, None)
                room_id = secrets.token_hex(8)
                room = Room(
                    room_id=room_id,
                    topic=topic,
                    giver_id=user_id if side == "give" else partner.user_id,
                    seeker_id=user_id if side == "seek" else partner.user_id,
                )
                self.rooms[room_id] = room
                self.user_room[room.giver_id] = room_id
                self.user_room[room.seeker_id] = room_id
                partner.room_id = room_id
                self.by_user[partner.user_id] = Waiter(
                    user_id=partner.user_id, topic=topic, side=other, room_id=room_id
                )
                self.by_user[user_id] = Waiter(user_id=user_id, topic=topic, side=side, room_id=room_id)
                return {
                    "status": "matched",
                    "room_id": room_id,
                    "side": side,
                    "topic": topic,
                    "seconds": CALL_SECONDS,
                }
            waiter = Waiter(user_id=user_id, topic=topic, side=side)
            self.waiting[(topic, side)].append(waiter)
            self.by_user[user_id] = waiter
            return {"status": "waiting", "side": side, "topic": topic, "seconds": CALL_SECONDS}

    async def leave_queue(self, user_id: int) -> None:
        async with self.lock:
            self._leave_locked(user_id)

    def _leave_locked(self, user_id: int) -> None:
        waiter = self.by_user.pop(user_id, None)
        if waiter and not waiter.room_id:
            bucket = self.waiting.get((waiter.topic, waiter.side), [])
            self.waiting[(waiter.topic, waiter.side)] = [item for item in bucket if item.user_id != user_id]

    async def connect(self, room_id: str, user_id: int, socket: WebSocket) -> Room | None:
        async with self.lock:
            room = self.rooms.get(room_id)
            if room is None or room.closed:
                return None
            if user_id not in {room.giver_id, room.seeker_id}:
                return None
            side = "give" if user_id == room.giver_id else "seek"
            room.peers[user_id] = Peer(user_id=user_id, socket=socket, side=side)
            if len(room.peers) == 2 and not room.started_at:
                room.started_at = time.time()
            return room

    async def disconnect(self, room_id: str, user_id: int) -> None:
        async with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return
            room.peers.pop(user_id, None)

    async def broadcast(self, room: Room, payload: dict, skip: int | None = None) -> None:
        dead: list[int] = []
        for peer in list(room.peers.values()):
            if skip is not None and peer.user_id == skip:
                continue
            try:
                await peer.socket.send_text(json.dumps(payload))
            except Exception:
                dead.append(peer.user_id)
        for user_id in dead:
            room.peers.pop(user_id, None)

    def quality_score(self, room: Room) -> tuple[float, str]:
        if not room.stats:
            duration = time.time() - room.started_at if room.started_at else 0
            score = 55 if duration >= CALL_SECONDS * 0.8 else 40
            return score, "Observer sat in. Sparse telemetry; score from presence."
        loss = [row.get("loss", 0) for row in room.stats]
        rtt = [row.get("rtt", 0) for row in room.stats]
        avg_loss = sum(loss) / max(len(loss), 1)
        avg_rtt = sum(rtt) / max(len(rtt), 1)
        duration = time.time() - room.started_at if room.started_at else 0
        score = 92
        notes = ["Quality room joined both chairs."]
        if avg_loss > 4:
            score -= 18
            notes.append("Packet loss showed up.")
        if avg_rtt > 250:
            score -= 12
            notes.append("Round-trip ran long.")
        if duration < CALL_SECONDS * 0.6:
            score -= 20
            notes.append("The five minutes were cut short.")
        return max(20, min(100, score)), " ".join(notes)


hub = Hub()
