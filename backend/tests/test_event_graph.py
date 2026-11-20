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
        "/api/join/mentorwow-join",
        json={"accepted_join": False, "show_attendance": True},
        headers=headers,
    )
    assert denied.status_code == 400
    join(client, headers, show_attendance=False, skill_tags=["quiet"])
    people = client.get("/api/events/mentorwow-pilot/people", headers=auth_header(client, "copper.loom@mentorwow.app"))
    handles = [row["handle"] for row in people.json()]
    assert "nimbus-kiln" not in handles
    assert "copper-loom" in handles


def test_resume_opt_in_and_gated_url(client: TestClient):
    headers = register(client, "resume.user@mentorwow.app", "Resume User")
    join(client, headers, skill_tags=["fastapi"])
    upload = client.post("/api/me/resume", files={"file": ("cv.pdf", MIN_PDF, "application/pdf")}, headers=headers)
    assert upload.status_code == 200
    assert upload.json()["skill_tags"] == []
    client.put(
        "/api/me/profile",
        json={"skill_tags": ["fastapi", "privacy"], "headline": "API person"},
        headers=headers,
    )
    me = client.get("/api/me/profile", headers=headers).json()
    handle = me["handle"]
    copper = auth_header(client, "copper.loom@mentorwow.app")
    people = {row["handle"]: row for row in client.get("/api/events/mentorwow-pilot/people", headers=copper).json()}
    assert people[handle]["resume_url"] is None
    event = client.get("/api/events/mentorwow-pilot", headers=headers).json()["event"]
    forbidden = client.get(f"/api/events/{event['id']}/members/{me['id']}/resume", headers=copper)
    assert forbidden.status_code == 403
    client.post("/api/consent", json={"slug": "mentorwow-pilot", "resume_visible_this_event": True}, headers=headers)
    people2 = {row["handle"]: row for row in client.get("/api/events/mentorwow-pilot/people", headers=copper).json()}
    assert people2[handle]["resume_visible"] is True
    assert people2[handle]["resume_url"]
    allowed = client.get(people2[handle]["resume_url"], headers=copper)
    assert allowed.status_code == 200
    assert allowed.headers["content-type"].startswith("application/pdf")


def test_outgoing_query_rate_limit(client: TestClient):
    headers = register(client, "rate.limit@mentorwow.app", "Ratey")
    join(client, headers, skill_tags=["python"])
    slot = {"start": (utcnow() + timedelta(hours=1)).isoformat()}
    for i in range(2):
        ok = client.post(
            "/api/events/mentorwow-pilot/queries",
            json={"type": "skill", "body": f"Need a teardown pass {i} on matching.", "available_slots": [slot]},
            headers=headers,
        )
        assert ok.status_code == 200, ok.text
    blocked = client.post(
        "/api/events/mentorwow-pilot/queries",
        json={"type": "skill", "body": "Third query should be blocked this week.", "available_slots": [slot]},
        headers=headers,
    )
    assert blocked.status_code == 429
    assert "2 outgoing" in blocked.json()["detail"]


def test_skill_match_accept_creates_call(client: TestClient):
    jules = auth_header(client, "salt.harbor@mentorwow.app")
    queries = client.get("/api/events/mentorwow-pilot/queries", headers=jules).json()
    pending = next(q for q in queries if q["matched"] and q["my_response"] == "pending" and q["type"] == "skill")
    accept = client.post(
        f"/api/queries/{pending['id']}/respond",
        json={"response": "accepted", "slot": pending["available_slots"][0]},
        headers=jules,
    )
    assert accept.status_code == 200, accept.text
    call = accept.json()["call"]
    assert call["status"] == "scheduled"
    assert call["meeting_url"].startswith("/e/mentorwow-pilot/call/")
    mine = client.get("/api/events/mentorwow-pilot/calls", headers=jules).json()
    assert mine[0]["meeting_url"].startswith("/e/mentorwow-pilot/call/")
    assert mine[0]["other"]["email"]  # visible after scheduled
    kept = client.get("/api/connections", headers=jules).json()
    assert "copper-loom" in [row["handle"] for row in kept["connected"]]


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
    event = db.query(Event).filter(Event.slug == "mentorwow-pilot").one()
    author = db.query(User).filter(User.email == "deepee110001@gmail.com").one()
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
        "/api/events/mentorwow-pilot/queries",
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


def test_chat_yay_nay_poll(client: TestClient):
    amina = auth_header(client, "copper.loom@mentorwow.app")
    posted = client.post(
        "/api/events/mentorwow-pilot/chat",
        json={"body": "Worth the trip?", "kind": "poll"},
        headers=amina,
    )
    assert posted.status_code == 200, posted.text
    assert posted.json()["kind"] == "poll"
    assert posted.json()["poll"]["total"] == 0
    msg_id = posted.json()["id"]
    jules = auth_header(client, "salt.harbor@mentorwow.app")
    voted = client.post(f"/api/events/mentorwow-pilot/chat/{msg_id}/vote", json={"choice": "yay"}, headers=jules)
    assert voted.status_code == 200
    assert voted.json()["poll"]["yay"] == 1
    assert voted.json()["poll"]["my_vote"] == "yay"
    flipped = client.post(f"/api/events/mentorwow-pilot/chat/{msg_id}/vote", json={"choice": "nay"}, headers=jules)
    assert flipped.json()["poll"]["yay"] == 0
    assert flipped.json()["poll"]["nay"] == 1
    rejected = client.post(f"/api/events/mentorwow-pilot/chat/{msg_id}/vote", json={"choice": "maybe"}, headers=jules)
    assert rejected.status_code == 400


def test_my_polls_lists_own_attachments(client: TestClient):
    headers = register(client, "poll.owner@mentorwow.app", "Poll Owner")
    join(client, headers)
    posted = client.post(
        "/api/events/mentorwow-pilot/chat",
        json={"body": "Keep the booth?", "kind": "poll"},
        headers=headers,
    )
    assert posted.status_code == 200, posted.text
    mine = client.get("/api/me/polls", headers=headers)
    assert mine.status_code == 200
    bodies = [row["body"] for row in mine.json()]
    assert "Keep the booth?" in bodies
    assert mine.json()[0]["event"]["slug"] == "mentorwow-pilot"


def test_author_and_organizer_can_delete_chat(client: TestClient):
    headers = register(client, "chat.delete@mentorwow.app", "Deleter")
    join(client, headers)
    posted = client.post(
        "/api/events/mentorwow-pilot/chat",
        json={"body": "Posted by mistake."},
        headers=headers,
    )
    assert posted.status_code == 200, posted.text
    msg_id = posted.json()["id"]
    other = auth_header(client, "salt.harbor@mentorwow.app")
    denied = client.delete(f"/api/events/mentorwow-pilot/chat/{msg_id}", headers=other)
    assert denied.status_code == 403
    deleted = client.delete(f"/api/events/mentorwow-pilot/chat/{msg_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert deleted.json()["body"] == "This message was deleted"
    again = client.delete(f"/api/events/mentorwow-pilot/chat/{msg_id}", headers=headers)
    assert again.status_code == 400
    poll = client.post(
        "/api/events/mentorwow-pilot/chat",
        json={"body": "Delete this poll?", "kind": "poll"},
        headers=headers,
    )
    assert poll.status_code == 200, poll.text
    poll_id = poll.json()["id"]
    org = auth_header(client, "deepee110001@gmail.com")
    removed = client.delete(f"/api/events/mentorwow-pilot/chat/{poll_id}", headers=org)
    assert removed.status_code == 200
    assert removed.json()["deleted"] is True
    blocked_vote = client.post(
        f"/api/events/mentorwow-pilot/chat/{poll_id}/vote",
        json={"choice": "yay"},
        headers=other,
    )
    assert blocked_vote.status_code == 400
    mine = client.get("/api/me/polls", headers=headers)
    assert "Delete this poll?" not in [row["body"] for row in mine.json()]


def test_legacy_join_token_aliases_pilot(client: TestClient):
    response = client.get("/api/join/cedat-join-demo")
    assert response.status_code == 200
    assert response.json()["event"]["slug"] == "mentorwow-pilot"


def test_chat_pin_recap_and_close(client: TestClient):
    amina = auth_header(client, "copper.loom@mentorwow.app")
    posted = client.post("/api/events/mentorwow-pilot/chat", json={"body": "Takeaway: keep the booth to five minutes."}, headers=amina)
    assert posted.status_code == 200
    msg_id = posted.json()["id"]
    org = auth_header(client, "deepee110001@gmail.com")
    pin = client.post(f"/api/events/mentorwow-pilot/chat/{msg_id}/pin", json={}, headers=org)
    assert pin.status_code == 200
    assert pin.json()["is_pinned"] is True
    recap = client.post("/api/events/mentorwow-pilot/chat/recap", json={}, headers=amina)
    assert recap.status_code == 200
    eid = client.get("/api/organizer/events", headers=org).json()[0]["id"]
    closed = client.post(f"/api/organizer/events/{eid}/close-chat", json={}, headers=org)
    assert closed.status_code == 200
    denied = client.post("/api/events/mentorwow-pilot/chat", json={"body": "too late"}, headers=amina)
    assert denied.status_code == 403


def test_contact_hidden_until_scheduled(client: TestClient):
    amina = auth_header(client, "copper.loom@mentorwow.app")
    people = {row["handle"]: row for row in client.get("/api/events/mentorwow-pilot/people", headers=amina).json()}
    if "amber-ridge" in people:
        assert people["amber-ridge"]["email"] is None
    headers = register(client, "contact.test@mentorwow.app", "Contact Test")
    join(client, headers, skill_tags=["career"])
    other = {row["handle"]: row for row in client.get("/api/events/mentorwow-pilot/people", headers=headers).json()}
    assert other["copper-loom"]["email"] is None


def test_organizer_dashboard_funnel(client: TestClient):
    org = auth_header(client, "deepee110001@gmail.com")
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
    assert "nimbus-kiln" in csv.text  # organizer sees opted-out attendees
    pilot = client.get("/api/pilot/metrics?gate=mentorwow")
    assert pilot.status_code == 200
    body = pilot.json()
    assert "queries_posted" in body
    assert "funnel" in body
    assert "insights" in body
    assert "activity" in body
    assert "match_rate_pct" in body
    assert isinstance(body["funnel"], list)
    assert metrics["insights"]


def test_google_sign_in_default_and_metrics_allowlist(client, monkeypatch):
    config = client.get("/api/auth/config")
    assert config.status_code == 200
    assert config.json()["google_enabled"] is False
    missing = client.post("/api/auth/google", json={"credential": "nope"})
    assert missing.status_code == 501

    from app.routers import auth as auth_mod

    monkeypatch.setattr(
        auth_mod,
        "verify_google_credential",
        lambda _credential: {
            "sub": "google-sub-deepee",
            "email": "deepee110001@gmail.com",
            "email_verified": True,
            "name": "Deepak",
            "picture": "https://example.com/p.png",
        },
    )
    signed = client.post("/api/auth/google", json={"credential": "fake-google-jwt"})
    assert signed.status_code == 200, signed.text
    body = signed.json()
    assert body["user"]["email"] == "deepee110001@gmail.com"
    assert body["user"]["name"] == ""
    assert body["user"]["handle"] == "deepee"
    assert body["user"]["is_admin"] is True
    assert body["access_token"]
    again = client.post("/api/auth/google", json={"credential": "fake-google-jwt"})
    assert again.json()["is_new"] is False
    assert again.json()["user"]["handle"] == body["user"]["handle"]

    created = client.post("/api/auth/login", json={"email": "fresh.handle@mentorwow.app", "password": "mentorwow"})
    assert created.status_code == 200, created.text
    assert created.json()["is_new"] is True
    assert created.json()["user"]["name"] == ""
    assert created.json()["user"]["is_admin"] is False
    handle = created.json()["user"]["handle"]
    assert handle
    returning = client.post("/api/auth/login", json={"email": "fresh.handle@mentorwow.app", "password": "mentorwow"})
    assert returning.json()["is_new"] is False
    assert returning.json()["user"]["handle"] == handle

    ok = client.post("/api/metrics/track", json={"name": "page_view", "path": "/login", "session_id": "s-test"})
    assert ok.status_code == 200
    assert ok.json()["written"] == 1
    rejected = client.post("/api/metrics/track", json={"name": "rm_rf", "path": "/"})
    assert rejected.status_code == 200
    assert rejected.json()["written"] == 0


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


def test_native_connect_request_accept_and_persist(client: TestClient):
    a = register(client, "connect.a@mentorwow.app", "Connect A")
    b = register(client, "connect.b@mentorwow.app", "Connect B")
    join(client, a, skill_tags=["python"])
    join(client, b, skill_tags=["design"])
    me_b = client.get("/api/auth/me", headers=b).json()
    people = {row["handle"]: row for row in client.get("/api/events/mentorwow-pilot/people", headers=a).json()}
    assert people[me_b["handle"]]["connection"]["state"] == "none"
    asked = client.post(
        "/api/events/mentorwow-pilot/connect",
        json={"user_id": me_b["id"]},
        headers=a,
    )
    assert asked.status_code == 200, asked.text
    assert asked.json()["state"] == "pending_out"
    dup = client.post("/api/events/mentorwow-pilot/connect", json={"user_id": me_b["id"]}, headers=a)
    assert dup.status_code == 400
    inbox = client.get("/api/connections", headers=b).json()
    assert len(inbox["incoming"]) == 1
    accepted = client.post(
        f"/api/connections/{inbox['incoming'][0]['id']}/respond",
        json={"response": "accepted"},
        headers=b,
    )
    assert accepted.status_code == 200
    assert accepted.json()["state"] == "connected"
    kept = client.get("/api/connections", headers=a).json()
    assert kept["connected"][0]["handle"] == me_b["handle"]
    people2 = {row["handle"]: row for row in client.get("/api/events/mentorwow-pilot/people", headers=a).json()}
    assert people2[me_b["handle"]]["connection"]["state"] == "connected"
    gone = client.post(f"/api/connections/{kept['connected'][0]['id']}/disconnect", headers=a)
    assert gone.status_code == 200
    assert gone.json()["state"] == "none"
    again = client.post("/api/events/mentorwow-pilot/connect", json={"user_id": me_b["id"]}, headers=a)
    assert again.status_code == 200
    assert again.json()["state"] == "pending_out"


def test_native_connect_incoming_tap_accepts(client: TestClient):
    a = register(client, "connect.c@mentorwow.app", "Connect C")
    b = register(client, "connect.d@mentorwow.app", "Connect D")
    join(client, a)
    join(client, b)
    me_a = client.get("/api/auth/me", headers=a).json()
    client.post("/api/events/mentorwow-pilot/connect", json={"user_id": me_a["id"]}, headers=b)
    people = {row["handle"]: row for row in client.get("/api/events/mentorwow-pilot/people", headers=a).json()}
    me_b = client.get("/api/auth/me", headers=b).json()
    assert people[me_b["handle"]]["connection"]["state"] == "pending_in"
    tapped = client.post("/api/events/mentorwow-pilot/connect", json={"user_id": me_b["id"]}, headers=a)
    assert tapped.status_code == 200
    assert tapped.json()["state"] == "connected"


def test_cannot_connect_to_self(client: TestClient):
    headers = register(client, "connect.self@mentorwow.app", "Connect Self")
    join(client, headers)
    me = client.get("/api/auth/me", headers=headers).json()
    denied = client.post("/api/events/mentorwow-pilot/connect", json={"user_id": me["id"]}, headers=headers)
    assert denied.status_code == 400
