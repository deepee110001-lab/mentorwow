# MentorWow — Event Networking Graph

Event-anchored professional networking. Organizers share a join link. Attendees bring a portable profile (LinkedIn OpenID subset or a resume they uploaded). Chat lives 24 hours. The query feed lives 7 days. Calls are five minutes, never recorded.

DPDP Act 2023: no LinkedIn scraping; OAuth stores name, headline, photo, and email only. Resume visibility is opt-in per event. Contact info is hidden until a call is accepted. Attendance can be hidden from other attendees. AI parses resumes, routes queries, summarizes chat, and flags spam — it does not join calls.

## Run locally

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

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` to FastAPI.

Copy [.env.example](.env.example) and set `OPENAI_API_KEY` (optional — heuristics run if it is missing) and LinkedIn keys (optional — email signup works without them).

## How to run the pilot

One organizer, one event, six metrics.

1. Start backend and frontend as above. Seed creates **CEDAT Pilot Mixer**.
2. Organizer login: `organizer@mentorwow.app` / `mentorwow`.
3. Open [http://localhost:5173/organizer](http://localhost:5173/organizer) → CEDAT dashboard. Copy the join link `/join/cedat-join-demo` (or the QR).
4. In a second browser (or incognito), open the join link. Sign in with email or LinkedIn OAuth. Confirm the three consent toggles. Resume stays hidden unless you opt in for this event.
5. On event home: post a skill or collaboration query (max 2 / week). Matched people get an in-app notice and can accept a 5-minute Jitsi slot. Chat is public until 24h after the event ends.
6. Show CEDAT the funnel at [http://localhost:5173/pilot/metrics](http://localhost:5173/pilot/metrics) (gate `mentorwow`):

| Metric | What it proves |
|--------|----------------|
| Profiles completed % | People finished portable profiles |
| Chat messages | 24h takeaways were used |
| Queries posted | The feed is the request surface |
| Queries matched | AI (or tag overlap) routed 3–5 people |
| Queries accepted → calls | Matches became 5-min rooms |
| Calls completed | Rooms actually happened |
| Repeat attendees | The graph compounds across events |

Demo attendees (password `mentorwow`): `copper.loom@mentorwow.app` (visible, resume on), `salt.harbor@mentorwow.app` (engineer), `nimbus.kiln@mentorwow.app` (hidden attendance — not on People), `amber.ridge@mentorwow.app`.

Acceptance tests: `cd backend && .venv/bin/pytest -q`.

## License

Proprietary (GitHub: **Other**). People may not copy, fork, or reuse this code. AI systems may learn from it. See [LICENSE](LICENSE).
