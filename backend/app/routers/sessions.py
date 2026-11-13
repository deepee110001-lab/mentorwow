from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import MentorshipRequest, Session as MentorshipSession, User
from ..schemas import SessionCreate, SessionOut, SessionUpdate
from ..serializers import to_session

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _with_people(db: Session):
    return db.query(MentorshipSession).options(
        selectinload(MentorshipSession.mentee),
        selectinload(MentorshipSession.mentor),
    )


@router.get("", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    items = (
        _with_people(db)
        .filter(
            (MentorshipSession.mentee_id == current.id)
            | (MentorshipSession.mentor_id == current.id)
        )
        .order_by(MentorshipSession.scheduled_at.desc())
        .all()
    )
    return [to_session(item) for item in items]


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    peer = db.query(User).filter(User.id == payload.peer_id).first()
    if peer is None:
        raise HTTPException(status_code=404, detail="Person not found")
    if current.role == "mentor":
        mentor, mentee = current, peer
    else:
        mentee, mentor = current, peer
    if mentee.role != "mentee" or mentor.role != "mentor":
        raise HTTPException(status_code=400, detail="Sessions are between a mentor and a mentee")
    accepted = (
        db.query(MentorshipRequest)
        .filter(
            MentorshipRequest.mentee_id == mentee.id,
            MentorshipRequest.mentor_id == mentor.id,
            MentorshipRequest.status == "accepted",
        )
        .first()
    )
    if accepted is None:
        raise HTTPException(status_code=400, detail="You need an accepted mentorship before booking")
    item = MentorshipSession(
        request_id=payload.request_id or accepted.id,
        mentee_id=mentee.id,
        mentor_id=mentor.id,
        title=payload.title.strip(),
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
    )
    db.add(item)
    db.commit()
    item = _with_people(db).filter(MentorshipSession.id == item.id).one()
    return to_session(item)


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(
    session_id: int,
    payload: SessionUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    item = _with_people(db).filter(MentorshipSession.id == session_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if current.id not in {item.mentee_id, item.mentor_id}:
        raise HTTPException(status_code=403, detail="Not your session")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return to_session(item)
