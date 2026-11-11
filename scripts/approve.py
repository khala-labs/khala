#!/usr/bin/env python
"""Approve one SPEC or ADR in this repository's Arbiter ledger — one short command.

    python scripts/approve.py <artifact-id>
    python scripts/approve.py <artifact-id> --dispositions <file> --approver <name>

⛔ **Why this exists (2026-11-12).** Approving meant typing by hand
`ARBITER_ROOT=… ARBITER_DOCS=… arbiter approve <id> --dispositions <path> --approver <name>`.
The owner did that twice on one SPEC and neither run took effect. Arbiter's CLI defaults
`ARBITER_DOCS` to `<root>/docs`, and `Ledger.__init__` creates `specs/`, `adr/` and `.reviews/`
under whatever path it gets. So when the variable is missing (shell syntax differs between
PowerShell and Git Bash), the CLI opens an empty ledger under `docs/` and exits without a word.
The stray `docs/.reviews/` and `docs/adr/` left in a checkout on that day are what that looks like.

This script fixes the paths instead of asking for them:

- the ledger is always `<repo>/records` — the only ledger this repository has;
- it **refuses** to run if `records/specs`, `records/adr` or `records/.reviews` is missing,
  so it can never create a ledger somewhere else;
- dispositions default to `records/.reviews/dispositions-<id>.json`;
- the approver defaults to `git config user.name` of this repository.

It then calls the same `review.approve()` the CLI calls, and adds the id to
`records/governance/integrity-manifest.txt` so `ledger_integrity.py` keeps checking the stamp.

⚠ **It does not make the signature stronger.** `approved_by` is still a string, as with the CLI.
What it adds is that the owner runs one short command (or allows one prompt) instead of a long
one. It does not regenerate `records/INDEX.md`: `Ledger.index()` calls `Ledger.status()`, which
rewrites files (see `ledger_integrity.py`).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records"
MANIFEST = RECORDS / "governance" / "integrity-manifest.txt"
LEDGER_DIRS = ("specs", "adr", ".reviews")


class ApproveError(RuntimeError):
    """A refusal with a message meant for the person running the script."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_ledger(records: Path) -> None:
    """Refuse unless every ledger directory already exists under ``records``."""
    missing = [d for d in LEDGER_DIRS if not (records / d).is_dir()]
    if missing:
        raise ApproveError(
            f"ledger directories missing under {records}: {', '.join(missing)} — "
            "refusing so no new ledger is created by accident")


def default_dispositions(records: Path, artifact_id: str) -> Path:
    return records / ".reviews" / f"dispositions-{artifact_id}.json"


def default_approver(root: Path) -> str:
    try:
        out = subprocess.run(["git", "config", "user.name"], cwd=root, capture_output=True,
                             text=True, check=False)
    except OSError:
        out = None
    name = (out.stdout.strip() if out else "")
    if not name:
        raise ApproveError("no approver: pass --approver or set `git config user.name`")
    return name


def add_to_manifest(manifest: Path, artifact_id: str) -> bool:
    """Add ``artifact_id`` to the manifest, keeping header comments and sorted ids.

    Returns ``False`` if it was already listed.
    """
    lines = manifest.read_text(encoding="utf-8").splitlines()
    header = [ln for ln in lines if ln.startswith("#") or not ln.strip()]
    ids = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    if artifact_id in ids:
        return False
    ids = sorted(ids + [artifact_id])
    manifest.write_text("\n".join(header + ids) + "\n", encoding="utf-8", newline="\n")
    return True


def approve(artifact_id: str, dispositions: Path | None, approver: str | None,
            root: Path = ROOT) -> str:
    """Approve ``artifact_id``; return the resulting status line."""
    records = root / "records"
    check_ledger(records)
    disp_path = dispositions or default_dispositions(records, artifact_id)
    try:
        disp = json.loads(disp_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ApproveError(f"cannot read dispositions {disp_path}: {e}") from None
    who = approver or default_approver(root)

    from khala.arbiter import review
    from khala.arbiter.artifacts import Artifact
    from khala.arbiter.ledger import Ledger

    ledger = Ledger(records, now=_utc_now)
    review.approve(ledger, artifact_id, disp, who, now=_utc_now)
    art = Artifact.load(ledger._resolve(artifact_id))
    add_to_manifest(root / "records" / "governance" / "integrity-manifest.txt", artifact_id)
    return f"{artifact_id}: {art.meta.get('status')} by {who} ({art.meta.get('content_hash')})"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("artifact_id")
    ap.add_argument("--dispositions", type=Path, default=None)
    ap.add_argument("--approver", default=None)
    ap.add_argument("--root", type=Path, default=ROOT,
                    help="repository root (default: this script's repository)")
    a = ap.parse_args(argv)
    try:
        print(approve(a.artifact_id, a.dispositions, a.approver, root=a.root.resolve()))
    except ApproveError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 — Arbiter's ReviewError and friends, as one line
        print(f"refused by Arbiter: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
