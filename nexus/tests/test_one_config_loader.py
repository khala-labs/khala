"""`nexus.config.load_config` is the one reader of `config.yaml`.

⛔ **Why (2026-11-12 structure review).** Five private copies of `_load_config` lived in the
package and 17 scripts reached the one in `nexus.api`, importing the whole FastAPI app to read a
YAML file. These tests pin today's behaviour of the single function and keep the copies gone.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from nexus.config import load_config

NEXUS = Path(__file__).resolve().parents[1]


def test_a_missing_file_is_an_empty_dict(tmp_path):
    assert load_config(tmp_path / "absent.yaml") == {}


def test_an_empty_file_is_an_empty_dict(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("", encoding="utf-8")
    assert load_config(p) == {}


def test_a_file_is_parsed(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("a:\n  b: 1\n", encoding="utf-8")
    assert load_config(p) == {"a": {"b": 1}}


def test_a_malformed_file_raises(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("a: [1,\n", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        load_config(p)


def test_the_ingest_path_still_warns_when_the_file_is_missing(tmp_path):
    from structlog.testing import capture_logs

    with capture_logs() as logs:
        assert load_config(tmp_path / "absent.yaml", warn_missing=True) == {}
    assert any(e.get("event") == "config_not_found" for e in logs)


def test_the_module_wrappers_delegate(monkeypatch, tmp_path):
    """`api._load_config` and `cli._load_config` stay as names tests patch, but read through here."""
    from nexus import api, cli

    (tmp_path / "config.yaml").write_text("marker: 7\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert api._load_config() == {"marker": 7}
    assert cli._load_config() == {"marker": 7}


def test_no_second_copy_of_the_loader_comes_back():
    """A `_load_config` that parses YAML itself (outside `nexus/config.py`) is red."""
    import ast

    copies = []
    for f in (NEXUS / "nexus").rglob("*.py"):
        if f == NEXUS / "nexus" / "config.py":
            continue
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.FunctionDef) and node.name == "_load_config":
                calls = {getattr(n.func, "attr", None) for n in ast.walk(node)
                         if isinstance(n, ast.Call)}
                if "safe_load" in calls:
                    copies.append(f"{f.relative_to(NEXUS)}:{node.lineno}")
    assert copies == []


def test_scripts_do_not_import_the_app_to_read_config():
    offenders = [f.name for f in (NEXUS / "scripts").glob("*.py")
                 if re.search(r"from nexus\.(api|cli) import _load_config\b",
                              f.read_text(encoding="utf-8"))]
    assert offenders == []
