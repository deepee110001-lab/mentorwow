import random
import re

from sqlalchemy.orm import Session

HANDLE_RE = re.compile(r"^[a-z][a-z0-9-]{2,23}$")

ADJECTIVES = [
    "copper", "salt", "nimbus", "amber", "quiet", "brine", "cedar", "ivory",
    "umber", "slate", "ember", "pollen", "harbor", "kiln", "moss", "iron",
]
NOUNS = [
    "loom", "harbor", "kiln", "orchard", "anvil", "ridge", "well", "atlas",
    "relay", "grove", "spool", "quarry", "lantern", "current", "hearth", "folio",
]


def valid_handle(handle: str) -> bool:
    return bool(HANDLE_RE.match(handle))


def random_handle(db: Session) -> str:
    from .models import User

    for _ in range(40):
        candidate = f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}"
        if db.query(User).filter(User.handle == candidate).first() is None:
            return candidate
    return f"seat-{random.randint(1000, 9999)}"
