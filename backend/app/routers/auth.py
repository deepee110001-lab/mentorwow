from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..handles import random_handle, valid_handle
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut
from ..security import create_access_token, hash_password, verify_password
from ..serializers import me_out

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_query(db: Session):
    return db.query(User).options(selectinload(User.projects))


@router.post("/register", response_model=TokenOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    handle = (payload.handle or "").strip().lower()
    if handle:
        if not valid_handle(handle):
            raise HTTPException(status_code=400, detail="Handle must be 3–24 chars, lowercase, start with a letter")
        if db.query(User).filter(User.handle == handle).first():
            raise HTTPException(status_code=409, detail="Handle taken")
    else:
        handle = random_handle(db)
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        handle=handle,
        name=(payload.name or "").strip(),
        guru_balance=20,
    )
    db.add(user)
    db.commit()
    user = _user_query(db).filter(User.id == user.id).one()
    return TokenOut(access_token=create_access_token(user.id), user=me_out(user))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = _user_query(db).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenOut(access_token=create_access_token(user.id), user=me_out(user))


@router.get("/me")
def me(current: User = Depends(get_current_user)):
    return me_out(current)


@router.post("/magic-link")
def magic_link(payload: dict, db: Session = Depends(get_db)):
    email = (payload.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    from ..config import EMAIL_PROVIDER_KEY
    from ..security import create_access_token

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        handle = random_handle(db)
        user = User(email=email, hashed_password="", handle=handle, name=email.split("@")[0])
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(user.id)
    # TODO: send via Supabase/email when EMAIL_PROVIDER_KEY is set
    return {"ok": True, "dev_token": token if not EMAIL_PROVIDER_KEY else None}


@router.get("/linkedin")
def linkedin_start():
    from fastapi.responses import RedirectResponse

    from ..config import APP_URL, LINKEDIN_CLIENT_ID, LINKEDIN_REDIRECT_URI

    if not LINKEDIN_CLIENT_ID:
        return RedirectResponse(f"{APP_URL}/login?error=linkedin_not_configured")
    import urllib.parse

    qs = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": LINKEDIN_CLIENT_ID,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "scope": "openid profile email",
            "state": "mentorwow",
        }
    )
    return RedirectResponse(f"https://www.linkedin.com/oauth/v2/authorization?{qs}")


@router.get("/linkedin/callback")
def linkedin_callback(code: str = "", db: Session = Depends(get_db)):
    from ..config import LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REDIRECT_URI, APP_URL
    import httpx
    from fastapi.responses import RedirectResponse

    if not LINKEDIN_CLIENT_ID:
        raise HTTPException(status_code=501, detail="LinkedIn OAuth not configured")
    token_res = httpx.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "client_id": LINKEDIN_CLIENT_ID,
            "client_secret": LINKEDIN_CLIENT_SECRET,
        },
        timeout=20,
    )
    token_res.raise_for_status()
    access = token_res.json().get("access_token")
    info = httpx.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access}"},
        timeout=20,
    ).json()
    sub = info.get("sub")
    email = (info.get("email") or "").lower()
    name = info.get("name") or ""
    picture = info.get("picture") or ""
    headline = ""  # OpenID userinfo does not include full LinkedIn profile; DPDP: do not fetch more
    user = db.query(User).filter((User.linkedin_sub == sub) | (User.email == email)).first()
    if user is None:
        user = User(
            email=email or f"{sub}@linkedin.local",
            hashed_password="",
            handle=random_handle(db),
            name=name,
            photo_url=picture,
            linkedin_sub=sub,
            headline=headline,
        )
        db.add(user)
    else:
        user.linkedin_sub = sub
        if name:
            user.name = name
        if picture:
            user.photo_url = picture
    db.commit()
    db.refresh(user)
    jwt_token = create_access_token(user.id)
    return RedirectResponse(f"{APP_URL}/login?linkedin_token={jwt_token}")
