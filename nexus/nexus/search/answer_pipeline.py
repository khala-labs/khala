"""The retrieval front half every answer surface shares (SPEC-nexus-shared-answer-pipeline).

Entity detection → route → ``hybrid_search`` → ``packet_for_answer``, written once.

⛔ **Why (2026-11-12 structure review).** `/search/answer`, `/search/answer/stream`, A2A and
the CLI each carried a copy of this sequence, and the copies drifted: the stream once built
its packet without `packet_for_answer`, and later dropped the synthetic-data marker. Each
fix landed on one copy. This module is the one copy.

**Dependencies are passed in, not imported.** Over a hundred tests patch these names on
`nexus.api` (`monkeypatch.setattr(api, "hybrid_search", ...)`). If this module imported them
itself, HTTP calls would escape those patches and reach a real database or model. The HTTP
handlers therefore build :class:`RetrievalDeps` from `nexus.api`'s globals at request time;
A2A and the CLI build it from the real modules. This module imports nothing from `nexus.api`.

⚠ So `packet_for_answer` is held by **one call site plus a test**
(`tests/test_answer_surfaces_share_the_seam.py`), not by the type system: a caller could
inject something else. A2A and the CLI always bind `nexus.search.reconcile.packet_for_answer`.

**No surface gains a step.** The channel step (`api._search_channels`, which may call the LLM)
stays with the HTTP caller, which passes its result in; A2A and the CLI pass nothing, as
before. The HTTP-only `hybrid_search` arguments arrive in ``search_opts`` and are absent for
A2A and the CLI, so they keep `hybrid_search`'s defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from nexus.rid import entity_rid

#: "the caller did not pass channels" — distinct from passing ``None`` explicitly.
_UNSET: Any = object()


@dataclass(frozen=True)
class RetrievalDeps:
    """What :func:`retrieve_for_answer` calls. Bound by the caller (see module docstring)."""

    hybrid_search: Callable[..., Awaitable[Any]]
    packet_for_answer: Callable[..., Awaitable[Any]]
    find_entities_in_text: Callable[..., Any]
    load_gazetteer: Callable[..., Any]
    build_entity_patterns: Callable[..., Any]
    determine_route: Callable[..., str]
    get_pool: Callable[[], Awaitable[Any]]
    graph_repository: Any
    embedding_service: Any
    config: dict


@dataclass
class Retrieval:
    """What one retrieval produced. ``packet`` is ``None`` when no packet was built."""

    search_result: Any
    packet: Any | None
    route: str
    entity_rids: list[str]
    channels: Any
    #: `hybrid_search`'s own `timing_ms`, passed through unchanged.
    timings: dict


async def retrieve_for_answer(
    query: str,
    *,
    scope: Any,
    clearance: str,
    route: str,
    top_k: int,
    deps: RetrievalDeps,
    entity_tenant: str,
    question: str | None = None,
    channels: Any = _UNSET,
    search_opts: dict | None = None,
    want_packet: bool = True,
    skip_packet_on_zero_hits: bool = False,
) -> Retrieval:
    """Run the shared retrieval sequence for one request.

    Args:
        query: the text to search with (after any rewrite the caller did).
        scope: the read scope — a tuple of tenants on read paths, or one tenant (CLI).
        clearance: the clearance the search filters by.
        route: the caller's route request (`req.route`, ``"auto"`` for A2A, the CLI option).
        top_k: passed by each caller (A2A keeps 10).
        entity_tenant: the tenant entity rids are minted under (the principal's own).
        question: what `packet_for_answer` treats as the question; defaults to ``query``.
        channels: the caller's channel result. Passed to `hybrid_search` only when given.
        search_opts: HTTP-only `hybrid_search` arguments; ``None`` keeps its defaults.
        want_packet: build the packet at all (`POST /search` passes False).
        skip_packet_on_zero_hits: also skip it when nothing was found (the CLI's condition).
    """
    patterns = deps.build_entity_patterns(deps.load_gazetteer())
    detected = deps.find_entities_in_text(query, patterns)
    entity_rids = [entity_rid(entity_tenant, e.entity_type, e.name) for e in detected]
    route_used = deps.determine_route(query, route, [e.name for e in detected])

    kwargs: dict[str, Any] = dict(
        query=query, tenant=scope, clearance=clearance, top_k=top_k,
        embedding_svc=deps.embedding_service, graph_repo=deps.graph_repository,
        route=route_used, entity_rids=entity_rids, config=deps.config,
    )
    if channels is not _UNSET:
        kwargs["channels"] = channels
    kwargs.update(search_opts or {})
    search_result = await deps.hybrid_search(**kwargs)

    packet = None
    if want_packet and not (skip_packet_on_zero_hits and not search_result.hits):
        # Evidence for an answer is built by this one call, on every surface.
        packet = await deps.packet_for_answer(
            search_result, scope, clearance,
            config=deps.config, search=deps.hybrid_search,
            embedding_svc=deps.embedding_service,
            question=question or query, pool=await deps.get_pool())

    return Retrieval(
        search_result=search_result, packet=packet, route=route_used,
        entity_rids=entity_rids, channels=None if channels is _UNSET else channels,
        timings=getattr(search_result, "timing_ms", {}) or {},
    )
