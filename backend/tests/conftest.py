import os
from pathlib import Path

DB = Path(__file__).resolve().parent / "_graph_test.db"
if DB.exists():
    DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{DB}"
os.environ["OPENAI_API_KEY"] = ""
os.environ["PILOT_GATE"] = "mentorwow"
os.environ["EMAIL_PROVIDER_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def auth_header(client: TestClient, email: str, password: str = "mentorwow") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register(client: TestClient, email: str, name: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "mentorwow", "name": name},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def join(client: TestClient, headers: dict, **flags):
    payload = {
        "accepted_join": True,
        "show_attendance": True,
        "resume_visible_this_event": False,
        "show_contact_after_call": True,
        "name": flags.pop("name", "New Member"),
        "headline": flags.pop("headline", "Pilot attendee"),
        "skill_tags": flags.pop("skill_tags", ["python", "engineering"]),
        "can_advise_on": flags.pop("can_advise_on", ["debugging"]),
        "open_to_collaborate_on": flags.pop("open_to_collaborate_on", ["technical co-founder"]),
    }
    payload.update(flags)
    response = client.post("/api/join/cedat-join-demo", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()
