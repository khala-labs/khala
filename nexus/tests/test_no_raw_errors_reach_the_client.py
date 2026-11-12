"""An internal failure reaches the client as a reference number, never as the exception text.

⛔ **Why (2026-11-12 structure review).** Nine places in `api.py` answered
`HTTPException(500, detail=str(e))` — including the stream's `event: error` — so an asyncpg or
LLM error could hand a caller a DSN, a table name or an internal path. Before any public path
opens, the text stays in the server log (with the same `ref`) and the client gets the `ref`.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nexus import api  # noqa: E402

_TOKEN = "y" * 40
_AUTH = {"Authorization": "Bearer " + _TOKEN}
SECRET = "postgresql://nexus:hunter2@db.internal:5432/nexus relation \"chunks\""


@pytest.fixture
def client(monkeypatch):
    from nexus import db

    monkeypatch.setenv("NEXUS_DEV_TOKEN", _TOKEN)

    async def _noop_async(*a, **k):
        return None

    monkeypatch.setattr(api, "_load_config", lambda *a, **k: {})
    monkeypatch.setattr(api, "embedding_service_from_config", lambda *a, **k: None)
    monkeypatch.setattr(api.db, "get_pool", _noop_async)
    monkeypatch.setattr(api, "PostgresGraphRepository", lambda *a, **k: None)
    monkeypatch.setattr(api, "_load_gazetteer", lambda *a, **k: {})
    monkeypatch.setattr(api, "_build_entity_patterns", lambda *a, **k: {})
    monkeypatch.setattr(api, "find_entities_in_text", lambda *a, **k: [])
    monkeypatch.setattr(api, "record_search", _noop_async)
    saved = db._pool
    try:
        yield TestClient(api.app)
    finally:
        db._pool = saved


def _fail_with(monkeypatch, message: str) -> None:
    async def _boom(*a, **k):
        raise RuntimeError(message)

    monkeypatch.setattr(api, "hybrid_search", _boom)


@pytest.mark.parametrize("path", ["/search", "/search/answer"])
def test_a_500_carries_a_reference_not_the_exception_text(client, monkeypatch, path):
    _fail_with(monkeypatch, SECRET)

    r = client.post(path, json={"query": "q"}, headers=_AUTH)

    assert r.status_code == 500
    assert "hunter2" not in r.text and "db.internal" not in r.text
    assert "ref " in r.json()["detail"]


def test_a_lost_database_is_still_a_503_without_the_text(client, monkeypatch):
    _fail_with(monkeypatch, "could not connect to server: " + SECRET)

    r = client.post("/search", json={"query": "q"}, headers=_AUTH)

    assert r.status_code == 503
    assert "hunter2" not in r.text
    assert "ref " in r.json()["detail"]


def test_the_stream_error_event_carries_a_reference_not_the_text(client, monkeypatch):
    _fail_with(monkeypatch, SECRET)

    r = client.post("/search/answer/stream", json={"query": "q"}, headers=_AUTH)

    events = [b for b in r.text.split("\n\n") if b.startswith("event: error")]
    assert len(events) == 1, r.text
    payload = json.loads(events[0].split("data: ", 1)[1])
    assert "hunter2" not in payload["error"] and "ref " in payload["error"]


def test_the_server_log_keeps_what_the_client_does_not_see(monkeypatch):
    from structlog.testing import capture_logs

    with capture_logs() as logs:
        err = api._server_error(RuntimeError(SECRET), "here")
    ref = err.detail.split("ref ", 1)[1].rstrip(")")
    assert any(e.get("event") == "api.internal_error" and e.get("error_ref") == ref
               and e.get("where") == "here" for e in logs)


def test_no_endpoint_answers_a_500_with_the_exception_text():
    """Structural guard: a new `HTTPException(status_code=500, detail=str(...))` turns this red."""
    tree = ast.parse((ROOT / "nexus" / "api.py").read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "HTTPException":
            kw = {k.arg: k.value for k in node.keywords}
            code = kw.get("status_code")
            detail = kw.get("detail")
            if (isinstance(code, ast.Constant) and code.value >= 500 and isinstance(detail, ast.Call)
                    and getattr(detail.func, "id", None) == "str"):
                offenders.append(node.lineno)
    assert offenders == []
