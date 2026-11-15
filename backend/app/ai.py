"""Server-side OpenAI helpers. Never imported by the frontend."""

from __future__ import annotations

import json
import re

import httpx

from .config import OPENAI_API_KEY, OPENAI_MODEL
from .jsonutil import loads


def _chat(system: str, user: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY missing")
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": OPENAI_MODEL,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=45,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _json_from(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"[\[{].*[\]}]", text, re.S)
        if match:
            return json.loads(match.group(0))
        raise


def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
        import io

        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join((page.extract_text() or "") for page in reader.pages)[:12000]
    except Exception:
        return ""


def parse_resume(file_bytes: bytes) -> dict:
    empty = {"skill_tags": [], "can_advise_on": [], "open_to_collaborate_on": []}
    try:
        text = extract_pdf_text(file_bytes)
        if not text.strip():
            return empty
        raw = _chat(
            "Extract professional tags from a resume. Return JSON only. "
            "Max 10 skill_tags, 5 can_advise_on, 5 open_to_collaborate_on. "
            "Short phrases. No extra PII fields.",
            text[:8000],
        )
        data = _json_from(raw)
        return {
            "skill_tags": list(data.get("skill_tags") or [])[:10],
            "can_advise_on": list(data.get("can_advise_on") or [])[:5],
            "open_to_collaborate_on": list(data.get("open_to_collaborate_on") or [])[:5],
        }
    except Exception:
        return empty


def match_query(query: dict, members: list[dict]) -> list[dict]:
    """Return [{user_id, reason}] length 3–5. Heuristic fallback if OpenAI fails."""
    try:
        raw = _chat(
            "You match event attendees to a query. Return JSON array "
            "[{user_id, reason}]. Pick 3 to 5 people. Exclude the author. "
            "skill queries: overlap skill_tags/can_advise_on. "
            "collaboration queries: overlap open_to_collaborate_on; "
            "if the query mentions technical/engineer match engineering tags; "
            "design → designers.",
            json.dumps({"query": query, "members": members})[:12000],
        )
        picked = _json_from(raw)
        out = []
        for row in picked:
            uid = int(row.get("user_id"))
            out.append({"user_id": uid, "reason": str(row.get("reason") or "tag overlap")[:240]})
        if out:
            return out[:5]
    except Exception:
        pass
    return heuristic_match(query, members)


def heuristic_match(query: dict, members: list[dict]) -> list[dict]:
    body = (query.get("body") or "").lower()
    qtype = query.get("type")
    scored = []
    for member in members:
        blob = " ".join(
            member.get("skill_tags", [])
            + member.get("can_advise_on", [])
            + member.get("open_to_collaborate_on", [])
            + [member.get("headline") or ""]
        ).lower()
        score = 0
        for word in re.findall(r"[a-zA-Z]{3,}", body):
            if word in blob:
                score += 2
        if qtype == "skill":
            score += sum(2 for tag in member.get("can_advise_on", []) if tag.lower() in body)
            score += sum(1 for tag in member.get("skill_tags", []) if tag.lower() in body)
        else:
            score += sum(3 for tag in member.get("open_to_collaborate_on", []) if tag.lower() in body)
            if any(w in body for w in ("technical", "engineer", "dev", "cto")):
                if any("engineer" in t.lower() or "dev" in t.lower() for t in member.get("skill_tags", [])):
                    score += 4
            if "design" in body:
                if any("design" in t.lower() for t in member.get("skill_tags", []) + member.get("open_to_collaborate_on", [])):
                    score += 4
        if member.get("recent_decline"):
            score -= 2
        if score > 0:
            scored.append((score, member["user_id"], "tag overlap with the query"))
    scored.sort(reverse=True)
    return [{"user_id": uid, "reason": reason} for _, uid, reason in scored[:5]]


def summarize_chat(messages: list[dict]) -> str:
    try:
        raw = _chat(
            "Summarize this public event chat in 3–5 bullets. "
            "Tag people by name if mentioned. No speculation.",
            json.dumps(messages)[:10000],
        )
        return raw.strip() or "Recap unavailable."
    except Exception:
        return "Recap unavailable."


def moderate_message(body: str) -> dict:
    try:
        raw = _chat(
            "Flag only clear spam or abuse. Opinions are fine. "
            'Return JSON {"flagged": bool, "reason": string|null}.',
            body,
        )
        data = _json_from(raw)
        return {"flagged": bool(data.get("flagged")), "reason": data.get("reason")}
    except Exception:
        return {"flagged": False}
