from datetime import timedelta

from sqlalchemy.orm import Session

from .handles import random_handle
from .jsonutil import dumps
from .models import (
    ChatMessage,
    Event,
    EventCall,
    EventMember,
    Profile,
    Query,
    QueryMatch,
    User,
    utcnow,
)
from .security import hash_password


def _user(db: Session, email: str, handle: str, name: str, headline: str, **extra) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password("mentorwow"),
            handle=handle,
            name=name,
            headline=headline,
            **extra,
        )
        db.add(user)
        db.flush()
    else:
        user.name = user.name or name
        user.headline = user.headline or headline
    return user


def _profile(db: Session, user: User, skills, advise, collab) -> Profile:
    row = db.query(Profile).filter(Profile.user_id == user.id).first()
    if row is None:
        row = Profile(user_id=user.id)
        db.add(row)
    row.skill_tags = dumps(skills)
    row.can_advise_on = dumps(advise)
    row.open_to_collaborate_on = dumps(collab)
    return row


def seed_graph(db: Session) -> None:
    if db.query(Event).first():
        return
    now = utcnow()
    organizer = _user(db, "organizer@mentorwow.app", "priya-host", "Priya Shah", "Organizer · CEDAT pilot")
    a = _user(db, "copper.loom@mentorwow.app", "copper-loom", "Amina K.", "Product systems")
    b = _user(db, "salt.harbor@mentorwow.app", "salt-harbor", "Jules Park", "Staff engineer")
    c = _user(db, "nimbus.kiln@mentorwow.app", "nimbus-kiln", "Quiet Attendee", "Designer (hidden attendance)")
    d = _user(db, "amber.ridge@mentorwow.app", "amber-ridge", "Samira H.", "Research → industry")
    _profile(db, a, ["product strategy", "privacy"], ["roadmaps", "0-1 product"], ["fintech collab"])
    _profile(db, b, ["system design", "python", "engineering"], ["staff engineering"], ["technical co-founder", "open source"])
    _profile(db, c, ["design systems", "brand"], ["critique"], ["design partnership"])
    _profile(db, d, ["career", "research"], ["PhD transitions"], ["research collab"])
    event = Event(
        organizer_id=organizer.id,
        name="CEDAT Pilot Mixer",
        slug="cedat-pilot",
        join_link_token="cedat-join-demo",
        starts_at=now - timedelta(hours=2),
        ends_at=now + timedelta(hours=4),
        chat_opens_at=now - timedelta(hours=2),
        chat_closes_at=now + timedelta(hours=26),
        feed_closes_at=now + timedelta(days=7),
        status="live",
    )
    db.add(event)
    db.flush()
    for user, vis, resume in [
        (organizer, "visible", False),
        (a, "visible", True),
        (b, "visible", False),
        (c, "hidden", False),
        (d, "visible", False),
    ]:
        db.add(
            EventMember(
                event_id=event.id,
                user_id=user.id,
                accepted_join=True,
                attendance_visibility=vis,
                resume_visible_this_event=resume,
            )
        )
    query = Query(
        event_id=event.id,
        author_id=a.id,
        type="skill",
        body="Need a 5-min teardown of a marketplace matching loop.",
        available_slots=dumps([{"start": (now + timedelta(hours=1)).isoformat(), "end": (now + timedelta(hours=1, minutes=5)).isoformat()}]),
        status="open",
        expires_at=event.feed_closes_at,
    )
    db.add(query)
    db.flush()
    db.add(QueryMatch(query_id=query.id, matched_user_id=b.id, notified_at=now, response="pending", reason="system design overlap"))
    collab = Query(
        event_id=event.id,
        author_id=d.id,
        type="collaboration",
        body="Looking for a technical co-founder to prototype a lab-notes tool.",
        available_slots=dumps([{"start": (now + timedelta(hours=2)).isoformat(), "end": (now + timedelta(hours=2, minutes=5)).isoformat()}]),
        status="open",
        expires_at=event.feed_closes_at,
    )
    db.add(collab)
    db.flush()
    db.add(QueryMatch(query_id=collab.id, matched_user_id=b.id, notified_at=now, response="pending", reason="open to technical co-founder"))
    db.add(
        ChatMessage(event_id=event.id, author_id=a.id, body="Takeaway: eight bets is not a roadmap.")
    )
    db.add(
        ChatMessage(event_id=event.id, author_id=b.id, body="Happy to sit on system design in the booth.")
    )
    db.commit()
