"""The stream sends every key `/search/answer` sends — one list of exceptions, written down here.

⛔ **Why (SPEC-nexus-shared-answer-pipeline §4.3, §6).** The stream re-implemented the answer
path's evidence shaping inline and drifted, none of it on purpose: provenance carried
`doc_title` where the answer path carried `approved_hash`; observed graph edges said
`call_count` where the answer path said `calls`; the `done` event lacked `abstained`,
`abstain_reason` and `n_unknown_origin_time`. A consumer of the stream (the web chat) could not
see what a consumer of the answer path (MCP, the Slack bot) saw.

So the stream's `evidence` + `done` events together must carry **every** key of the answer
path's `data`, except the ones listed in :data:`ALLOWED_MISSING` with their reason. A new key
added to one path only turns this red.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from nexus import api
from nexus.llm.answer import abstention, evidence_view
from nexus.search import evidence_packet
from nexus.search.hybrid import SearchHit, SearchResult

_TOKEN = "s" * 40
_AUTH = {"Authorization": "Bearer " + _TOKEN}

#: Keys of `/search/answer`'s `data` the stream does not send, and why. Keep it this short.
ALLOWED_MISSING = {
    # The stream takes `evidence_only` in its request but ignores it and always generates, so
    # sending the flag would describe a mode it does not run. Whether it should honour the flag
    # is an open question (SPEC §8).
    "evidence_only",
}


def _hit(rid: str, doc: str, title: str) -> SearchHit:
    return SearchHit(rid=rid, doc_rid=doc, doc_title=title, section_path="§1",
                     snippet=f"{title} 본문", chunk_text=f"{title} 본문", score=0.05)


class _Unconfigured:
    """No model key — both paths skip the model, so the test needs no LLM."""

    configured = False

    def __init__(self, *a, **k):
        pass


@pytest.fixture
def client(monkeypatch):
    from nexus import db

    monkeypatch.setenv("NEXUS_DEV_TOKEN", _TOKEN)
    state = {"hits": [_hit("c1", "d1", "SOP-01")]}

    async def _noop_async(*a, **k):
        return None

    async def _no_rows(*a, **k):
        return {}

    async def _search(*a, **k):
        r = SearchResult(route_used="hybrid_only")
        r.hits = list(state["hits"])
        return r

    monkeypatch.setattr(api, "_load_config", lambda *a, **k: {})
    monkeypatch.setattr(api, "embedding_service_from_config", lambda *a, **k: None)
    monkeypatch.setattr(api, "LLMService", _Unconfigured)
    monkeypatch.setattr(api.db, "get_pool", _noop_async)
    monkeypatch.setattr(api, "PostgresGraphRepository", lambda *a, **k: None)
    monkeypatch.setattr(api, "_load_gazetteer", lambda *a, **k: {})
    monkeypatch.setattr(api, "_build_entity_patterns", lambda *a, **k: {})
    monkeypatch.setattr(api, "find_entities_in_text", lambda *a, **k: [])
    monkeypatch.setattr(api, "hybrid_search", _search)
    monkeypatch.setattr(evidence_packet, "statuses_for_chunks", _no_rows)
    monkeypatch.setattr(evidence_packet, "debts_for_docs", _no_rows)
    monkeypatch.setattr(api, "extract_signals", lambda *a, **k: None)
    monkeypatch.setattr(api, "record_search", _noop_async)

    saved = db._pool
    try:
        c = TestClient(api.app)
        c.state = state
        yield c
    finally:
        db._pool = saved


def _answer(client) -> dict:
    r = client.post("/search/answer", json={"query": "q"}, headers=_AUTH)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _events(client) -> dict[str, dict]:
    r = client.post("/search/answer/stream", json={"query": "q"}, headers=_AUTH)
    assert r.status_code == 200, r.text
    out = {}
    for blk in r.text.strip().split("\n\n"):
        head, _, data = blk.partition("\ndata: ")
        out[head.removeprefix("event: ")] = json.loads(data)
    assert "error" not in out, out.get("error")
    return out


def test_the_stream_carries_every_key_the_answer_carries(client):
    answer_keys = set(_answer(client))
    ev = _events(client)
    stream_keys = set(ev["evidence"]) | set(ev["done"])
    missing = answer_keys - stream_keys - ALLOWED_MISSING
    assert not missing, f"the stream does not send {sorted(missing)}"


def test_the_allowlist_has_no_stale_entries(client):
    """An exception that no longer applies hides the next real one."""
    answer_keys = set(_answer(client))
    ev = _events(client)
    stream_keys = set(ev["evidence"]) | set(ev["done"])
    assert ALLOWED_MISSING <= answer_keys - stream_keys


@pytest.mark.parametrize("hits", [True, False], ids=["with-evidence", "no-evidence"])
def test_both_paths_agree_on_abstention(client, hits):
    if not hits:
        client.state["hits"] = []
    data, done = _answer(client), _events(client)["done"]
    assert (done["abstained"], done["abstain_reason"]) == (
        data["abstained"], data["abstain_reason"])
    assert data["abstained"] is (not hits)


def test_both_paths_send_the_same_provenance_fields(client):
    a = {k for p in _answer(client)["provenance"] for k in p}
    s = {k for p in _events(client)["evidence"]["provenance"] for k in p}
    assert a == s and {"approved_hash", "doc_title"} <= a


# ── evidence_view itself ─────────────────────────────────────────────────────────────

def _packet(snippets=()):
    edge = SimpleNamespace(edge_type="CALLS", from_name="a", to_name="b", call_count=7,
                           error_rate=0.1, latency_p95=12, trace_query_ref=None)
    designed = SimpleNamespace(edge_type="CALLS", from_name="a", to_name="b",
                               confidence=0.9, source_category="design")
    graph = SimpleNamespace(center_name="a", edges=[designed], observed_edges=[edge])
    prov = SimpleNamespace(doc_rid="d", source_uri="git://d", source_version="v1",
                           approved_hash="h", doc_title="D")
    return SimpleNamespace(snippets=list(snippets), graph=graph, provenance=[prov])


def test_observed_edges_carry_both_names_for_the_call_count():
    """The web chat reads `call_count`; the answer path sent `calls`. Neither loses its key."""
    edge = evidence_view(_packet()).graph_findings["observed_edges"][0]
    assert edge["calls"] == edge["call_count"] == 7


def test_provenance_carries_both_the_hash_and_the_title():
    prov = evidence_view(_packet()).provenance[0]
    assert prov["approved_hash"] == "h" and prov["doc_title"] == "D"


def test_abstention_is_decided_by_the_packet_alone():
    assert abstention(_packet()) == (True, "no_evidence")
    assert abstention(_packet(snippets=[object()])) == (False, "")
