"""SPEC-nexus-per-principal-answer-backend — the A2A half.

Split from `test_answer_backend_per_principal.py` because these need the optional `a2a` SDK:
`conftest.py` skips collecting any test file that imports `nexus.a2a` when the SDK is absent,
and it would have skipped the whole main file with it.
"""

from __future__ import annotations

import pytest

from nexus.auth import AuthConfig
from nexus.auth.principal import hash_token

pytestmark = pytest.mark.usefixtures("isolate_auth_env")


def _entry(name: str, **extra) -> dict:
    return {"name": name, "token_sha256": hash_token("t" + name), "tenant": "default",
            "clearance": "PUBLIC", **extra}


@pytest.fixture
def default_bridge(monkeypatch):
    monkeypatch.setenv("NEXUS_LLM_PROVIDER", "claude-code")


# ── A2A uses the same check ──────────────────────────────────────────────────────────────

def test_a2a_and_auth_call_the_same_check():
    from nexus.a2a import server

    assert "check_principal_backends" in server.mount_a2a.__code__.co_names
    assert "check_principal_backends" in AuthConfig.validate_startup.__code__.co_names


def test_the_a2a_env_token_is_never_owner(default_bridge, monkeypatch):
    from fastapi import FastAPI

    from nexus.a2a.config import A2AConfig
    from nexus.a2a.server import mount_a2a

    monkeypatch.setenv("NEXUS_A2A_TOKEN", "a2a-token-for-this-test")
    cfg = A2AConfig.from_dict({"a2a": {"enabled": True}})
    assert cfg.principals and "owner" not in cfg.principals[-1]
    with pytest.raises(RuntimeError, match="'a2a-static'"):
        mount_a2a(FastAPI(), cfg, answer_fn=lambda q, t, c: None)


def test_the_a2a_answer_surface_passes_the_principals_backend():
    from nexus.a2a import server

    seen, names = set(), set()

    def walk(code) -> None:
        if id(code) in seen:
            return
        seen.add(id(code))
        names.update(code.co_names)
        for const in code.co_consts:
            if hasattr(const, "co_names"):
                walk(const)

    walk(server._default_answer_fn.__code__)
    assert "llm_for" in names
    assert "LLMService" not in names, "the A2A surface must not build a backend without the principal"
