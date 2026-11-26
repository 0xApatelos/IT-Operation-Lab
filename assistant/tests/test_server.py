"""Unit test server FastAPI (TestClient): health, query, batasan, UI relatif."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from assistant_lab.server import create_app


@pytest.fixture
def client(mini_engine):
    return TestClient(create_app(mini_engine))


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok" and data["mode"] == "search-only"
    assert data["kb"]["chunks"] > 0


def test_query_answered(client):
    r = client.post("/api/query", json={"question": "layanan demo-x berhenti bagaimana diagnosis"})
    assert r.status_code == 200
    a = r.json()
    assert a["status"] in ("answered", "insufficient_evidence")
    assert "citations" in a and "limitations" in a


def test_query_abstain(client):
    r = client.post("/api/query", json={"question": "zzqq blorptix unknownxyz"})
    assert r.status_code == 200
    assert r.json()["status"] == "insufficient_evidence"


def test_query_too_long_rejected(client):
    r = client.post("/api/query", json={"question": "x" * 600})
    assert r.status_code == 200
    assert r.json()["error"] == "invalid_query"


def test_query_missing_field(client):
    r = client.post("/api/query", json={"bukan": "question"})
    assert r.json()["error"] == "invalid_request"


def test_query_invalid_json(client):
    r = client.post("/api/query", content=b"{bukan json", headers={"Content-Type": "application/json"})
    assert r.json()["error"] == "invalid_json"


def test_ui_uses_relative_urls_only(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "fetch('/api/query'" in html
    assert "127.0.0.1" not in html and "localhost" not in html
