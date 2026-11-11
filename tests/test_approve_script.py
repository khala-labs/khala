"""`scripts/approve.py` — one short command that approves into `records/`, never anywhere else.

⛔ **The failure this pins (2026-11-12).** Arbiter's CLI, given no `ARBITER_DOCS`, opened an empty
ledger under `docs/` and exited quietly; two approvals were lost that way. The first test below is
the one that matters: a missing ledger directory is a refusal, and nothing gets created.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import approve as ap  # noqa: E402

BODY = "# A small spec\n\nIt says one thing.\n"


def _repo(tmp: Path) -> Path:
    """A throwaway repository root with an empty ledger and a manifest."""
    for d in ap.LEDGER_DIRS:
        (tmp / "records" / d).mkdir(parents=True)
    gov = tmp / "records" / "governance"
    gov.mkdir(parents=True)
    (gov / "integrity-manifest.txt").write_text(
        "# header line\nADR-0001\nSPEC-b\n", encoding="utf-8")
    return tmp


def test_a_missing_ledger_directory_is_refused_and_nothing_is_created(tmp_path):
    (tmp_path / "records" / "specs").mkdir(parents=True)
    with pytest.raises(ap.ApproveError, match="adr"):
        ap.approve("SPEC-x", None, "someone", root=tmp_path)
    assert not (tmp_path / "records" / "adr").exists()
    assert not (tmp_path / "docs").exists()


def test_dispositions_default_to_the_reviews_directory(tmp_path):
    assert ap.default_dispositions(tmp_path / "records", "SPEC-x") == (
        tmp_path / "records" / ".reviews" / "dispositions-SPEC-x.json")


def test_an_unreadable_dispositions_file_is_refused(tmp_path):
    root = _repo(tmp_path)
    with pytest.raises(ap.ApproveError, match="cannot read dispositions"):
        ap.approve("SPEC-x", None, "someone", root=root)


def test_the_manifest_keeps_its_header_and_sorted_ids(tmp_path):
    m = _repo(tmp_path) / "records" / "governance" / "integrity-manifest.txt"
    assert ap.add_to_manifest(m, "SPEC-a") is True
    assert m.read_text(encoding="utf-8") == "# header line\nADR-0001\nSPEC-a\nSPEC-b\n"
    assert ap.add_to_manifest(m, "SPEC-a") is False


def test_it_approves_through_arbiter_and_lists_the_id(tmp_path):
    pytest.importorskip("khala.arbiter")
    from khala.arbiter.artifacts import Artifact
    from khala.arbiter.ledger import Ledger
    from khala.arbiter.sidecar import Issue, Sidecar

    root = _repo(tmp_path)
    records = root / "records"
    ledger = Ledger(records, now=ap._utc_now)
    art_id = ledger.record("spec", "A small spec", slug="small")
    path = ledger._resolve(art_id)
    path.write_text(path.read_text(encoding="utf-8") + "\n" + BODY, encoding="utf-8")
    art = Artifact.load(path)
    Sidecar(target=art_id, critiqued_hash=art.recompute_hash(), critiqued_at=ap._utc_now(),
            issues=[Issue("I-001", "undefined", "low", "says too little", "open")]
            ).write(records / ".reviews" / f"{art_id}.md")
    (records / ".reviews" / f"dispositions-{art_id}.json").write_text(json.dumps(
        [{"issue_id": "I-001", "disposition": "rejected", "reason": "one thing is enough"}]),
        encoding="utf-8")

    line = ap.approve(art_id, None, "someone", root=root)

    art = Artifact.load(path)
    assert art.meta["status"] == "approved"
    assert art.meta["approved_by"] == "someone"
    assert art.meta["content_hash"] == art.recompute_hash()
    assert art_id in line and "someone" in line
    manifest = (records / "governance" / "integrity-manifest.txt").read_text(encoding="utf-8")
    assert art_id in manifest.splitlines()
