"""Principal resolution: opaque bearer token -> fixed (tenant, clearance)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from .clearance import floor_public


@dataclass(frozen=True)
class Principal:
    """An authenticated identity bound to exactly one tenant and clearance ceiling.

    ``capabilities`` is an optional, additive set of write/action grants (default: none →
    read-only). Phase 3 (SPEC-specledger-a2a-publish-phase3 §5.5) introduces the minimal
    ``ingest_governed`` capability so a read token can never write.
    """

    name: str
    tenant: str
    clearance: str  # always a valid clearance level
    capabilities: tuple[str, ...] = ()
    #: 읽기 범위. 비면 ``(tenant,)`` 와 같다 (SPEC-nexus-tenant-read-scope §3.1).
    #:
    #: ⛔ **쓰기는 이 목록을 절대 쓰지 않는다.** 쓰기 테넌트는 ``tenant`` 하나다. 목록이
    #: 생기면 호출부를 ``read_tenants[0]`` 로 고치는 것이 자연스러운데, 그것은 목록이
    #: ``["design_docs", "default"]`` 인 principal 을 **엉뚱한 테넌트에 적재**시킨다
    #: (SPEC §4 I-5, 크리틱 3R I-001).
    read_tenants: tuple[str, ...] = ()
    #: 이 principal 의 답변 백엔드. ``None`` 이면 프로세스 기본값(`NEXUS_LLM_PROVIDER`)을 따른다
    #: (SPEC-nexus-per-principal-answer-backend §4.1). 요청 본문은 이것을 고를 수 없다.
    llm_provider: str | None = None
    #: 구독 보유자 **본인**의 신원인가. 결정된 백엔드가 키리스 브리지인 principal 은 이것이
    #: 참이어야 기동한다(`providers.backend_choice.check_principal_backends`). ``ANONYMOUS`` 와
    #: Cloudflare Access 신원은 언제나 거짓이다.
    owner: bool = False

    @property
    def read_scope(self) -> tuple[str, ...]:
        """읽기에 허용된 테넌트들. 설정이 없으면 오늘과 같은 하나."""
        return self.read_tenants or (self.tenant,)

    def has(self, capability: str) -> bool:
        """True if this principal carries ``capability`` (default-deny: empty ⇒ read-only)."""
        return capability in self.capabilities


def gen_token() -> str:
    """A fresh high-entropy bearer token. The scheme's security rests on this entropy."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """sha256 hex of a token, as stored in ``auth.principals[].token_sha256``."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _llm_provider(entry: dict) -> str | None:
    """The entry's backend, normalised by the same function startup validation uses.

    Startup (`check_principal_backends`) already refused anything invalid, so this only
    normalises. Imported lazily: the providers package is heavier than the auth layer.
    """
    from nexus.providers.backend_choice import principal_provider

    return principal_provider(entry, str(entry.get("name", "unknown")))


def resolve_principal(token: str | None, principals: list[dict]) -> Principal | None:
    """Return the matching principal, or ``None`` if the token is missing/unknown.

    Compares ``sha256(token)`` against each configured ``token_sha256`` with a constant-time
    per-entry comparison. A principal's configured clearance is floored to a valid level so a
    misconfigured entry can never grant more than ``PUBLIC`` by accident.
    """
    if not token:
        return None
    digest = hash_token(token)
    for p in principals or []:
        stored = str(p.get("token_sha256", ""))
        if stored and hmac.compare_digest(digest, stored):
            return Principal(
                name=str(p.get("name", "unknown")),
                tenant=str(p.get("tenant", "default")),
                clearance=floor_public(p.get("clearance")),
                capabilities=tuple(str(c) for c in (p.get("capabilities") or [])),
                read_tenants=tuple(str(t) for t in (p.get("read_tenants") or [])),
                llm_provider=_llm_provider(p),
                owner=p.get("owner") is True,
            )
    return None
