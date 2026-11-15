import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'mentorwow.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "mentorwow-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
CORS_ORIGINS = [
    os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
    "http://127.0.0.1:5173",
]
APP_URL = os.getenv("NEXT_PUBLIC_APP_URL", os.getenv("APP_URL", "http://localhost:5173"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
LINKEDIN_REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/auth/linkedin/callback"
)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
EMAIL_PROVIDER_KEY = os.getenv("EMAIL_PROVIDER_KEY", "")
PILOT_GATE = os.getenv("PILOT_GATE", "mentorwow")
STORAGE_DIR = BASE_DIR / "storage" / "resumes"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
CALL_SECONDS = 5 * 60
GURU_SEEK_COST = 5
GURU_PACKS = {"starter": 20, "stack": 50, "bundle": 120}
OUTGOING_QUERY_LIMIT = 2
INCOMING_PENDING_LIMIT = 5
