"""설계-관측 Diff Engine.

설계 edge(문서에서 추출)와 관측 edge(OTel에서 집계)를 비교하여
불일치를 탐지하고 quality_flags를 태깅한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

from nexus import db
from nexus.repositories.graph import DiffItem, PostgresGraphRepository

logger = structlog.get_logger(__name__)


@dataclass
class DiffReport:
    """Diff 보고서."""
    total_designed: int = 0
    total_observed: int = 0
    diffs: list[DiffItem] = field(default_factory=list)
    generated_at: str = ""


async def run_diff(
    tenant: str = "default",
    flag_filter: str | None = None,
    clearance: str | None = None,
) -> DiffReport:
    """설계-관측 diff 실행.

    1. v_edge_diff 뷰 조회
    2. quality_flags 태깅
    3. 보고서 생성

    Args:
        tenant: 테넌트 ID
        flag_filter: doc_only | observed_only | conflict (None이면 전체)

    Returns:
        DiffReport
    """
    report = DiffReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    # 통계
    pool = await db.get_pool()
    graph_repo = PostgresGraphRepository(pool)
    report.total_designed = await graph_repo.count_active("edges", tenant)
    report.total_observed = await graph_repo.count_active("observed_edges", tenant)

    # Diff 조회 — 테넌트(·등급) 안에서만 (`GraphRepository.get_diff`)
    # 태깅은 **테넌트 전체**(등급 무관)로 한다 — 호출자의 등급에 따라 플래그가 달라지면 안 된다.
    # 응답으로 나가는 목록은 호출자의 등급으로 다시 거른다(`clearance` 가 주어질 때).
    all_diffs = await graph_repo.get_diff(tenant)
    visible = all_diffs if clearance is None else await graph_repo.get_diff(tenant, clearance)

    # 필터 적용
    if flag_filter:
        report.diffs = [d for d in visible if d.flag == flag_filter]
    else:
        report.diffs = visible

    # quality_flags 태깅
    await _tag_quality_flags(all_diffs, tenant, graph_repo)

    logger.info("diff_complete",
                designed=report.total_designed,
                observed=report.total_observed,
                diffs=len(report.diffs))

    return report


async def _tag_quality_flags(diffs: list[DiffItem], tenant: str,
                             graph_repo: PostgresGraphRepository | None = None) -> None:
    """Diff 결과에 따라 edge/observed_edge의 quality_flags 갱신.

    ``graph_repo`` 를 안 주면 공용 풀로 하나 만든다 — 호출 계약 `(diffs, tenant)` 는 그대로다.
    """
    if graph_repo is None:
        graph_repo = PostgresGraphRepository(await db.get_pool())
    for diff in diffs:
        now = datetime.now(timezone.utc)

        if diff.flag == "doc_only" and diff.edge_rid:
            await graph_repo.tag_doc_only(diff.edge_rid, tenant, now)

        elif diff.flag == "observed_only" and diff.observed_edge_rid:
            await graph_repo.tag_observed_only(diff.observed_edge_rid, tenant, now)
