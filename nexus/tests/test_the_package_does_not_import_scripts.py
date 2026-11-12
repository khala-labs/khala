"""패키지(`nexus/nexus`)는 저장소 디렉터리 `scripts/` 를 import 하지 않는다.

⛔ **왜 (2026-11-12 구조 점검).** `schema_health` 가 `from scripts.migrate import ...` 를 했다.
`scripts/` 는 패키지가 아니라 저장소 디렉터리라, 저장소 루트가 경로에 없는 설치에서는 이 import 가
실패하고, 진단은 실패를 삼켜 `/status` 의 밀린 마이그레이션 목록이 조용히 비었다. 판정 규칙은
`nexus/migrations.py` 로 옮겼고, 이 검사가 같은 길이 다시 생기지 않게 한다.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "nexus"


def _imports_scripts(tree: ast.AST) -> list[int]:
    lines = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "scripts":
            lines.append(n.lineno)
        elif isinstance(n, ast.Import) and any(a.name.split(".")[0] == "scripts" for a in n.names):
            lines.append(n.lineno)
    return lines


def test_no_package_module_imports_scripts():
    found = [f"{f.relative_to(PACKAGE.parent)}:{ln}"
             for f in sorted(PACKAGE.rglob("*.py"))
             for ln in _imports_scripts(ast.parse(f.read_text(encoding="utf-8")))]
    assert found == []


def test_the_check_can_actually_fail():
    """대조군 — 함수 안의 지연 import 도 잡는다(옮기기 전의 모양이 그것이었다)."""
    tree = ast.parse("def f():\n    from scripts.migrate import pending_migrations\n")
    assert _imports_scripts(tree) == [2]


def test_the_runner_and_the_diagnostic_share_one_rule():
    from nexus import migrations, schema_health
    from scripts import migrate

    assert migrate.pending_migrations is migrations.pending_migrations
    assert schema_health.MIGRATIONS_DIR == migrate.MIGRATIONS_DIR == migrations.MIGRATIONS_DIR
