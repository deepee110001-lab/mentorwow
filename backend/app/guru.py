from sqlalchemy.orm import Session

from .models import Call, GuruEvent, Post, TopicStat, User, utcnow


def parse_topics(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def join_topics(topics: list[str]) -> str:
    return ", ".join(dict.fromkeys(topic.strip() for topic in topics if topic.strip()))


def credit(db: Session, user: User, amount: int, reason: str, note: str = "") -> None:
    user.guru_balance += amount
    db.add(GuruEvent(user_id=user.id, amount=amount, reason=reason, note=note))


def bump_minutes(db: Session, user_id: int, topic: str, *, given: int = 0, received: int = 0) -> None:
    row = (
        db.query(TopicStat)
        .filter(TopicStat.user_id == user_id, TopicStat.topic == topic)
        .first()
    )
    if row is None:
        row = TopicStat(user_id=user_id, topic=topic)
        db.add(row)
        db.flush()
    row.given_seconds += given
    row.received_seconds += received


def close_call(db: Session, call: Call, duration: int, score: float, notes: str) -> tuple[int, int]:
    call.status = "completed"
    call.ended_at = utcnow()
    call.duration_seconds = duration
    call.quality_score = round(score, 2)
    call.quality_notes = notes
    giver = db.query(User).filter(User.id == call.giver_id).one()
    seeker = db.query(User).filter(User.id == call.seeker_id).one()
    bonus = int(max(0, min(5, round(score / 20))))
    give_delta = 5 + bonus
    receive_delta = 1
    credit(db, giver, give_delta, "give", f"{call.topic} · quality {call.quality_score}")
    credit(db, seeker, receive_delta, "receive", call.topic)
    bump_minutes(db, giver.id, call.topic, given=duration)
    bump_minutes(db, seeker.id, call.topic, received=duration)
    db.add(
        Post(
            author_id=giver.id,
            kind="update",
            title="",
            body=f"A five-minute session closed on {call.topic}. No names. The quality room kept the score.",
            topic=call.topic,
        )
    )
    db.commit()
    return give_delta, receive_delta
