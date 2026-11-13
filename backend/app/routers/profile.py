from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import User, UserSkill
from ..schemas import ProfileUpdate, UserPublic
from ..serializers import set_user_skills, to_public

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.put("", response_model=UserPublic)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    skills = data.pop("skills", None)
    for key, value in data.items():
        setattr(current, key, value)
    if skills is not None:
        kind = "teaching" if current.role == "mentor" else "learning"
        set_user_skills(db, current, skills, kind)
    db.commit()
    current = (
        db.query(User)
        .options(selectinload(User.skills).selectinload(UserSkill.skill))
        .filter(User.id == current.id)
        .one()
    )
    return to_public(current)
