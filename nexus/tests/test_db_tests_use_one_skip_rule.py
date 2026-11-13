"""DB 가 필요한 테스트는 마커(`db` · `integration`)로 표시하고, 건너뛰기는 `conftest.py` 한 곳이 정한다.

⛔ **왜 (2026-11-12 구조 점검).** 67개 파일이 저마다 `skipif(not os.getenv("NEXUS_TEST_DB_URL"))` 를
적었고, `integration` 마커만 conftest 가 걸렀다. 규칙이 두 군데라 어느 테스트가 정리(TRUNCATE)를
거치는지 파일을 열어야 알 수 있었다. 이 검사는 옛 모양 — DB URL 이 없다는 조건만으로 거는
`skipif` — 이 돌아오면 붉어진다.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
ENV = "NEXUS_TEST_DB_URL"


def _env_read(node) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("getenv", "get") and bool(node.args)
            and isinstance(node.args[0], ast.Constant) and node.args[0].value == ENV)


def _own_skips(source: str) -> list[int]:
    """`skipif(not <DB URL>)` 의 줄 번호 — 이름에 담아 둔 URL(`DB_URL = os.getenv(...)`)도 센다."""
    tree = ast.parse(source)
    names = {t.id for n in tree.body if isinstance(n, ast.Assign) and _env_read(n.value)
             for t in n.targets if isinstance(t, ast.Name)}
    lines = []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "skipif"
                and n.args and isinstance(n.args[0], ast.UnaryOp) and isinstance(n.args[0].op, ast.Not)):
            o = n.args[0].operand
            if _env_read(o) or (isinstance(o, ast.Name) and o.id in names):
                lines.append(n.lineno)
    return lines


def test_no_test_file_carries_its_own_db_skip():
    found = [f"{f.name}:{ln}" for f in sorted(TESTS.glob("test_*.py"))
             for ln in _own_skips(f.read_text(encoding="utf-8"))]
    assert found == [], "DB 가 필요한 테스트에는 `pytest.mark.db` 를 붙여라 (건너뛰기는 conftest 가 한다)"


_OLD_DIRECT = (
    "import os, pytest\n"
    '@pytest.mark.skipif(not os.getenv("NEXUS_TEST_DB_URL"), reason="x")\n'
    "def test_a(): ...\n"
)
_OLD_VIA_NAME = (
    "import os, pytest\n"
    'DB_URL = os.environ.get("NEXUS_TEST_DB_URL")\n'
    'pytestmark = [pytest.mark.skipif(not DB_URL, reason="x")]\n'
)


@pytest.mark.parametrize("source", [_OLD_DIRECT, _OLD_VIA_NAME], ids=["direct", "via-name"])
def test_the_check_can_actually_fail(source):
    assert _own_skips(source) != []


def test_the_db_marker_is_registered_and_skipped_by_conftest():
    options = tomllib.loads((TESTS.parent / "pyproject.toml").read_text(encoding="utf-8"))
    markers = options["tool"]["pytest"]["ini_options"]["markers"]
    assert any(m.startswith("db:") for m in markers)
    assert 'get_closest_marker("db")' in (TESTS / "conftest.py").read_text(encoding="utf-8")
