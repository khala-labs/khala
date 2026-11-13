"""Which answer backend a caller gets — one place for the rule (SPEC-nexus-per-principal-answer-backend).

Three things live here, so validation and `LLMService` cannot disagree about them:

- `normalize_provider` — strip, lowercase; an empty string is an error, not "unset".
- `process_default` — what `NEXUS_LLM_PROVIDER` resolves to, alias `claude` included.
- `check_principal_backends` — **any principal whose resolved backend is `claude-code` must carry
  `owner: true`**, or startup is refused. `AuthConfig.validate_startup()` and the A2A mount both
  call it, so the two principal lists cannot drift apart.

⛔ Why the owner rule is enforced and not a comment: the keyless bridge runs `claude -p` under the
subscription holder's own login. Anthropic's Claude Code legal page (read 2026-11-12) does not
permit routing requests "through Free, Pro, Max, or Ultra plan credentials on behalf of their
users". A YAML comment would let one edit point a public token at the bridge.
"""

from __future__ import annotations

import os

#: The answer backends a principal may name. The env alias `claude` is accepted only in
#: `NEXUS_LLM_PROVIDER` (backward compatibility) — in principal config it would resolve to a
#: different backend depending on whether a bridge URL is set, a silent switch.
ANSWER_BACKENDS = ("anthropic", "claude-code")
BRIDGE = "claude-code"


def normalize_provider(value: object) -> str | None:
    """`None` stays `None` (unset). A string is stripped and lowercased; empty is an error."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"llm_provider must be a string, got {type(value).__name__}")
    v = value.strip().lower()
    if not v:
        raise ValueError("llm_provider is an empty string — omit it (or use null) to mean unset")
    return v


def resolve_env_provider(raw: str | None) -> str:
    """Resolve the process-wide `NEXUS_LLM_PROVIDER` value, alias `claude` included."""
    provider = (normalize_provider(raw) if raw is not None and raw.strip() else None) or "anthropic"
    if provider == "claude":
        provider = BRIDGE if os.getenv("NEXUS_LLM_BRIDGE_URL") else "anthropic"
    return provider


def process_default() -> str:
    return resolve_env_provider(os.getenv("NEXUS_LLM_PROVIDER"))


def principal_provider(entry: dict, who: str) -> str | None:
    """The `llm_provider` of a principal config entry, normalised; refuses the alias and unknowns."""
    try:
        value = normalize_provider(entry.get("llm_provider"))
    except ValueError as e:
        raise RuntimeError(f"principal {who!r}: {e}") from None
    if value is not None and value not in ANSWER_BACKENDS:
        raise RuntimeError(
            f"principal {who!r}: llm_provider {value!r} is not one of {', '.join(ANSWER_BACKENDS)}"
            + (" (the alias 'claude' is accepted only in NEXUS_LLM_PROVIDER)" if value == "claude"
               else ""))
    return value


def check_principal_backends(principals: list[dict], *, permissive: bool = False,
                             access_enabled: bool = False, surface: str = "auth") -> None:
    """Refuse startup unless every principal that resolves to the bridge is marked owner."""
    default = process_default()
    if default == BRIDGE:
        if permissive:
            raise RuntimeError(
                f"{surface}: NEXUS_LLM_PROVIDER resolves to {BRIDGE!r} while permissive mode is on "
                "— anonymous callers would be answered by the keyless bridge; set "
                "NEXUS_LLM_PROVIDER=anthropic and give owner tokens llm_provider: claude-code")
        if access_enabled:
            raise RuntimeError(
                f"{surface}: NEXUS_LLM_PROVIDER resolves to {BRIDGE!r} while Cloudflare Access is "
                "enabled — Access identities are never owner; set NEXUS_LLM_PROVIDER=anthropic")
    for p in principals or []:
        who = str(p.get("name", "?"))
        resolved = principal_provider(p, who) or default
        if resolved == BRIDGE and p.get("owner") is not True:
            raise RuntimeError(
                f"{surface}: principal {who!r} resolves to the {BRIDGE!r} backend but is not "
                "marked owner: true — only the subscription holder's own identities may use the "
                "keyless bridge (SPEC-nexus-per-principal-answer-backend). On a dev box, set "
                "NEXUS_LLM_PROVIDER=anthropic and NEXUS_DEV_LLM_PROVIDER=claude-code so only the "
                "local-dev identity uses the bridge")
