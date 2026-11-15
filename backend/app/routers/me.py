from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..guru import join_topics
from ..handles import valid_handle
from ..models import Follow, Project, TopicStat, User
from ..schemas import MeOut, PrivateStats, ProfileUpdate, ProjectIn, PublicProfile, TopicMinutes
from ..serializers import me_out, public_out

router = APIRouter(prefix="/api", tags=["people"])


@router.put("/me", response_model=MeOut)
def update_me(payload: ProfileUpdate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    if payload.handle:
        handle = payload.handle.strip().lower()
        if not valid_handle(handle):
            raise HTTPException(status_code=400, detail="Handle must be 3–24 chars, lowercase")
        taken = db.query(User).filter(User.handle == handle, User.id != current.id).first()
        if taken:
            raise HTTPException(status_code=409, detail="Handle taken")
        current.handle = handle
    if payload.accent:
        current.accent = payload.accent
    db.commit()
    current = db.query(User).options(selectinload(User.projects)).filter(User.id == current.id).one()
    return me_out(current)


@router.get("/me/private", response_model=PrivateStats)
def private_stats(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = db.query(TopicStat).filter(TopicStat.user_id == current.id).all()
    topics = [
        TopicMinutes(
            topic=row.topic,
            given_minutes=round(row.given_seconds / 60, 1),
            received_minutes=round(row.received_seconds / 60, 1),
        )
        for row in rows
    ]
    return PrivateStats(
        guru_balance=current.guru_balance,
        given_minutes=round(sum(row.given_seconds for row in rows) / 60, 1),
        received_minutes=round(sum(row.received_seconds for row in rows) / 60, 1),
        topics=topics,
    )


@router.post("/me/projects", response_model=MeOut)
def add_project(payload: ProjectIn, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    db.add(
        Project(
            user_id=current.id,
            title=payload.title.strip(),
            summary=payload.summary.strip(),
            url=payload.url.strip(),
            topics=join_topics(payload.topics),
        )
    )
    db.commit()
    current = db.query(User).options(selectinload(User.projects)).filter(User.id == current.id).one()
    return me_out(current)


@router.put("/me/projects/{project_id}", response_model=MeOut)
def edit_project(
    project_id: int,
    payload: ProjectIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    item = db.query(Project).filter(Project.id == project_id, Project.user_id == current.id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Project not found")
    item.title = payload.title.strip()
    item.summary = payload.summary.strip()
    item.url = payload.url.strip()
    item.topics = join_topics(payload.topics)
    db.commit()
    current = db.query(User).options(selectinload(User.projects)).filter(User.id == current.id).one()
    return me_out(current)


@router.delete("/me/projects/{project_id}", response_model=MeOut)
def delete_project(project_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    item = db.query(Project).filter(Project.id == project_id, Project.user_id == current.id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(item)
    db.commit()
    current = db.query(User).options(selectinload(User.projects)).filter(User.id == current.id).one()
    return me_out(current)


@router.get("/u/{handle}", response_model=PublicProfile)
def public_profile(
    handle: str,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    user = db.query(User).options(selectinload(User.projects)).filter(User.handle == handle.lower()).first()
    if user is None:
        raise HTTPException(status_code=404, detail="No such handle")
    return public_out(user, db, viewer.id if viewer else None)


@router.post("/u/{handle}/follow")
def follow(handle: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    user = db.query(User).filter(User.handle == handle.lower()).first()
    if user is None:
        raise HTTPException(status_code=404, detail="No such handle")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="You already sit with yourself")
    existing = db.query(Follow).filter(Follow.follower_id == current.id, Follow.followee_id == user.id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"following": False}
    db.add(Follow(follower_id=current.id, followee_id=user.id))
    db.commit()
    return {"following": True}
