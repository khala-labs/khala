"""Importing `nexus.api` defines routes and nothing else — the app is built by `create_app()`.

⛔ **Why (2026-11-12 structure review).** Importing the module read `config.yaml` (for CORS
origins and the A2A flag), mounted A2A when the config enabled it, and attached the source
routers — at import time. Scripts that only wanted one helper (`from nexus.api import
_search_channels`) paid for all of that, and an A2A misconfiguration could fail an import that
had nothing to do with A2A. Now `create_app()` does that work, and `nexus.api.app` is built the
first time something reads it, so `uvicorn nexus.api:app` and the tests keep working.

The import check runs in a fresh interpreter: in this process the module is already imported.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

NEXUS = Path(__file__).resolve().parents[1]


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=NEXUS,
                          capture_output=True, text=True, timeout=120)


def test_import_reads_no_config_and_builds_no_app():
    """Config reads fail loudly in the child; the import must not trigger one."""
    r = _run("""
        import nexus.config as c
        def boom(*a, **k):
            raise SystemExit("config read during import")
        c.load_config = boom
        import nexus.api as api
        assert "app" not in vars(api), "the app was built at import"
        assert api.router.routes, "the routes were not defined"
        print("ok")
    """)
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr or r.stdout


def test_reading_app_builds_it_once_and_that_is_where_config_is_read():
    """Control — the config read happens when the app is built, not never."""
    r = _run("""
        import nexus.config as c
        calls = []
        real = c.load_config
        def counting(*a, **k):
            calls.append(1)
            return real(*a, **k)
        c.load_config = counting
        import nexus.api as api
        assert not calls
        app = api.app
        assert calls, "building the app read no config"
        assert api.app is app, "a second read built a second app"
        print("ok")
    """)
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr or r.stdout


def test_create_app_builds_a_fresh_app_with_the_routes_in_order():
    """Static is the catch-all and must stay last; the module's routes come after the source routers."""
    from nexus import api

    a, b = api.create_app(), api.create_app()
    assert a is not b
    assert getattr(a.routes[-1], "path", None) == "/static"
    included = [r for r in a.routes if getattr(r, "original_router", None) is not None]
    assert included and included[-1].original_router is api.router
