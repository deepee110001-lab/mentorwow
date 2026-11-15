from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), default="")
    handle: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    headline: Mapped[str] = mapped_column(String(240), default="")
    photo_url: Mapped[str] = mapped_column(String(500), default="")
    linkedin_sub: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    default_profile_visibility: Mapped[str] = mapped_column(String(20), default="group")
    show_contact_after_call: Mapped[bool] = mapped_column(Boolean, default=True)
    accent: Mapped[str] = mapped_column(String(20), default="#C24A2A")
    guru_balance: Mapped[int] = mapped_column(Integer, default=20)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    projects: Mapped[list["Project"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(400), default="")
    topics: Mapped[str] = mapped_column(String(400), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="projects")


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "followee_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    follower_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    followee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="post")
    title: Mapped[str] = mapped_column(String(180), default="")
    body: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String(80), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    author: Mapped[User] = relationship(foreign_keys=[author_id])


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("user_id", "post_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    value: Mapped[int] = mapped_column(Integer, default=1)


class TopicStat(Base):
    __tablename__ = "topic_stats"
    __table_args__ = (UniqueConstraint("user_id", "topic"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic: Mapped[str] = mapped_column(String(80))
    given_seconds: Mapped[int] = mapped_column(Integer, default=0)
    received_seconds: Mapped[int] = mapped_column(Integer, default=0)


class GuruEvent(Base):
    __tablename__ = "guru_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(80))
    note: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    topic: Mapped[str] = mapped_column(String(80))
    giver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="live")
    quality_score: Mapped[float] = mapped_column(Float, default=0)
    quality_notes: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)


class Profile(Base):
    __tablename__ = "net_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    skill_tags: Mapped[str] = mapped_column(Text, default="[]")
    can_advise_on: Mapped[str] = mapped_column(Text, default="[]")
    open_to_collaborate_on: Mapped[str] = mapped_column(Text, default="[]")
    resume_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resume_visible_default: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship()


class Event(Base):
    __tablename__ = "net_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    join_link_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    chat_opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    chat_closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    feed_closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="live")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organizer: Mapped[User] = relationship()


class EventMember(Base):
    __tablename__ = "net_event_members"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("net_events.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    attendance_visibility: Mapped[str] = mapped_column(String(20), default="visible")
    resume_visible_this_event: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_join: Mapped[bool] = mapped_column(Boolean, default=False)
    show_contact_after_call: Mapped[bool] = mapped_column(Boolean, default=True)

    event: Mapped[Event] = relationship()
    user: Mapped[User] = relationship()


class Query(Base):
    __tablename__ = "net_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("net_events.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(String(280))
    available_slots: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship()
    event: Mapped[Event] = relationship()


class QueryMatch(Base):
    __tablename__ = "net_query_matches"
    __table_args__ = (UniqueConstraint("query_id", "matched_user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("net_queries.id"), index=True)
    matched_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response: Mapped[str] = mapped_column(String(20), default="pending")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(String(240), default="")

    query: Mapped[Query] = relationship()
    matched_user: Mapped[User] = relationship()


class EventCall(Base):
    __tablename__ = "net_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int | None] = mapped_column(ForeignKey("net_queries.id"), nullable=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    responder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=5)
    meeting_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    feedback_requester: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_responder: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    responder: Mapped[User] = relationship(foreign_keys=[responder_id])


class ChatMessage(Base):
    __tablename__ = "net_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("net_events.id"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("net_chat_messages.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    author: Mapped[User | None] = relationship()


class AuditLog(Base):
    __tablename__ = "net_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    target_type: Mapped[str] = mapped_column(String(80), default="")
    target_id: Mapped[str] = mapped_column(String(80), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "net_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(240), default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

