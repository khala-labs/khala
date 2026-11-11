"""SPEC-nexus-per-principal-answer-backend — the answer backend is chosen per principal.

⛔ **The rule these tests hold.** One Nexus process may answer different callers through
different backends, but **a principal whose resolved backend is the keyless bridge
(`claude-code`) must be marked `owner: true`, or the process refuses to start.** The bridge runs
under the subscription holder's own login; answering anyone else through it is what the terms
forbid. A YAML comment would let one edit point a public token at the bridge, so the rule is a
startup check — and these tests pin both halves: what must be refused, and what must still boot.
"""

from __future__ import annotations

import httpx
import pytest

from nexus.auth import AuthConfig
from nexus.auth.principal import Principal, hash_token, resolve_principal
from nexus.providers import backend_choice as bc
from nexus.providers import llm as P
from nexus.providers.llm import LLMService, llm_for

pytestmark = pytest.mark.usefixtures("isolate_auth_env")


def _entry(name: str, token: str = "t", **extra) -> dict:
    return {"name": name, "token_sha256": hash_token(token + name), "tenant": "default",
            "clearance": "PUBLIC", **extra}


@pytest.fixture
def default_anthropic(monkeypatch):
    monkeypatch.setenv("NEXUS_LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("NEXUS_LLM_BRIDGE_URL", raising=False)


@pytest.fixture
def default_bridge(monkeypatch):
    monkeypatch.setenv("NEXUS_LLM_PROVIDER", "claude-code")


# ── principal config carries the two fields ──────────────────────────────────────────────

def test_a_principal_carries_its_backend_and_owner_flag():
    p = resolve_principal("t" + "me", [_entry("me", llm_provider=" Claude-Code ", owner=True)])
    assert p.llm_provider == "claude-code"
    assert p.owner is True


def test_absent_fields_mean_process_default_and_not_owner():
    p = resolve_principal("t" + "pub", [_entry("pub")])
    assert p.llm_provider is None
    assert p.owner is False


def test_owner_must_be_literally_true():
    """A truthy string is not a claim of ownership — `owner: "yes"` stays not-owner."""
    p = resolve_principal("t" + "x", [_entry("x", owner="yes")])
    assert p.owner is False


# ── one normalisation function ───────────────────────────────────────────────────────────

def test_normalisation_strips_and_lowercases():
    assert bc.normalize_provider("  ANTHROPIC ") == "anthropic"
    assert bc.normalize_provider(None) is None


def test_an_empty_string_is_an_error_not_unset():
    with pytest.raises(ValueError, match="empty"):
        bc.normalize_provider("   ")


def test_the_alias_is_refused_in_principal_config():
    with pytest.raises(RuntimeError, match="alias 'claude'"):
        bc.principal_provider({"llm_provider": "claude"}, "p")


def test_an_unknown_backend_is_refused_in_principal_config():
    with pytest.raises(RuntimeError, match="'p'"):
        bc.principal_provider({"llm_provider": "gemini"}, "p")


# ── LLMService takes the choice as an argument ───────────────────────────────────────────

@pytest.mark.parametrize("env", ["anthropic", "claude-code"])
def test_an_explicit_provider_wins_over_the_env(monkeypatch, env):
    monkeypatch.setenv("NEXUS_LLM_PROVIDER", env)
    assert isinstance(LLMService(provider="anthropic")._backend, P._AnthropicBackend)
    assert isinstance(LLMService(provider="claude-code")._backend, P._ClaudeCodeBackend)


def test_no_provider_follows_the_env_as_before(monkeypatch):
    monkeypatch.setenv("NEXUS_LLM_PROVIDER", "claude-code")
    svc = LLMService()
    assert svc.provider == "claude-code"
    assert isinstance(svc._backend, P._ClaudeCodeBackend)


@pytest.mark.parametrize("bad", ["claude", "gemini", ""])
def test_an_explicit_provider_outside_the_two_backends_is_refused(bad):
    with pytest.raises(ValueError):
        LLMService(provider=bad)


def test_the_env_alias_keeps_its_meaning(monkeypatch):
    monkeypatch.setenv("NEXUS_LLM_PROVIDER", "claude")
    monkeypatch.delenv("NEXUS_LLM_BRIDGE_URL", raising=False)
    assert LLMService().provider == "anthropic"
    monkeypatch.setenv("NEXUS_LLM_BRIDGE_URL", "http://bridge.invalid:8900")
    assert LLMService().provider == "claude-code"


# ── the owner rule ───────────────────────────────────────────────────────────────────────

def test_a_bridge_principal_without_owner_is_refused(default_anthropic):
    with pytest.raises(RuntimeError, match="'friend'"):
        bc.check_principal_backends([_entry("friend", llm_provider="claude-code")])


def test_a_bridge_principal_marked_owner_boots(default_anthropic):
    bc.check_principal_backends([_entry("me", llm_provider="claude-code", owner=True),
                                 _entry("public")])


def test_with_a_bridge_default_a_team_token_without_owner_is_refused(default_bridge):
    """The `slack-bot` case: a team-facing token is not an owner, so this deployment must not boot."""
    with pytest.raises(RuntimeError, match="'slack-bot'"):
        bc.check_principal_backends([_entry("me", owner=True), _entry("slack-bot")])


def test_with_a_bridge_default_an_explicit_anthropic_token_still_boots(default_bridge):
    bc.check_principal_backends([_entry("me", owner=True),
                                 _entry("public", llm_provider="anthropic")])


def test_with_a_bridge_default_permissive_mode_is_refused(default_bridge):
    with pytest.raises(RuntimeError, match="permissive"):
        bc.check_principal_backends([], permissive=True)


def test_with_a_bridge_default_access_is_refused(default_bridge):
    with pytest.raises(RuntimeError, match="Access"):
        bc.check_principal_backends([], access_enabled=True)


def test_auth_startup_runs_the_rule(default_bridge):
    cfg = AuthConfig.from_dict({"auth": {"principals": [_entry("slack-bot")]}})
    with pytest.raises(RuntimeError, match="'slack-bot'"):
        cfg.validate_startup()


def test_the_local_dev_operator_token_is_an_owner(default_bridge, monkeypatch):
    """A dev box with the bridge as default and only the env-injected operator token must boot."""
    monkeypatch.setenv("NEXUS_DEV_TOKEN", "a-strong-enough-dev-token-for-this-test-only")
    cfg = AuthConfig.from_dict({})
    assert [p["name"] for p in cfg.principals] == ["local-dev"]
    cfg.validate_startup()


def test_the_anonymous_principal_is_never_owner():
    from nexus.auth.deps import ANONYMOUS

    assert ANONYMOUS.owner is False
    assert ANONYMOUS.llm_provider is None


# ── every answer surface passes the principal's choice ───────────────────────────────────

def _names(func) -> set[str]:
    """Names reachable from the function's code object, nested functions included."""
    seen, out = set(), set()

    def walk(code) -> None:
        if id(code) in seen:
            return
        seen.add(id(code))
        out.update(code.co_names)
        for const in code.co_consts:
            if hasattr(const, "co_names"):
                walk(const)

    walk(func.__code__)
    return out


def _surfaces():
    """HTTP surfaces only — the A2A surface needs the optional SDK and is counted in
    `test_answer_backend_per_principal_a2a.py`, so this file runs in every CI job."""
    from nexus import api

    return {
        "HTTP /search (rewrite)": api.search,
        "HTTP /search/answer": api.search_answer,
        "HTTP /search/answer/stream": api.search_answer_stream,
    }


@pytest.mark.parametrize("label", list(_surfaces()))
def test_every_answer_surface_passes_the_principals_backend(label):
    """⛔ A surface that forgets sends its public callers to the process default — maybe the bridge."""
    names = _names(_surfaces()[label])
    assert "llm_provider" in names or "llm_for" in names, label
    assert "log_answer_backend" in names or "llm_for" in names, label


def test_the_cli_is_left_on_the_process_default():
    from nexus import cli

    names = _names(cli.query)
    assert "llm_for" not in names and "log_answer_backend" not in names


# ── coexistence, logging, no fallback ────────────────────────────────────────────────────

async def test_one_process_serves_an_owner_on_the_bridge_and_a_public_token_on_the_key(
        default_anthropic, monkeypatch):
    calls: list[str] = []

    def bridge(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"text": "from the bridge", "usage": None})

    monkeypatch.setattr(P, "_bridge_transport", lambda: httpx.MockTransport(bridge))
    monkeypatch.setenv("NEXUS_LLM_BRIDGE_URL", "http://bridge.invalid:8900")
    owner = Principal(name="me", tenant="default", clearance="PUBLIC",
                      llm_provider="claude-code", owner=True)
    public = Principal(name="public", tenant="default", clearance="PUBLIC")

    a = llm_for(owner)
    b = llm_for(public)
    c = llm_for(owner)

    assert isinstance(a._backend, P._ClaudeCodeBackend)
    assert isinstance(b._backend, P._AnthropicBackend)
    assert a._backend is not c._backend, "no shared module-level backend"
    out = await a.generate_full("system", "question")
    assert out.text == "from the bridge" and calls


def test_each_answer_request_logs_principal_and_backend(default_anthropic):
    from structlog.testing import capture_logs

    with capture_logs() as logs:
        llm_for(Principal(name="public", tenant="default", clearance="PUBLIC"))
    events = [e for e in logs if e.get("event") == P.BACKEND_EVENT]
    assert events == [{"event": P.BACKEND_EVENT, "principal": "public", "backend": "anthropic",
                       "log_level": "info"}]


def test_a_bridge_principal_never_falls_back_to_the_key(default_anthropic, monkeypatch):
    """With no bridge URL the backend is still the bridge (its dev default URL); it fails at call
    time on the `llm_failed` path — it does not quietly become the Anthropic backend."""
    monkeypatch.delenv("NEXUS_LLM_BRIDGE_URL", raising=False)
    svc = llm_for(Principal(name="me", tenant="default", clearance="PUBLIC",
                            llm_provider="claude-code", owner=True))
    assert isinstance(svc._backend, P._ClaudeCodeBackend)
