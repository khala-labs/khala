"""`search/answer_pipeline.py::retrieve_for_answer` — the one retrieval front half (SPEC-nexus-shared-answer-pipeline).

⛔ **Why these.** The SPEC's promise is that moving four copies into one function changed no
surface's retrieval: each passes the `hybrid_search` arguments it passed before, and the CLI
builds a packet only when it did before. A refactor that quietly widened A2A's or the CLI's
search (or dropped one of the HTTP-only arguments) would look green everywhere else, so the
argument sets are pinned here, per surface.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from types import SimpleNamespace

import pytest

from nexus.search.answer_pipeline import RetrievalDeps, retrieve_for_answer

#: What A2A and the CLI pass today — and what the pipeline passes when the caller adds nothing.
BASE_ARGS = {"query", "tenant", "clearance", "top_k", "embedding_svc", "graph_repo",
             "route", "entity_rids", "config"}
#: What the two HTTP answer paths add (SPEC §3): 14 in all.
ANSWER_ARGS = BASE_ARGS | {"window", "channels", "exclude_doc_types",
                           "identifier_channel_asked", "fusion_doc_agreement"}
#: What `POST /search` adds: 11 in all.
SEARCH_ARGS = BASE_ARGS | {"window", "channels"}


def _deps(hits=("h",), calls=None):
    calls = calls if calls is not None else {}

    async def _search(**k):
        calls["search"] = set(k)
        return SimpleNamespace(hits=list(hits), timing_ms={"total_ms": 1})

    async def _packet(*a, **k):
        calls["packet"] = calls.get("packet", 0) + 1
        return "PACKET"

    async def _pool():
        return None

    return RetrievalDeps(
        hybrid_search=_search, packet_for_answer=_packet,
        find_entities_in_text=lambda q, p: [SimpleNamespace(entity_type="Service", name="pay")],
        load_gazetteer=lambda: [], build_entity_patterns=lambda g: [],
        determine_route=lambda q, r, names: f"routed:{r}", get_pool=_pool,
        graph_repository=None, embedding_service=None, config={},
    ), calls


async def test_a_caller_that_adds_nothing_passes_the_nine_base_arguments():
    deps, calls = _deps()
    out = await retrieve_for_answer("q", scope=("t",), clearance="INTERNAL", route="auto",
                                    top_k=10, deps=deps, entity_tenant="t")
    assert calls["search"] == BASE_ARGS
    assert out.packet == "PACKET" and calls["packet"] == 1
    assert out.route == "routed:auto"
    assert out.timings == {"total_ms": 1}
    assert len(out.entity_rids) == 1


async def test_http_options_are_added_not_substituted():
    deps, calls = _deps()
    await retrieve_for_answer(
        "q", scope=("t",), clearance="INTERNAL", route="auto", top_k=5, deps=deps,
        entity_tenant="t", channels=None,
        search_opts=dict(window=None, exclude_doc_types=[], identifier_channel_asked=False,
                         fusion_doc_agreement=False))
    assert calls["search"] == ANSWER_ARGS


async def test_no_packet_when_the_caller_does_not_want_one():
    deps, calls = _deps()
    out = await retrieve_for_answer("q", scope=("t",), clearance="INTERNAL", route="auto",
                                    top_k=5, deps=deps, entity_tenant="t", want_packet=False)
    assert out.packet is None and "packet" not in calls


async def test_the_cli_condition_skips_the_packet_on_zero_hits():
    """`query --answer` with no hits builds no packet and so writes no answer span — today's behaviour.

    Whether it should write one is an open question (SPEC §8); this pins what it does now.
    """
    deps, calls = _deps(hits=())
    out = await retrieve_for_answer("q", scope="t", clearance="INTERNAL", route="auto",
                                    top_k=5, deps=deps, entity_tenant="t",
                                    want_packet=True, skip_packet_on_zero_hits=True)
    assert out.packet is None and "packet" not in calls


async def test_the_answer_paths_build_a_packet_even_with_zero_hits():
    """The HTTP answer paths and A2A always built one (the abstain path reads it)."""
    deps, calls = _deps(hits=())
    out = await retrieve_for_answer("q", scope=("t",), clearance="INTERNAL", route="auto",
                                    top_k=5, deps=deps, entity_tenant="t")
    assert out.packet == "PACKET"


# ── per-surface argument sets, read from the callers ──────────────────────────────────

def _call_keywords(func) -> set[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "id", None) == "retrieve_for_answer"]
    assert len(calls) == 1
    return {k.arg for k in calls[0].keywords}


def test_the_cli_passes_no_channels_and_no_http_options():
    from nexus import cli

    kw = _call_keywords(cli.query)
    assert "channels" not in kw and "search_opts" not in kw
    assert {"want_packet", "skip_packet_on_zero_hits"} <= kw


def test_the_cli_generates_only_when_a_packet_was_built():
    from nexus import cli

    assert "if packet is not None:" in inspect.getsource(cli.query)


@pytest.mark.parametrize("path,expected", [
    ("/search/answer", ANSWER_ARGS),
    ("/search/answer/stream", ANSWER_ARGS),
    ("/search", SEARCH_ARGS),
])
def test_each_http_path_passes_the_arguments_it_passed_before(path, expected, monkeypatch):
    from fastapi.testclient import TestClient

    from nexus import api, db
    from nexus.llm.answer import AnswerResult
    from nexus.search.hybrid import SearchResult

    token = "p" * 40
    monkeypatch.setenv("NEXUS_DEV_TOKEN", token)
    seen: dict = {}

    async def _search(**k):
        seen["args"] = set(k)
        return SearchResult(route_used="hybrid_only")

    async def _noop(*a, **k):
        return None

    async def _generate(*a, **k):
        return AnswerResult(answer="ok")

    class _Unconfigured:
        configured = False

        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(api, "hybrid_search", _search)
    monkeypatch.setattr(api, "generate_answer", _generate)
    monkeypatch.setattr(api, "_load_config", lambda *a, **k: {})
    monkeypatch.setattr(api, "embedding_service_from_config", lambda *a, **k: None)
    monkeypatch.setattr(api, "LLMService", _Unconfigured)
    monkeypatch.setattr(api.db, "get_pool", _noop)
    monkeypatch.setattr(api, "PostgresGraphRepository", lambda *a, **k: None)
    monkeypatch.setattr(api, "_load_gazetteer", lambda *a, **k: {})
    monkeypatch.setattr(api, "_build_entity_patterns", lambda *a, **k: {})
    monkeypatch.setattr(api, "find_entities_in_text", lambda *a, **k: [])
    monkeypatch.setattr(api, "extract_signals", lambda *a, **k: None)
    monkeypatch.setattr(api, "record_search", _noop)

    async def _packet(*a, **k):
        return SimpleNamespace(snippets=[], provenance=[], graph=None, searched_tenants=["default"],
                               prompt_version="", corpus_version="", search_fingerprint="",
                               debts=[], code_values=[])

    monkeypatch.setattr(api, "packet_for_answer", _packet)
    saved = db._pool
    try:
        r = TestClient(api.app).post(path, json={"query": "q"},
                                     headers={"Authorization": "Bearer " + token})
    finally:
        db._pool = saved
    assert r.status_code == 200, r.text
    assert seen["args"] == expected, (
        f"{path}: added {sorted(seen['args'] - expected)}, dropped {sorted(expected - seen['args'])}")
