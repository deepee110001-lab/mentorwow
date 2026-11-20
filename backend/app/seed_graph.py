from datetime import timedelta

from sqlalchemy.orm import Session

from .config import ADMIN_HANDLE, ORGANIZER_EMAIL, PILOT_JOIN_TOKEN, PILOT_SLUG
from .handles import random_handle
from .jsonutil import dumps
from .metrics import track
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


def _user(db: Session, email: str, handle: str, headline: str = "", **extra) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password("mentorwow"),
            handle=handle,
            name="",
            headline=headline,
            **extra,
        )
        db.add(user)
        db.flush()
    else:
        user.name = ""
        user.headline = user.headline or headline
        if handle and user.handle != handle:
            taken = db.query(User).filter(User.handle == handle, User.id != user.id).first()
            if taken:
                taken.handle = random_handle(db)
            user.handle = handle
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


def _ensure_organizer(db: Session) -> User:
    organizer = _user(db, ORGANIZER_EMAIL, ADMIN_HANDLE, "")
    legacy = db.query(User).filter(User.email == "organizer@mentorwow.app").first()
    if legacy and legacy.id != organizer.id:
        db.query(Event).filter(Event.organizer_id == legacy.id).update({Event.organizer_id: organizer.id})
    if "CEDAT" in (organizer.headline or ""):
        organizer.headline = "Organizer · MentorWow pilot"
    return organizer


def _rename_legacy_pilot(db: Session) -> None:
    row = db.query(Event).filter(Event.slug == "cedat-pilot").first()
    if row is None:
        return
    row.slug = PILOT_SLUG
    row.join_link_token = PILOT_JOIN_TOKEN
    row.name = "MentorWow Pilot Mixer"


def seed_graph(db: Session) -> None:
    if db.query(Event).first():
        _ensure_organizer(db)
        _rename_legacy_pilot(db)
        db.commit()
        return
    now = utcnow()
    organizer = _ensure_organizer(db)
    a = _user(db, "copper.loom@mentorwow.app", "copper-loom", "Product systems")
    b = _user(db, "salt.harbor@mentorwow.app", "salt-harbor", "Staff engineer")
    c = _user(db, "nimbus.kiln@mentorwow.app", "nimbus-kiln", "Designer")
    d = _user(db, "amber.ridge@mentorwow.app", "amber-ridge", "Research → industry")
    _profile(db, a, ["product strategy", "privacy"], ["roadmaps", "0-1 product"], ["fintech collab"])
    _profile(db, b, ["system design", "python", "engineering"], ["staff engineering"], ["technical co-founder", "open source"])
    _profile(db, c, ["design systems", "brand"], ["critique"], ["design partnership"])
    _profile(db, d, ["career", "research"], ["PhD transitions"], ["research collab"])
    event = Event(
        organizer_id=organizer.id,
        name="MentorWow Pilot Mixer",
        slug=PILOT_SLUG,
        join_link_token=PILOT_JOIN_TOKEN,
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
    db.add(
        ChatMessage(
            event_id=event.id,
            author_id=organizer.id,
            kind="poll",
            body="Was this mixer worth showing up for?",
        )
    )
    track(db, "join_event", user_id=a.id, event_id=event.id, properties={"slug": event.slug, "source": "seed"})
    track(db, "query_posted", user_id=a.id, event_id=event.id, properties={"slug": event.slug, "query_type": "skill"})
    track(db, "query_matched", user_id=b.id, event_id=event.id, properties={"slug": event.slug, "query_type": "skill"})
    db.commit()
