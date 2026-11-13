from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import MentorshipRequest, User
from ..schemas import RequestCreate, RequestOut, RequestStatusIn
from ..serializers import to_request

router = APIRouter(prefix="/api/requests", tags=["requests"])


def _with_people(db: Session):
    return db.query(MentorshipRequest).options(
        selectinload(MentorshipRequest.mentee),
        selectinload(MentorshipRequest.mentor),
    )


@router.get("", response_model=list[RequestOut])
def list_requests(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    items = (
        _with_people(db)
        .filter(
            (MentorshipRequest.mentee_id == current.id)
            | (MentorshipRequest.mentor_id == current.id)
        )
        .order_by(MentorshipRequest.created_at.desc())
        .all()
    )
    return [to_request(item) for item in items]


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if current.role != "mentee":
        raise HTTPException(status_code=400, detail="Only mentees can send mentorship requests")
    mentor = db.query(User).filter(User.id == payload.mentor_id, User.role == "mentor").first()
    if mentor is None:
        raise HTTPException(status_code=404, detail="Mentor not found")
    if mentor.id == current.id:
        raise HTTPException(status_code=400, detail="You cannot request yourself")
    existing = (
        db.query(MentorshipRequest)
        .filter(
            MentorshipRequest.mentee_id == current.id,
            MentorshipRequest.mentor_id == mentor.id,
            MentorshipRequest.status.in_(["pending", "accepted"]),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="You already have an open request with this mentor")
    item = MentorshipRequest(
        mentee_id=current.id,
        mentor_id=mentor.id,
        goal=payload.goal.strip(),
        message=payload.message.strip(),
    )
    db.add(item)
    db.commit()
    item = _with_people(db).filter(MentorshipRequest.id == item.id).one()
    return to_request(item)


@router.patch("/{request_id}", response_model=RequestOut)
def update_request(
    request_id: int,
    payload: RequestStatusIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    item = _with_people(db).filter(MentorshipRequest.id == request_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if payload.status == "withdrawn":
        if item.mentee_id != current.id:
            raise HTTPException(status_code=403, detail="Only the mentee can withdraw")
        if item.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending requests can be withdrawn")
    else:
        if item.mentor_id != current.id:
            raise HTTPException(status_code=403, detail="Only the mentor can accept or decline")
        if item.status != "pending":
            raise HTTPException(status_code=400, detail="This request is no longer pending")
    item.status = payload.status
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return to_request(item)
