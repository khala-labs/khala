"""The console/MCP Notion sync refuses to wipe text already read from images — like the CLI does.

⛔ **Why (2026-11-12 structure review).** `vision_guard.refusal` was called only from
`cli.py ingest-notion`. The HTTP sync job (`sources/sync_job.py`, used by the web console and
the MCP `nexus_sources_sync` tool) walks the same `import_notion` → `_fill_images` path, which
replaces image placeholders with empty images when `NEXUS_VISION` is off. That is the
2026-09-02 incident (466 → 385 chunks, live answers turned into abstentions), reachable from a
second door with no guard.

These tests need no database and no A2A SDK: the refusal path returns before the sync imports
the ingest function.
"""

from __future__ import annotations

import pytest

from nexus.ingest import vision_guard
from nexus.sources import runs_store, sync_job


@pytest.fixture
def five_machine_read(monkeypatch):
    async def _count(tenant):
        return 5

    monkeypatch.setattr(vision_guard, "count_machine_read", _count)


@pytest.fixture
def finished(monkeypatch):
    seen: list[dict] = []

    async def _finish(run_id, **kw):
        seen.append({"run_id": run_id, **kw})

    monkeypatch.setattr(runs_store, "finish_run", _finish)
    return seen


def _never_called(*a, **k):
    raise AssertionError("the sync walked Notion although it should have refused")


async def _walk(**over):
    kw = dict(run_id="r1", tenant="t", roots=["root"], reconcile=False, dry_run=False,
              force=False, since="", threshold=0.5, confirm_run=None,
              source_factory=_never_called)
    kw.update(over)
    await sync_job._walk_and_apply(**kw)


async def test_with_vision_off_the_sync_refuses_and_says_why(five_machine_read, finished,
                                                            monkeypatch):
    monkeypatch.delenv("NEXUS_VISION", raising=False)
    monkeypatch.delenv(vision_guard.OVERRIDE_ENV, raising=False)

    await _walk()

    assert len(finished) == 1
    assert finished[0]["status"] == "failed"
    assert finished[0]["reason"].startswith("vision_guard: ")
    assert "5" in finished[0]["reason"]


async def test_a_preview_run_is_refused_too(five_machine_read, finished, monkeypatch):
    """`dry_run` stops only the reconcile planner here — `import_notion` still writes."""
    monkeypatch.delenv("NEXUS_VISION", raising=False)
    monkeypatch.delenv(vision_guard.OVERRIDE_ENV, raising=False)

    await _walk(dry_run=True)

    assert [f["status"] for f in finished] == ["failed"]


@pytest.mark.parametrize("env", [{"NEXUS_VISION": "on"}, {vision_guard.OVERRIDE_ENV: "1"}])
async def test_vision_on_or_a_declared_drop_lets_it_through(five_machine_read, monkeypatch, env):
    monkeypatch.delenv("NEXUS_VISION", raising=False)
    monkeypatch.delenv(vision_guard.OVERRIDE_ENV, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    assert await sync_job.vision_refusal("t") == ""


async def test_nothing_to_lose_lets_it_through(monkeypatch):
    async def _none(tenant):
        return 0

    monkeypatch.setattr(vision_guard, "count_machine_read", _none)
    monkeypatch.delenv("NEXUS_VISION", raising=False)

    assert await sync_job.vision_refusal("t") == ""
