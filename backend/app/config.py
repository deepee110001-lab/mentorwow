from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'mentorwow.db'}"
SECRET_KEY = "mentorwow-dev-secret-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
