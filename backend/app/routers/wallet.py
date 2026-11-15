from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import GURU_PACKS
from ..database import get_db
from ..deps import get_current_user
from ..guru import credit
from ..models import GuruEvent, User
from ..schemas import BuyIn, GuruEventOut

router = APIRouter(prefix="/api/guru", tags=["guru"])


@router.get("/ledger", response_model=list[GuruEventOut])
def ledger(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = (
        db.query(GuruEvent)
        .filter(GuruEvent.user_id == current.id)
        .order_by(GuruEvent.created_at.desc())
        .limit(50)
        .all()
    )
    return rows


@router.get("/packs")
def packs():
    return [{"id": key, "guru": value} for key, value in GURU_PACKS.items()]


@router.post("/buy")
def buy(payload: BuyIn, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    amount = GURU_PACKS.get(payload.pack)
    if amount is None:
        raise HTTPException(status_code=400, detail="Unknown pack")
    credit(db, current, amount, "buy", f"pack {payload.pack}")
    db.commit()
    db.refresh(current)
    return {"guru_balance": current.guru_balance, "added": amount}
