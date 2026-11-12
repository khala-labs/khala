"""`scripts/check_index.py` — INDEX.md is what Arbiter generates from the ledger, or CI is red.

⛔ **Why (2026-11-12).** INDEX.md said "generated, do not edit by hand", but nothing generated
or compared it, and it had drifted to 50 rows for 67 artifacts. Pinned from both sides: a stale
index fails *and is left as it was* (a check must not edit the evidence), a fresh one passes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_index as ci  # noqa: E402

pytest.importorskip("khala.arbiter")


def _ledger(tmp: Path) -> Path:
    from khala.arbiter.ledger import Ledger

    records = tmp / "records"
    for d in ("specs", "adr", ".reviews"):
        (records / d).mkdir(parents=True)
    Ledger(records, now=lambda: "2026-11-12T00:00:00Z").record("spec", "A small spec", slug="small")
    return records


def test_a_fresh_index_passes(tmp_path):
    records = _ledger(tmp_path)
    assert ci.main(["--records", str(records), "--write"]) == 0
    assert ci.main(["--records", str(records)]) == 0


def test_a_stale_index_fails_and_is_left_untouched(tmp_path, capsys):
    records = _ledger(tmp_path)
    stale = "# Arbiter Index\n\n## 🟢 승인 (0)\n"
    (records / "INDEX.md").write_text(stale, encoding="utf-8")

    assert ci.main(["--records", str(records)]) == 1
    assert (records / "INDEX.md").read_text(encoding="utf-8") == stale
    assert "SPEC-small" in capsys.readouterr().out


def test_a_missing_ledger_is_refused_not_created(tmp_path):
    with pytest.raises(SystemExit, match="missing"):
        ci.main(["--records", str(tmp_path / "records")])
    assert not (tmp_path / "records").exists()


def test_the_real_index_matches_the_ledger():
    """The committed INDEX.md in this repository is current."""
    assert ci.main([]) == 0
