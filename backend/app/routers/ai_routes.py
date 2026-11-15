from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..ai import match_query, parse_resume, summarize_chat
from ..database import get_db
from ..deps import get_current_user
from ..matching import matchable_members
from ..models import User
from .events import get_event_by_slug
from ..privacy import require_member

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/parse-resume")
async def api_parse_resume(file: UploadFile = File(...), current: User = Depends(get_current_user)):
    data = await file.read()
    return parse_resume(data)


@router.post("/match")
def api_match(payload: dict, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    slug = payload.get("slug")
    event = get_event_by_slug(db, slug)
    require_member(db, event, current)
    members = matchable_members(db, event, current.id)
    return match_query({"type": payload.get("type"), "body": payload.get("body"), "author_id": current.id}, members)


@router.post("/summarize")
def api_summarize(payload: dict, current: User = Depends(get_current_user)):
    messages = payload.get("messages") or []
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="messages array required")
    return {"recap": summarize_chat(messages)}
