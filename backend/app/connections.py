from sqlalchemy.orm import Session

from .models import Connection, Event, User, utcnow


INACTIVE = frozenset({"declined", "disconnected"})


def pair_ids(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def get_connection(db: Session, a: int, b: int) -> Connection | None:
    low, high = pair_ids(a, b)
    return (
        db.query(Connection)
        .filter(Connection.user_low_id == low, Connection.user_high_id == high)
        .first()
    )


def other_id(row: Connection, viewer_id: int) -> int:
    return row.user_high_id if row.user_low_id == viewer_id else row.user_low_id


def viewer_state(row: Connection | None, viewer_id: int) -> dict:
    if row is None or row.status in INACTIVE:
        return {"id": row.id if row else None, "state": "none"}
    if row.status == "accepted":
        return {"id": row.id, "state": "connected"}
    if row.requester_id == viewer_id:
        return {"id": row.id, "state": "pending_out"}
    return {"id": row.id, "state": "pending_in"}


def connections_for(db: Session, user_id: int) -> dict[int, Connection]:
    rows = (
        db.query(Connection)
        .filter((Connection.user_low_id == user_id) | (Connection.user_high_id == user_id))
        .all()
    )
    return {other_id(row, user_id): row for row in rows}


def pending_outgoing_count(db: Session, user_id: int) -> int:
    return (
        db.query(Connection)
        .filter(Connection.requester_id == user_id, Connection.status == "pending")
        .count()
    )


def pending_incoming_count(db: Session, user_id: int) -> int:
    return (
        db.query(Connection)
        .filter(
            Connection.status == "pending",
            Connection.requester_id != user_id,
            (Connection.user_low_id == user_id) | (Connection.user_high_id == user_id),
        )
        .count()
    )


def ensure_accepted_connection(
    db: Session,
    a: int,
    b: int,
    *,
    source: str,
    event_id: int | None = None,
) -> Connection:
    if a == b:
        raise ValueError("cannot connect to self")
    row = get_connection(db, a, b)
    now = utcnow()
    if row is None:
        low, high = pair_ids(a, b)
        row = Connection(
            user_low_id=low,
            user_high_id=high,
            requester_id=a,
            event_id=event_id,
            status="accepted",
            source=source,
            accepted_at=now,
        )
        db.add(row)
        db.flush()
        return row
    if row.status != "accepted":
        row.status = "accepted"
        row.accepted_at = now
        if source:
            row.source = source
        if event_id and row.event_id is None:
            row.event_id = event_id
    return row


def serialize_person(db: Session, user: User, row: Connection, viewer_id: int) -> dict:
    event_name = None
    event_slug = None
    if row.event_id:
        event = db.query(Event).filter(Event.id == row.event_id).first()
        if event is not None:
            event_name = event.name
            event_slug = event.slug
    state = viewer_state(row, viewer_id)
    return {
        "id": row.id,
        "user_id": user.id,
        "handle": user.handle,
        "headline": user.headline,
        "status": row.status,
        "state": state["state"],
        "source": row.source,
        "created_at": row.created_at,
        "accepted_at": row.accepted_at,
        "event_name": event_name,
        "event_slug": event_slug,
    }
