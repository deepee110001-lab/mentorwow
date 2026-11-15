from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ProjectIn(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    summary: str = ""
    url: str = ""
    topics: list[str] = []


class ProjectOut(BaseModel):
    id: int
    title: str
    summary: str
    url: str
    topics: list[str]


class PublicProfile(BaseModel):
    handle: str
    accent: str
    projects: list[ProjectOut]
    topics: list[str]
    following: bool = False


class MeOut(BaseModel):
    id: int
    email: str
    handle: str
    name: str = ""
    headline: str = ""
    photo_url: str = ""
    accent: str
    guru_balance: int
    projects: list[ProjectOut] = []


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    handle: str | None = None
    name: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: MeOut


class ProfileUpdate(BaseModel):
    handle: str | None = None
    accent: str | None = None


class TopicMinutes(BaseModel):
    topic: str
    given_minutes: float
    received_minutes: float


class PrivateStats(BaseModel):
    guru_balance: int
    given_minutes: float
    received_minutes: float
    topics: list[TopicMinutes]


class GuruEventOut(BaseModel):
    amount: int
    reason: str
    note: str
    created_at: datetime


class BuyIn(BaseModel):
    pack: str


class PostIn(BaseModel):
    title: str = Field(default="", max_length=180)
    body: str = Field(min_length=4, max_length=4000)
    topic: str = Field(min_length=2, max_length=80)


class PostOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    topic: str
    score: int
    created_at: datetime
    handle: str
    accent: str
    my_vote: int = 0


class QueueIn(BaseModel):
    topic: str = Field(min_length=2, max_length=80)
    side: str = Field(pattern="^(give|seek)$")


class QueueOut(BaseModel):
    status: str
    room_id: str | None = None
    side: str | None = None
    topic: str | None = None
    seconds: int = 300


class CallQuality(BaseModel):
    score: float
    notes: str
    duration_seconds: int
    guru_delta: int
