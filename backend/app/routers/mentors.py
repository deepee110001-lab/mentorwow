from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Skill, User, UserSkill
from ..schemas import MentorCard
from ..serializers import to_mentor_card

router = APIRouter(prefix="/api/mentors", tags=["mentors"])


def _mentor_query(db: Session):
    return (
        db.query(User)
        .options(selectinload(User.skills).selectinload(UserSkill.skill))
        .filter(User.role == "mentor")
    )


@router.get("", response_model=list[MentorCard])
def list_mentors(q: str | None = None, skill: str | None = None, db: Session = Depends(get_db)):
    mentors = _mentor_query(db).order_by(User.name).all()
    cards = [to_mentor_card(user, db) for user in mentors]
    if q:
        needle = q.lower()
        cards = [
            card
            for card in cards
            if needle in card.name.lower()
            or needle in card.headline.lower()
            or needle in card.bio.lower()
            or any(needle in item.lower() for item in card.skills)
        ]
    if skill:
        cards = [card for card in cards if skill in card.skills]
    return cards


@router.get("/skills")
def list_skills(db: Session = Depends(get_db)):
    skills = db.query(Skill).order_by(Skill.category, Skill.name).all()
    return [{"name": skill.name, "category": skill.category} for skill in skills]


@router.get("/{mentor_id}", response_model=MentorCard)
def get_mentor(mentor_id: int, db: Session = Depends(get_db)):
    user = _mentor_query(db).filter(User.id == mentor_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Mentor not found")
    return to_mentor_card(user, db)
