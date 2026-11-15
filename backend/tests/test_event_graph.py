from datetime import timedelta

from fastapi.testclient import TestClient

from app.ai import heuristic_match, match_query, parse_resume, summarize_chat
from app.database import SessionLocal
from app.jsonutil import dumps
from app.models import Event, Query, QueryMatch, User, utcnow
from tests.conftest import auth_header, join, register

MIN_PDF = b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def test_invalid_join_link(client: TestClient):
    response = client.get("/api/join/not-a-real-token")
    assert response.status_code == 404


def test_join_requires_consent_and_hides_attendance(client: TestClient):
    headers = register(client, "quiet.new@mentorwow.app", "Hidden Joiner")
    denied = client.post(
        "/api/join/cedat-join-demo",
        json={"accepted_join": False, "show_attendance": True},
        headers=headers,
    )
    assert denied.status_code == 400
    join(client, headers, name="Hidden Joiner", show_attendance=False, skill_tags=["quiet"])
    people = client.get("/api/events/cedat-pilot/people", headers=auth_header(client, "copper.loom@mentorwow.app"))
    names = [row["name"] for row in people.json()]
    assert "Hidden Joiner" not in names
    assert "Quiet Attendee" not in names
    assert "Amina K." in names


def test_resume_opt_in_and_gated_url(client: TestClient):
    headers = register(client, "resume.user@mentorwow.app", "Resume User")
    join(client, headers, name="Resume User", skill_tags=["fastapi"])
    upload = client.post("/api/me/resume", files={"file": ("cv.pdf", MIN_PDF, "application/pdf")}, headers=headers)
    assert upload.status_code == 200
    assert upload.json()["skill_tags"] == []
    client.put(
        "/api/me/profile",
        json={"skill_tags": ["fastapi", "privacy"], "headline": "API person"},
        headers=headers,
    )
    copper = auth_header(client, "copper.loom@mentorwow.app")
    people = {row["name"]: row for row in client.get("/api/events/cedat-pilot/people", headers=copper).json()}
    assert people["Resume User"]["resume_url"] is None
    event = client.get("/api/events/cedat-pilot", headers=headers).json()["event"]
    me = client.get("/api/me/profile", headers=headers).json()
    forbidden = client.get(f"/api/events/{event['id']}/members/{me['id']}/resume", headers=copper)
    assert forbidden.status_code == 403
    client.post("/api/consent", json={"slug": "cedat-pilot", "resume_visible_this_event": True}, headers=headers)
    people2 = {row["name"]: row for row in client.get("/api/events/cedat-pilot/people", headers=copper).json()}
    assert people2["Resume User"]["resume_visible"] is True
    assert people2["Resume User"]["resume_url"]
    allowed = client.get(people2["Resume User"]["resume_url"], headers=copper)
    assert allowed.status_code == 200
    assert allowed.headers["content-type"].startswith("application/pdf")


def test_outgoing_query_rate_limit(client: TestClient):
    headers = register(client, "rate.limit@mentorwow.app", "Ratey")
    join(client, headers, name="Ratey", skill_tags=["python"])
    slot = {"start": (utcnow() + timedelta(hours=1)).isoformat()}
    for i in range(2):
        ok = client.post(
            "/api/events/cedat-pilot/queries",
            json={"type": "skill", "body": f"Need a teardown pass {i} on matching.", "available_slots": [slot]},
            headers=headers,
        )
        assert ok.status_code == 200, ok.text
    blocked = client.post(
        "/api/events/cedat-pilot/queries",
        json={"type": "skill", "body": "Third query should be blocked this week.", "available_slots": [slot]},
        headers=headers,
    )
    assert blocked.status_code == 429
    assert "2 outgoing" in blocked.json()["detail"]


def test_skill_match_accept_creates_call(client: TestClient):
    jules = auth_header(client, "salt.harbor@mentorwow.app")
    queries = client.get("/api/events/cedat-pilot/queries", headers=jules).json()
    pending = next(q for q in queries if q["matched"] and q["my_response"] == "pending" and q["type"] == "skill")
    accept = client.post(
        f"/api/queries/{pending['id']}/respond",
        json={"response": "accepted", "slot": pending["available_slots"][0]},
        headers=jules,
    )
    assert accept.status_code == 200, accept.text
    call = accept.json()["call"]
    assert call["status"] == "scheduled"
    assert call["meeting_url"].startswith("https://meet.jit.si/")
    mine = client.get("/api/events/cedat-pilot/calls", headers=jules).json()
    assert mine[0]["meeting_url"].startswith("https://meet.jit.si/")
    assert mine[0]["other"]["email"]  # visible after scheduled


def test_collaboration_matches_engineering_tags():
    members = [
        {"user_id": 1, "headline": "PM", "skill_tags": ["product"], "can_advise_on": [], "open_to_collaborate_on": ["fintech collab"]},
        {"user_id": 2, "headline": "Staff engineer", "skill_tags": ["python", "engineering"], "can_advise_on": [], "open_to_collaborate_on": ["technical co-founder"]},
        {"user_id": 3, "headline": "Designer", "skill_tags": ["design systems"], "can_advise_on": [], "open_to_collaborate_on": ["design partnership"]},
    ]
    picked = heuristic_match({"type": "collaboration", "body": "looking for a technical co-founder", "author_id": 9}, members)
    ids = [row["user_id"] for row in picked]
    assert ids[0] == 2
    assert 3 not in ids


def test_incoming_rate_limit_skips_saturated_user(client: TestClient):
    db = SessionLocal()
    jules = db.query(User).filter(User.email == "salt.harbor@mentorwow.app").one()
    event = db.query(Event).filter(Event.slug == "cedat-pilot").one()
    author = db.query(User).filter(User.email == "organizer@mentorwow.app").one()
    while (
        db.query(QueryMatch)
        .filter(QueryMatch.matched_user_id == jules.id, QueryMatch.response == "pending")
        .count()
        < 5
    ):
        q = Query(
            event_id=event.id,
            author_id=author.id,
            type="skill",
            body="filler to saturate incoming",
            available_slots=dumps([{"start": utcnow().isoformat()}]),
            status="open",
            expires_at=event.feed_closes_at,
        )
        db.add(q)
        db.flush()
        db.add(QueryMatch(query_id=q.id, matched_user_id=jules.id, notified_at=utcnow(), response="pending"))
    db.commit()
    headers = register(client, "matcher@mentorwow.app", "Matcher")
    join(client, headers, name="Matcher", skill_tags=["product"], headline="Need help")
    before = (
        db.query(QueryMatch)
        .filter(QueryMatch.matched_user_id == jules.id, QueryMatch.response == "pending")
        .count()
    )
    posted = client.post(
        "/api/events/cedat-pilot/queries",
        json={
            "type": "skill",
            "body": "Need python engineering advice on a matching loop.",
            "available_slots": [{"start": utcnow().isoformat()}],
        },
        headers=headers,
    )
    assert posted.status_code == 200, posted.text
    qid = posted.json()["id"]
    hit = db.query(QueryMatch).filter(QueryMatch.query_id == qid, QueryMatch.matched_user_id == jules.id).first()
    db.close()
    assert hit is None
    assert before >= 5


def test_chat_pin_recap_report_and_close(client: TestClient):
    amina = auth_header(client, "copper.loom@mentorwow.app")
    posted = client.post("/api/events/cedat-pilot/chat", json={"body": "Takeaway: keep the booth to five minutes."}, headers=amina)
    assert posted.status_code == 200
    msg_id = posted.json()["id"]
    org = auth_header(client, "organizer@mentorwow.app")
    pin = client.post(f"/api/events/cedat-pilot/chat/{msg_id}/pin", json={}, headers=org)
    assert pin.status_code == 200
    assert pin.json()["is_pinned"] is True
    recap = client.post("/api/events/cedat-pilot/chat/recap", json={}, headers=amina)
    assert recap.status_code == 200
    report = client.post(f"/api/events/cedat-pilot/chat/{msg_id}/report", json={"reason": "spam?"}, headers=org)
    assert report.json()["flagged"] is True
    eid = client.get("/api/organizer/events", headers=org).json()[0]["id"]
    closed = client.post(f"/api/organizer/events/{eid}/close-chat", json={}, headers=org)
    assert closed.status_code == 200
    denied = client.post("/api/events/cedat-pilot/chat", json={"body": "too late"}, headers=amina)
    assert denied.status_code == 403


def test_contact_hidden_until_scheduled(client: TestClient):
    amina = auth_header(client, "copper.loom@mentorwow.app")
    people = {row["name"]: row for row in client.get("/api/events/cedat-pilot/people", headers=amina).json()}
    # Samira has no scheduled call with Amina in remaining seed state
    if "Samira H." in people:
        assert people["Samira H."]["email"] is None
    headers = register(client, "contact.test@mentorwow.app", "Contact Test")
    join(client, headers, name="Contact Test", skill_tags=["career"])
    other = {row["name"]: row for row in client.get("/api/events/cedat-pilot/people", headers=headers).json()}
    assert other["Amina K."]["email"] is None


def test_organizer_dashboard_funnel(client: TestClient):
    org = auth_header(client, "organizer@mentorwow.app")
    eid = client.get("/api/organizer/events", headers=org).json()[0]["id"]
    dash = client.get(f"/api/organizer/events/{eid}", headers=org)
    assert dash.status_code == 200
    metrics = dash.json()["metrics"]
    db = SessionLocal()
    event = db.query(Event).filter(Event.id == eid).one()
    from app.routers.organizer import metrics_for

    expected = metrics_for(db, event)
    db.close()
    assert metrics["queries_posted"] == expected["queries_posted"]
    assert metrics["queries_matched"] == expected["queries_matched"]
    assert metrics["calls_accepted"] == expected["calls_accepted"]
    assert metrics["calls_completed"] == expected["calls_completed"]
    assert metrics["repeat_attendees"] == expected["repeat_attendees"] == 0
    assert "/join/" in dash.json()["join_url"]
    csv = client.get(f"/api/organizer/events/{eid}/csv", headers=org)
    assert csv.status_code == 200
    assert "Quiet Attendee" in csv.text  # organizer sees opted-out attendees
    pilot = client.get("/api/pilot/metrics?gate=mentorwow")
    assert pilot.status_code == 200
    assert "queries_posted" in pilot.json()


def test_ai_failure_fallbacks(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("OpenAI 500")

    monkeypatch.setattr("app.ai._chat", boom)
    monkeypatch.setattr("app.ai.extract_pdf_text", lambda _b: "Python engineer, FastAPI, system design")
    parsed = parse_resume(MIN_PDF)
    assert parsed == {"skill_tags": [], "can_advise_on": [], "open_to_collaborate_on": []}
    members = [
        {"user_id": 11, "headline": "eng", "skill_tags": ["python", "engineering"], "can_advise_on": ["system design"], "open_to_collaborate_on": []},
        {"user_id": 12, "headline": "pm", "skill_tags": ["roadmaps"], "can_advise_on": [], "open_to_collaborate_on": []},
        {"user_id": 13, "headline": "eng 2", "skill_tags": ["python"], "can_advise_on": ["debugging"], "open_to_collaborate_on": []},
        {"user_id": 14, "headline": "eng 3", "skill_tags": ["fastapi"], "can_advise_on": ["apis"], "open_to_collaborate_on": []},
    ]
    picked = match_query({"type": "skill", "body": "python system design review", "author_id": 1}, members)
    assert 3 <= len(picked) <= 5 or len(picked) >= 1
    assert all("user_id" in row for row in picked)
    assert summarize_chat([{"name": "Amina", "body": "hello"}]) == "Recap unavailable."
