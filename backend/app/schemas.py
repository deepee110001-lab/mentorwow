from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: int
    email: str
    name: str
    role: str
    headline: str
    bio: str
    location: str
    availability: str
    years_experience: int
    accent: str
    skills: list[str] = []

    model_config = {"from_attributes": True}


class MentorCard(BaseModel):
    id: int
    name: str
    role: str
    headline: str
    bio: str
    location: str
    availability: str
    years_experience: int
    accent: str
    skills: list[str]
    mentee_count: int = 0


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2, max_length=120)
    role: str = Field(pattern="^(mentee|mentor)$")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class ProfileUpdate(BaseModel):
    name: str | None = None
    role: str | None = Field(default=None, pattern="^(mentee|mentor)$")
    headline: str | None = None
    bio: str | None = None
    location: str | None = None
    availability: str | None = None
    years_experience: int | None = None
    skills: list[str] | None = None


class RequestCreate(BaseModel):
    mentor_id: int
    goal: str = Field(min_length=4, max_length=240)
    message: str = Field(min_length=10, max_length=2000)


class PersonBrief(BaseModel):
    id: int
    name: str
    headline: str
    accent: str


class RequestOut(BaseModel):
    id: int
    mentee: PersonBrief
    mentor: PersonBrief
    goal: str
    message: str
    status: str
    created_at: datetime


class RequestStatusIn(BaseModel):
    status: str = Field(pattern="^(accepted|declined|withdrawn)$")


class SessionCreate(BaseModel):
    request_id: int | None = None
    peer_id: int
    title: str = Field(min_length=4, max_length=180)
    scheduled_at: datetime
    duration_minutes: int = Field(default=45, ge=15, le=180)


class SessionOut(BaseModel):
    id: int
    mentee: PersonBrief
    mentor: PersonBrief
    title: str
    scheduled_at: datetime
    duration_minutes: int
    status: str
    notes: str


class SessionUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(scheduled|completed|cancelled)$")
    notes: str | None = None
    title: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
