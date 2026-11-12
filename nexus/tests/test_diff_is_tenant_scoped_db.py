"""The design-vs-observed diff stays inside the caller's tenant and clearance.

⛔ **Why (2026-11-12 structure review).** `GraphRepository.get_diff(tenant)` ran
`SELECT * FROM v_edge_diff`, and that view has no tenant column — so `GET /diff` and the diff
flags in `/search` returned **every tenant's** edges, and `_tag_quality_flags` then updated
those edges by rid alone. The leak is in SQL, so only a real database can show it
(SPEC-nexus-graph-scope-filter is the rule; this surface had missed it).
"""

from __future__ import annotations

import pytest

from nexus import db
from nexus.otel.diff_engine import _tag_quality_flags
from nexus.repositories.graph import PostgresGraphRepository
from nexus.rid import edge_rid, entity_rid

pytestmark = pytest.mark.integration


async def _ent(conn, tenant, name, *, classification="INTERNAL", quarantined=False):
    rid = entity_rid(tenant, "service", name)
    await conn.execute(
        """INSERT INTO entities (rid, tenant, entity_type, name, classification, is_quarantined,
                                 source_uri, hash)
           VALUES ($1, $2, 'service', $3, $4::classification_level, $5, 'test:diff', 'h')""",
        rid, tenant, name, classification, quarantined,
    )
    return rid


async def _edge(conn, tenant, frm, to):
    rid = edge_rid(tenant, "CALLS", frm, to)
    await conn.execute(
        """INSERT INTO edges (rid, tenant, edge_type, from_rid, to_rid, confidence)
           VALUES ($1, $2, 'CALLS', $3, $4, 0.9)""",
        rid, tenant, frm, to,
    )
    return rid


async def _seed(conn) -> dict:
    """Designed-only edges: one in scope, one in another tenant, one over clearance, one quarantined."""
    a1 = await _ent(conn, "default", "a1")
    a2 = await _ent(conn, "default", "a2")
    b1 = await _ent(conn, "other", "b1")
    b2 = await _ent(conn, "other", "b2")
    secret = await _ent(conn, "default", "a_secret", classification="RESTRICTED")
    quar = await _ent(conn, "default", "a_quar", quarantined=True)
    return {
        "mine": await _edge(conn, "default", a1, a2),
        "theirs": await _edge(conn, "other", b1, b2),
        "secret": await _edge(conn, "default", a1, secret),
        "quar": await _edge(conn, "default", a1, quar),
    }


async def test_the_diff_never_returns_another_tenants_edges(db_pool):
    async with db_pool.acquire() as conn:
        e = await _seed(conn)
    repo = PostgresGraphRepository(db_pool)

    rids = {d.edge_rid for d in await repo.get_diff("default", "INTERNAL")}

    assert e["mine"] in rids
    assert e["theirs"] not in rids, "another tenant's edge leaked into the diff"
    assert e["secret"] not in rids, "an edge to an over-clearance entity leaked into the diff"
    assert e["quar"] not in rids, "an edge to a quarantined entity leaked into the diff"


async def test_without_clearance_the_tenant_still_bounds_the_diff(db_pool):
    """The maintenance call (tagging) skips the clearance filter — never the tenant filter."""
    async with db_pool.acquire() as conn:
        e = await _seed(conn)
    repo = PostgresGraphRepository(db_pool)

    rids = {d.edge_rid for d in await repo.get_diff("default")}

    assert {e["mine"], e["secret"]} <= rids
    assert e["theirs"] not in rids


async def test_tagging_touches_only_the_callers_tenant(db_pool):
    async with db_pool.acquire() as conn:
        e = await _seed(conn)
    db._pool = db_pool
    repo = PostgresGraphRepository(db_pool)
    other_diffs = await repo.get_diff("other")

    # A diff list from tenant "other", tagged under tenant "default", must change nothing.
    await _tag_quality_flags(other_diffs, "default")

    async with db_pool.acquire() as conn:
        flags = await conn.fetchval("SELECT quality_flags FROM edges WHERE rid = $1", e["theirs"])
    assert "doc_only" not in (flags or [])
