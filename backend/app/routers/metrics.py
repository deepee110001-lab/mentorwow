from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_optional_user
from ..metrics import ingest
from ..models import User

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.post("/track")
def track_events(payload: dict, db: Session = Depends(get_db), current: User | None = Depends(get_optional_user)):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    written = ingest(db, payload, current.id if current else None)
    db.commit()
    return {"ok": True, "written": written}
