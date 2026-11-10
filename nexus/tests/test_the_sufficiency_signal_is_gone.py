"""충분성 신호를 되돌린 뒤의 상태 — ADR-0012 가 말한 것이 코드와 스키마에 그대로인가.

되돌리는 변경은 테스트 29 를 지운다. 지우기만 하면 **되돌렸다는 주장 자체를 아무것도 안 지킨다**
(비평 I-007). 그래서 세 가지를 못 박는다:

* 네 환경변수를 읽는 코드가 없다 — 이름만 남아 있어도 「끈 것」과 「없는 것」이 섞인다.
* 마이그레이션 052 뒤에 네 칸과 CHECK 제약이 없다.
* 052 는 두 번 돌아도 같다(멱등) — 파일 머리말이 그렇다고 적어 뒀으니 확인한다.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "nexus"
_MIGRATION = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "052_drop_the_sufficiency_signal.sql"
_ENV = re.compile(r"NEXUS_SUFFICIENCY\w*")
_COLUMNS = ("sufficiency", "sufficiency_at", "sufficiency_judge", "evidence_fingerprint")


def test_no_module_reads_the_sufficiency_environment_variables():
    """읽는 자리를 겨눈다 — `os.getenv("NEXUS_SUFFICIENCY…")` 가 제품 코드 어디에도 없다."""
    hits = []
    for p in _SRC.rglob("*.py"):
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _ENV.search(line):
                hits.append(f"{p.relative_to(_SRC)}:{n}: {line.strip()}")
    assert hits == [], "\n".join(hits)


def test_the_insert_names_none_of_the_dropped_columns():
    text = (_SRC / "search" / "signals.py").read_text(encoding="utf-8")
    insert = text[text.index("INSERT INTO search_log"):text.index("RETURNING id")]
    present = [c for c in _COLUMNS if re.search(rf"\b{c}\b", insert)]
    assert present == [], present


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_052_leaves_no_sufficiency_column_and_is_idempotent(db_url):
    import asyncpg

    conn = await asyncpg.connect(db_url)
    try:
        cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'search_log' AND column_name = ANY($1::text[])", list(_COLUMNS))
        assert cols == [], [r["column_name"] for r in cols]
        checks = await conn.fetchval(
            "SELECT count(*) FROM pg_constraint WHERE conname = 'search_log_sufficiency_check'")
        assert checks == 0
        # 두 번째 적용 — 칸이 이미 없어도 오류 없이 끝나야 멱등이다.
        await conn.execute(_MIGRATION.read_text(encoding="utf-8"))
        assert await conn.fetchval(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = 'search_log' AND column_name = ANY($1::text[])", list(_COLUMNS)) == 0
    finally:
        await conn.close()
