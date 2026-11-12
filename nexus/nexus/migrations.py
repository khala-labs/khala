"""어떤 마이그레이션이 아직 안 됐는가 — 그 판정 하나. 러너(`scripts/migrate.py`)와 진단(`schema_health`)이 같이 쓴다.

⛔ **왜 패키지 안에 있나 (2026-11-12 구조 점검).** 이 규칙은 `scripts/migrate.py` 에 있었고,
`nexus/schema_health.py` 가 그것을 `from scripts.migrate import ...` 로 가져왔다. `scripts/` 는
패키지가 아니라 저장소 디렉터리라, 저장소 루트가 경로에 없는 설치(`pip install` 한 패키지)에서는
그 import 가 실패한다. 진단은 실패를 삼키게 돼 있어서 `/status` 의 `pending_migrations` 가
**조용히 빈 목록**이 됐다 — "밀린 것 없음" 과 구별되지 않는다. 규칙을 패키지로 옮기고 러너가
여기서 가져가게 해서, 두 판정이 한 함수로 남는다.
"""

from __future__ import annotations

from pathlib import Path

#: `nexus/migrations/` — 이 패키지 디렉터리의 형제다.
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def migration_version(path: Path) -> str:
    """파일명을 버전 키로 사용(예: 001_add_x.sql)."""
    return path.name


def pending_migrations(all_files: list[Path], applied: set[str]) -> list[Path]:
    """아직 적용되지 않은 마이그레이션을 파일명 정렬 순으로 반환."""
    return [
        f for f in sorted(all_files, key=lambda p: p.name)
        if migration_version(f) not in applied
    ]
