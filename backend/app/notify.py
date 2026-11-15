from sqlalchemy.orm import Session

from .config import APP_URL, EMAIL_PROVIDER_KEY
from .models import Notification, utcnow


def notify(db: Session, user_id: int, title: str, body: str, link: str = "") -> None:
    db.add(Notification(user_id=user_id, title=title, body=body, link=link, created_at=utcnow()))
    send_email_stub(user_id, title, body, link)


def send_email_stub(user_id: int, title: str, body: str, link: str) -> None:
    # TODO: wire EMAIL_PROVIDER_KEY (Resend/Postmark/Supabase) when set.
    if not EMAIL_PROVIDER_KEY:
        print(f"[email-stub] user={user_id} {title} {APP_URL}{link}")
        return
    print(f"[email] provider configured, would send to user={user_id}: {title}")
