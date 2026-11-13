from sqlalchemy.orm import Session

from .models import MentorshipRequest, Session as MentorshipSession, User, UserSkill
from .schemas import MentorCard, PersonBrief, RequestOut, SessionOut, UserPublic


def skill_names(user: User, kind: str | None = "teaching") -> list[str]:
    names = []
    for item in user.skills:
        if kind is None or item.kind == kind:
            names.append(item.skill.name)
    return names


def to_public(user: User) -> UserPublic:
    kind = "teaching" if user.role == "mentor" else "learning"
    return UserPublic(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        headline=user.headline,
        bio=user.bio,
        location=user.location,
        availability=user.availability,
        years_experience=user.years_experience,
        accent=user.accent,
        skills=skill_names(user, kind),
    )


def to_brief(user: User) -> PersonBrief:
    return PersonBrief(id=user.id, name=user.name, headline=user.headline, accent=user.accent)


def to_mentor_card(user: User, db: Session) -> MentorCard:
    mentee_count = (
        db.query(MentorshipRequest)
        .filter(
            MentorshipRequest.mentor_id == user.id,
            MentorshipRequest.status == "accepted",
        )
        .count()
    )
    return MentorCard(
        id=user.id,
        name=user.name,
        role=user.role,
        headline=user.headline,
        bio=user.bio,
        location=user.location,
        availability=user.availability,
        years_experience=user.years_experience,
        accent=user.accent,
        skills=skill_names(user, "teaching"),
        mentee_count=mentee_count,
    )


def to_request(item: MentorshipRequest) -> RequestOut:
    return RequestOut(
        id=item.id,
        mentee=to_brief(item.mentee),
        mentor=to_brief(item.mentor),
        goal=item.goal,
        message=item.message,
        status=item.status,
        created_at=item.created_at,
    )


def to_session(item: MentorshipSession) -> SessionOut:
    return SessionOut(
        id=item.id,
        mentee=to_brief(item.mentee),
        mentor=to_brief(item.mentor),
        title=item.title,
        scheduled_at=item.scheduled_at,
        duration_minutes=item.duration_minutes,
        status=item.status,
        notes=item.notes,
    )


def set_user_skills(db: Session, user: User, names: list[str], kind: str) -> None:
    from .models import Skill

    existing = [item for item in user.skills if item.kind == kind]
    for item in existing:
        db.delete(item)
    db.flush()
    for name in names:
        skill = db.query(Skill).filter(Skill.name == name).first()
        if skill is None:
            skill = Skill(name=name, category="Custom")
            db.add(skill)
            db.flush()
        db.add(UserSkill(user_id=user.id, skill_id=skill.id, kind=kind))
