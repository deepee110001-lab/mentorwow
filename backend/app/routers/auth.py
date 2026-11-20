from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from ..config import ADMIN_HANDLE, GOOGLE_CLIENT_ID, ORGANIZER_EMAIL
from ..database import get_db
from ..deps import get_current_user
from ..handles import random_handle
from ..metrics import track
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut
from ..security import create_access_token, hash_password, verify_password
from ..serializers import me_out

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_query(db: Session):
    return db.query(User).options(selectinload(User.projects))


def _token(db: Session, user: User, is_new: bool) -> TokenOut:
    user = _user_query(db).filter(User.id == user.id).one()
    return TokenOut(access_token=create_access_token(user.id), user=me_out(user), is_new=is_new)


def _create_user(db: Session, email: str, password: str) -> User:
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user = User(
        email=email,
        hashed_password=hash_password(password),
        handle=random_handle(db),
        name="",
        guru_balance=20,
    )
    db.add(user)
    db.flush()
    return user


@router.post("/register", response_model=TokenOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = _create_user(db, email, payload.password)
    track(db, "register_email", user_id=user.id, properties={"method": "email", "is_new": True})
    db.commit()
    return _token(db, user, is_new=True)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    user = _user_query(db).filter(User.email == email).first()
    if user is None:
        user = _create_user(db, email, payload.password)
        track(db, "register_email", user_id=user.id, properties={"method": "email", "is_new": True})
        db.commit()
        return _token(db, user, is_new=True)
    if not user.hashed_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Continue with Google")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    track(db, "login_email", user_id=user.id, properties={"method": "email", "is_new": False})
    db.commit()
    return _token(db, user, is_new=False)


@router.get("/me")
def me(current: User = Depends(get_current_user)):
    return me_out(current)


@router.get("/config")
def auth_config():
    return {
        "google_client_id": GOOGLE_CLIENT_ID,
        "google_enabled": bool(GOOGLE_CLIENT_ID),
        "default_provider": "google" if GOOGLE_CLIENT_ID else "email",
    }


def verify_google_credential(credential: str) -> dict:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google sign-in is not configured")
    if not credential or not isinstance(credential, str) or len(credential) > 4096:
        raise HTTPException(status_code=400, detail="Google credential required")
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=401, detail="Invalid Google credential") from exc
    if info.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=401, detail="Invalid Google issuer")
    email = (info.get("email") or "").lower().strip()
    if not email or not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account email is not verified")
    return info


def _upsert_google_user(db: Session, info: dict) -> tuple[User, bool]:
    sub = str(info.get("sub") or "")
    email = (info.get("email") or "").lower().strip()
    user = None
    if sub:
        user = db.query(User).filter(User.google_sub == sub).first()
    if user is None and email:
        user = db.query(User).filter(User.email == email).first()
    if user is None:
        handle = ADMIN_HANDLE if email == ORGANIZER_EMAIL else random_handle(db)
        if email == ORGANIZER_EMAIL:
            taken = db.query(User).filter(User.handle == handle).first()
            if taken:
                taken.handle = random_handle(db)
        user = User(
            email=email,
            hashed_password="",
            handle=handle,
            name="",
            google_sub=sub or None,
            guru_balance=20,
        )
        db.add(user)
        db.flush()
        return user, True
    user.google_sub = sub or user.google_sub
    user.name = ""
    if email and user.email != email:
        taken = db.query(User).filter(User.email == email, User.id != user.id).first()
        if taken is None:
            user.email = email
    if email == ORGANIZER_EMAIL:
        taken = db.query(User).filter(User.handle == ADMIN_HANDLE, User.id != user.id).first()
        if taken:
            taken.handle = random_handle(db)
        user.handle = ADMIN_HANDLE
    return user, False


@router.post("/google", response_model=TokenOut)
def google_login(payload: dict, db: Session = Depends(get_db)):
    credential = payload.get("credential") if isinstance(payload, dict) else None
    info = verify_google_credential(credential or "")
    user, is_new = _upsert_google_user(db, info)
    track(db, "login_google", user_id=user.id, properties={"method": "google", "is_new": is_new})
    db.commit()
    return _token(db, user, is_new=is_new)


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
    user = db.query(User).filter((User.linkedin_sub == sub) | (User.email == email)).first()
    if user is None:
        user = User(
            email=email or f"{sub}@linkedin.local",
            hashed_password="",
            handle=random_handle(db),
            name="",
            linkedin_sub=sub,
        )
        db.add(user)
    else:
        user.linkedin_sub = sub
    db.commit()
    db.refresh(user)
    jwt_token = create_access_token(user.id)
    return RedirectResponse(f"{APP_URL}/login?linkedin_token={jwt_token}")
