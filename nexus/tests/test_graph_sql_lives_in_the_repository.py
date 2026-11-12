"""그래프 표를 만지는 SQL 은 `nexus/repositories/graph.py` 에만 있다.

⛔ **왜 (2026-11-12 구조 점검).** `entities` · `edges` · `observed_edges` · `evidence` ·
`v_edge_diff` 를 읽고 쓰는 SQL 이 `api.py` · `cli.py` · `index/graph_extractor.py` ·
`otel/diff_engine.py` · `otel/aggregator.py` 에 22곳 흩어져 있었다. 그중 `/graph` 와 `/diff` 의
증거 조회는 같은 정책 필터를 **두 벌** 갖고 있었고, `/diff` 쪽은 필터 없이 남아 있다가
2026-11-12 에야 고쳐졌다. 2026-11-13 에 전부 저장소로 옮겼다 — SQL 은 글자 그대로다.

이 검사는 패키지(`nexus/nexus`)의 **문자열 상수**를 읽어, 그래프 표 이름 앞에
`FROM` · `JOIN` · `INTO` · `UPDATE` 가 오는 것을 저장소 밖에서 찾는다. 하나라도 있으면 붉다.

⚠ 스크립트(`nexus/scripts`)와 마이그레이션 SQL 파일은 세지 않는다 — 일회성 도구와 스키마 정의다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "nexus"
REPOSITORY = PACKAGE / "repositories" / "graph.py"

GRAPH_SQL = re.compile(
    r"\b(FROM|JOIN|INTO|UPDATE)\s+"
    r"(entities|edges|observed_edges|evidence|v_edge_diff|f_graph_neighbors)\b",
    re.IGNORECASE,
)


def _graph_sql(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [f"{path.relative_to(PACKAGE.parent)}:{n.lineno} {m.group(0)}"
            for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            for m in GRAPH_SQL.finditer(n.value)]


def test_no_graph_sql_outside_the_repository():
    found = [hit for f in sorted(PACKAGE.rglob("*.py")) if f != REPOSITORY
             for hit in _graph_sql(f)]
    assert found == [], "그래프 표를 만지는 SQL 은 repositories/graph.py 로:\n" + "\n".join(found)


def test_the_check_can_actually_fail(tmp_path):
    """⛔ 일부러 깨뜨려 본다 — 빈 목록이 '패턴이 안 맞는다' 일 수도 있다."""
    sample = tmp_path / "sample.py"
    sample.write_text('Q = """\n    SELECT 1\n    FROM evidence ev\n"""\nR = "update Edges set x = 1"\n',
                      encoding="utf-8")
    hits = [m.group(0) for n in ast.walk(ast.parse(sample.read_text(encoding="utf-8")))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            for m in GRAPH_SQL.finditer(n.value)]
    assert len(hits) == 2


def test_the_repository_itself_is_seen():
    """대조군 — 저장소 안의 SQL 은 이 패턴에 걸린다. 안 걸리면 위 검사는 아무것도 안 본다."""
    assert len(_graph_sql(REPOSITORY)) >= 20


def test_graph_and_diff_share_one_evidence_query():
    """같은 정책 필터가 두 벌이던 자리 — 이제 두 엔드포인트가 한 함수를 부른다."""
    from nexus import api

    for handler in (api.get_graph, api.get_diff):
        assert "edge_evidence" in handler.__code__.co_names, handler.__name__
