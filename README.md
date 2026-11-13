# MentorWow

A mentorship atelier: React frontend, FastAPI backend. Browse practitioners, send a specific ask, accept matches, and book sessions.

## Stack

- **Frontend:** React 19, Vite, TypeScript, React Router
- **Backend:** FastAPI, SQLAlchemy, SQLite, JWT auth

## Run locally

Use two terminals.

```bash
# backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
# frontend
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` to the FastAPI app.

## Demo accounts

Password for all seeded users: `mentorwow`

| Role   | Email                 |
|--------|-----------------------|
| Mentee | mentee@mentorwow.app  |
| Mentor | amara@mentorwow.app   |

The first API start creates `backend/mentorwow.db` and seeds eight mentors, a mentee, an accepted match, and sample sessions.

## What you can do

- Register as a mentee or mentor and edit your studio
- Filter the atelier by craft
- Send, accept, decline, or withdraw mentorship requests
- Book sessions once a request is accepted
- Leave notes on completed sessions
