"""A2A reads with the **read** clamp — a token reads its whole `read_tenants`, and no more.

⛔ **Why (SPEC-nexus-shared-answer-pipeline §4.1).** The A2A answer skill resolved its scope with
`effective_scope`, the write clamp: it ignores the requested tenant and returns the principal's
own one. So a token whose `read_tenants` listed other tenants read only its own over A2A, while
the same token read all of them over HTTP. Nothing failed; the A2A answer just came from a
smaller corpus. These tests pin both directions: the whole read scope is reached, and a tenant
outside it is still refused (it falls back to the principal's own, with no error, as on HTTP).

Kept apart from `test_read_paths_use_the_read_clamp.py` because they need the optional `a2a`
SDK (`conftest.py` skips files that import `nexus.a2a` when it is absent).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nexus.a2a import server
from nexus.a2a.config import A2AConfig
from nexus.auth.principal import hash_token
from nexus.llm.answer import AnswerResult

_TOKEN = "a2a-read-scope-token"
_PRINCIPAL = {
    "name": "reader-agent", "token_sha256": hash_token(_TOKEN),
    "tenant": "default", "clearance": "INTERNAL",
    "read_tenants": ["default", "design_docs"],
}


@pytest.fixture
def seen(monkeypatch):
    captured: dict = {}

    async def _answer(query, tenant, clearance, principal=None):
        captured["scope"] = tenant
        return AnswerResult(answer="ok", route_used="vector")

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(server, "_default_answer_fn", _answer)
    monkeypatch.setattr(server, "record_audit", _noop)
    app = FastAPI()
    server.mount_a2a(app, A2AConfig(enabled=True, base_url="https://nexus.example.com",
                                    principals=[_PRINCIPAL]), answer_fn=None)
    captured["client"] = TestClient(app)
    return captured


def _send(seen, metadata=None):
    message = {"role": "user", "messageId": "m1", "kind": "message",
               "parts": [{"kind": "text", "text": "결제 흐름"}]}
    if metadata:
        message["metadata"] = metadata
    r = seen["client"].post("/a2a", headers={"Authorization": f"Bearer {_TOKEN}"},
                            json={"jsonrpc": "2.0", "id": "r1", "method": "message/send",
                                  "params": {"message": message}})
    assert r.status_code == 200, r.text
    assert "error" not in r.json(), r.json()
    return tuple(seen["scope"])


def test_a_token_with_read_tenants_reads_its_whole_scope(seen):
    assert _send(seen) == ("default", "design_docs")


def test_naming_a_tenant_in_scope_narrows_to_it(seen):
    assert _send(seen, {"tenant": "design_docs"}) == ("design_docs",)


def test_a_tenant_outside_read_tenants_is_refused(seen):
    """No error (that would leak whether the tenant exists) — the scope falls back to the token's own."""
    scope = _send(seen, {"tenant": "somebody_elses"})
    assert "somebody_elses" not in scope
    assert scope == ("default",)
