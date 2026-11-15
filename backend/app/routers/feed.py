from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..models import Follow, Post, User, Vote
from ..schemas import PostIn, PostOut
from ..serializers import post_out

router = APIRouter(prefix="/api", tags=["feed"])


@router.get("/topics")
def topics(db: Session = Depends(get_db)):
    rows = db.query(Post.topic).distinct().order_by(Post.topic).all()
    return [row[0] for row in rows if row[0]]


@router.get("/feed", response_model=list[PostOut])
def feed(
    topic: str | None = None,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    query = db.query(Post).options(selectinload(Post.author)).order_by(Post.created_at.desc())
    if topic:
        query = query.filter(Post.topic == topic)
    elif viewer:
        followed = [row.followee_id for row in db.query(Follow).filter(Follow.follower_id == viewer.id)]
        if followed:
            query = query.filter((Post.author_id.in_(followed)) | (Post.author_id == viewer.id))
    items = query.limit(80).all()
    return [post_out(item, db, viewer.id if viewer else None) for item in items]


@router.post("/posts", response_model=PostOut)
def create_post(payload: PostIn, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    item = Post(
        author_id=current.id,
        kind="post",
        title=payload.title.strip(),
        body=payload.body.strip(),
        topic=payload.topic.strip().lower(),
    )
    db.add(item)
    db.commit()
    item = db.query(Post).options(selectinload(Post.author)).filter(Post.id == item.id).one()
    return post_out(item, db, current.id)


@router.post("/posts/{post_id}/vote", response_model=PostOut)
def vote_post(post_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    item = db.query(Post).options(selectinload(Post.author)).filter(Post.id == post_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Post not found")
    row = db.query(Vote).filter(Vote.user_id == current.id, Vote.post_id == post_id).first()
    if row:
        item.score -= row.value
        db.delete(row)
    else:
        db.add(Vote(user_id=current.id, post_id=post_id, value=1))
        item.score += 1
    db.commit()
    item = db.query(Post).options(selectinload(Post.author)).filter(Post.id == post_id).one()
    return post_out(item, db, current.id)
