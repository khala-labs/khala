"""Read `config.yaml` — one function for the whole package.

⛔ **Why (2026-11-12 structure review).** Five modules carried their own `_load_config`
(`api`, `cli`, `ingest/pipeline`, `search/purge_schedule`, and a nested copy in `a2a/server`), and
17 scripts imported the one in `nexus.api` — loading the whole FastAPI app just to read YAML.
They all did the same thing, so any change (a path override, a warning) had five places to miss.

The modules keep their `_load_config` names as thin wrappers: tests replace
`api._load_config` (and `cli._load_config`) by attribute, and those replacements must keep working.

Behaviour is today's: the path is relative to the working directory, a missing file is an empty
dict, an empty file is an empty dict, a malformed file raises.
"""

from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_PATH = "config.yaml"


def load_config(path: str | Path = DEFAULT_PATH, *, warn_missing: bool = False) -> dict:
    """Parse the YAML config at ``path``; ``{}`` when the file does not exist."""
    p = Path(path)
    if not p.exists():
        if warn_missing:
            import structlog

            structlog.get_logger(__name__).warning("config_not_found", path=str(path))
        return {}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
