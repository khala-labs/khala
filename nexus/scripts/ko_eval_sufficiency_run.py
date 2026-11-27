"""충분성 판정기를 오프라인에서 측정하는 실행기 — 판정만 **기록**한다 (SPEC-nexus-abstention-gate §3.2).

채점은 이 파일이 하지 않는다. 비율·구간·통과 여부는 `ko_eval_sufficiency_score.py` 가 이 실행기가
남긴 파일을 읽어 낸다. 기록하는 실행과 판정하는 단계를 나눈 이유는 하나다: 숫자를 보면서 기록 방식을
고치는 일이 생기지 않게 한다.

**이 실행기가 지키는 것** (SPEC §3.2 의 번호):

1. 실행마다 자기 파일에 쓴다. 이름은 실행 id 이고, 같은 이름이 있으면 **쓰기를 거부한다**.
   2026-08-12 와 그 뒤 측정은 고정 파일명 때문에 앞 실행을 덮어 비교를 잃었다.
2. 두 실험군. 답할 수 있는 라벨의 패킷 그대로(answerable)와, 같은 패킷에서 gold 문서를 뺀 것
   (negative). 대상 라벨은 **실행 전에 규칙으로 정해진다**: gold 문서가 패킷에 하나라도 들어온
   답할 수 있는 라벨 전부. gold 가 패킷에 없던 라벨은 두 실험군 모두에서 빠지고, 그 id 가 파일에 남는다.
3. 판정기 호출 실패(`error`)와 형식 불일치(`unparseable`)를 따로 센다. `judge_raw` 를 부르므로
   호출 실패가 `unparseable` 로 접히지 않는다.
4. 판정기에 가는 근거는 답변 경로와 같은 함수로 만든다 (`retrieve_for_answer` → `format_for_llm`).
5. 판정기 식별 정보 네 가지를 모든 파일에 적는다: 백엔드, 설정된 모델, 프롬프트 SHA-256, 파서 SHA-256.
6. 판정 호출마다 지연(ms)을 적는다.
7. 유료 백엔드는 `--paid` 없이 거부한다.

**negative 실험군의 한계.** gold 를 빼도 다른 문서가 답을 담고 있을 수 있다. 그래서 탐지율은
하한이고, 그 실험군에서 `sufficient` 로 판정된 라벨은 채점기가 id 로 나열한다. 그래프 간선은
문서 단위로 뺄 수 없어 그대로 두고, 남은 간선 수를 행마다 적는다.

리포트는 기본으로 라벨 파일 옆(Pack B 는 gitignore 된 `tests/eval/local/`)에 쓴다. 판정 사유가
코퍼스 문장을 담을 수 있기 때문이다.

    docker exec nexus-app python scripts/ko_eval_sufficiency_run.py
    docker exec nexus-app python scripts/ko_eval_sufficiency_run.py --controls --out-dir /tmp/suff
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import inspect
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nexus.llm import sufficiency  # noqa: E402
from nexus.llm.dev_spend import Spend, paid_flag_help, require_free  # noqa: E402
from scripts.ko_eval_labels import ManifestPack, check, load  # noqa: E402
from scripts.ko_eval_packb import MANIFEST  # noqa: E402

LOCAL_DIR = Path(__file__).resolve().parents[1] / "tests" / "eval" / "local"
DEFAULT_LABELS = LOCAL_DIR / "packb-labels.yaml"
#: 판정 한 번의 시간 제한. 초과는 `error`(kind=timeout)로 기록하고 실행은 계속한다.
DEFAULT_TIMEOUT_SECONDS = 120.0
#: 이 파일 형식의 버전. 채점기가 모르는 버전을 거부한다.
ARTIFACT_VERSION = 1

ANSWERABLE, NEGATIVE, CONTROL = "answerable", "negative", "control"
STATUSES = ("sufficient", "insufficient", "unparseable", "error")


# ── 판정기 식별 정보 ─────────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompt_sha256() -> str:
    """판정기 프롬프트의 지문 — 시스템 문장과 사용자 프롬프트를 만드는 함수의 소스."""
    return _sha256(sufficiency.SYSTEM + "\n\x00\n" + inspect.getsource(sufficiency.build_prompt))


def parser_sha256() -> str:
    """판정 출력 파서의 지문 — `parse` 의 소스와 두 정규식."""
    return _sha256("\n\x00\n".join([
        inspect.getsource(sufficiency.parse),
        sufficiency._VERDICT.pattern, str(sufficiency._VERDICT.flags),
        sufficiency._REASON.pattern, str(sufficiency._REASON.flags),
    ]))


def judge_fingerprint(llm, model_setting: str | None) -> dict:
    """SPEC §3.2.5 의 네 부분. ``model_setting`` 은 **명시적으로 설정된** 모델 값이다
    (`--model` 또는 `NEXUS_LLM_MODEL`). 비어 있으면 None 으로 남긴다 — 백엔드 기본값을 설정값처럼
    적으면 §4.3 의 "설정 안 된 모델은 일치하지 않는다" 규칙이 기록에서부터 무너진다."""
    return {
        "backend": getattr(llm, "provider", None) or type(getattr(llm, "_backend", llm)).__name__,
        "model_setting": model_setting or None,
        "model_effective": getattr(llm, "model", None),
        "prompt_sha256": prompt_sha256(),
        "parser_sha256": parser_sha256(),
    }


# ── 패킷 조작 ───────────────────────────────────────────────────────────────────

def doc_key(source_uri: str) -> str:
    """`source_uri` → 라벨의 문서 키. 라벨 게이트·`unreadable_gold` 와 같은 규칙
    (`split_part(source_uri, ':', 2)`)."""
    parts = (source_uri or "").split(":")
    return parts[1] if len(parts) > 1 else ""


def gold_in_packet(packet, gold: list[str]) -> list[str]:
    """패킷에 실제로 들어온 gold 키들(라벨 순서 유지)."""
    present = {doc_key(s.source_uri) for s in packet.snippets}
    return [g for g in gold if g in present]


def drop_gold(packet, gold: list[str]):
    """gold 문서의 스니펫과 출처를 뺀 **새** 패킷. 원래 패킷은 건드리지 않는다.

    gold 가 여럿이면 전부 뺀다. 하나만 빼면 남은 gold 가 답을 담아 탐지 실패처럼 보인다
    (2026-08 측정의 `pb-comp-04` 가 gold 두 개였다).
    """
    drop = set(gold)
    return replace(
        packet,
        snippets=[s for s in packet.snippets if doc_key(s.source_uri) not in drop],
        provenance=[p for p in packet.provenance if doc_key(p.source_uri) not in drop],
    )


def graph_edges(packet) -> int:
    g = getattr(packet, "graph", None)
    if not g:
        return 0
    return len(getattr(g, "edges", []) or []) + len(getattr(g, "observed_edges", []) or [])


# ── 판정 한 번 ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Judged:
    status: str            # STATUSES 중 하나
    latency_ms: int
    reason: str = ""
    error_kind: str = ""   # status == "error" 일 때만: "timeout" 또는 예외 클래스 이름


async def judge_once(query: str, evidence: str, llm, *, timeout: float,
                     clock=time.perf_counter) -> Judged:
    """판정 한 번. 호출 실패는 `error`, 형식 불일치는 `unparseable` — 둘은 접히지 않는다."""
    t0 = clock()
    try:
        v = await asyncio.wait_for(sufficiency.judge_raw(query, evidence, llm), timeout)
    except asyncio.TimeoutError:
        return Judged("error", int((clock() - t0) * 1000), error_kind="timeout")
    except Exception as e:  # noqa: BLE001 — 실패는 기록 대상이지 실행을 멈출 이유가 아니다
        return Judged("error", int((clock() - t0) * 1000), error_kind=type(e).__name__)
    return Judged(v.label.value, int((clock() - t0) * 1000), reason=v.reason)


def row(qid: str, arm: str, j: Judged, *, snippets: int, dropped: int = 0, edges: int = 0) -> dict:
    return {"qid": qid, "arm": arm, "status": j.status, "error_kind": j.error_kind or None,
            "latency_ms": j.latency_ms, "reason": j.reason, "snippets": snippets,
            "dropped_snippets": dropped, "graph_edges": edges}


# ── 실행 파일 ───────────────────────────────────────────────────────────────────

def new_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)


def artifact_path(labels_path: Path, run_id: str, out_dir: Path | None = None) -> Path:
    import yaml

    try:
        pack = (yaml.safe_load(labels_path.read_text(encoding="utf-8")) or {}).get("pack") or ""
    except OSError:
        pack = ""
    prefix = pack.split("-")[0] or labels_path.stem.removesuffix("-labels")
    return (out_dir or labels_path.parent) / f"{prefix}-sufficiency-run-{run_id}.json"


def write_artifact(path: Path, payload: dict) -> None:
    """**덮어쓰지 않는다.** `x` 모드라 같은 이름이 있으면 `FileExistsError` 로 멈춘다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")


# ── 실행 ────────────────────────────────────────────────────────────────────────

async def _run(args) -> int:
    from nexus import db
    from nexus.config import load_config as _load_config
    from nexus.index.graph_extractor import (
        _build_entity_patterns, _load_gazetteer, find_entities_in_text)
    from nexus.providers.embedding import embedding_service_from_config
    from nexus.providers.llm import LLMService
    from nexus.repositories.graph import PostgresGraphRepository
    from nexus.search import reconcile
    from nexus.search.answer_pipeline import RetrievalDeps, retrieve_for_answer
    from nexus.search.evidence_packet import format_for_llm
    from nexus.search.hybrid import hybrid_search
    from nexus.search.router import determine_route

    labels = load(args.labels)
    if problems := check(labels, ManifestPack(args.manifest), require_corpus_binding=True):
        print("✗ 라벨 게이트 실패:", *problems[:4], sep="\n  ")
        return 1
    signed_tenant = (labels.get("corpus") or {}).get("tenant")
    if signed_tenant != args.tenant:
        print(f"✗ 라벨은 테넌트 {signed_tenant!r} 에 서명됐는데 측정하는 것은 {args.tenant!r} 이다")
        return 1

    svc, llm = embedding_service_from_config(), LLMService()
    search_cfg = _load_config()
    if args.model:
        llm.model = args.model
    require_free(llm, allow_paid=args.paid, what="충분성 판정기 측정")
    fingerprint = judge_fingerprint(llm, args.model or os.getenv("NEXUS_LLM_MODEL"))
    run_id = new_run_id()
    out = artifact_path(args.labels, run_id, args.out_dir)
    if out.exists():
        print(f"✗ {out} 가 이미 있다 — 실행 파일은 덮어쓰지 않는다")
        return 1

    answerable = [q for q in labels["queries"] if q.get("answerable")]
    controls = [q for q in labels["queries"] if not q.get("answerable")] if args.controls else []
    print(f"✓ 라벨 revision {labels['revision']} · 답할 수 있는 라벨 {len(answerable)}건"
          f" · 대조 {len(controls)}건")
    print(f"  판정기: {fingerprint['backend']} · 모델 설정 {fingerprint['model_setting']!r}")
    print(f"  쓸 파일: {out}\n")

    rows: list[dict] = []
    excluded: list[str] = []
    spend = Spend()
    try:
        pool = await db.get_pool()
        # 답변 표면과 **같은 앞단**이다 (엔티티 → 경로 → 검색 → 패킷, `search/answer_pipeline.py`).
        # 검색과 패킷 조립을 여기서 따로 부르면 표면과 갈린 사본이 하나 더 생긴다.
        deps = RetrievalDeps(
            hybrid_search=hybrid_search, packet_for_answer=reconcile.packet_for_answer,
            find_entities_in_text=find_entities_in_text, load_gazetteer=_load_gazetteer,
            build_entity_patterns=_build_entity_patterns, determine_route=determine_route,
            get_pool=db.get_pool, graph_repository=PostgresGraphRepository(pool),
            embedding_service=svc, config=search_cfg,
        )

        async def evidence_for(query: str):
            retrieval = await retrieve_for_answer(
                query, scope=args.tenant, clearance=args.clearance, route="auto", top_k=10,
                entity_tenant=args.tenant, deps=deps, want_packet=True)
            degraded = getattr(retrieval.search_result, "degraded", None)
            if degraded:
                raise RuntimeError(f"검색 경로가 죽었다({degraded})")
            return retrieval.packet

        for q in answerable:
            packet = await evidence_for(q["query"])
            gold = gold_in_packet(packet, q.get("gold") or [])
            if not gold:
                excluded.append(q["id"])
                print(f"   {q['id']:12s} gold 가 패킷에 없다 — 두 실험군에서 제외")
                continue
            j = await judge_once(q["query"], format_for_llm(packet), llm, timeout=args.timeout)
            spend.add(None, kind="sufficiency")
            rows.append(row(q["id"], ANSWERABLE, j, snippets=len(packet.snippets),
                            edges=graph_edges(packet)))
            neg = drop_gold(packet, gold)
            jn = await judge_once(q["query"], format_for_llm(neg), llm, timeout=args.timeout)
            spend.add(None, kind="sufficiency")
            rows.append(row(q["id"], NEGATIVE, jn, snippets=len(neg.snippets),
                            dropped=len(packet.snippets) - len(neg.snippets),
                            edges=graph_edges(neg)))
            print(f"   {q['id']:12s} answerable={j.status:12s} negative={jn.status}")

        for q in controls:
            packet = await evidence_for(q["query"])
            j = await judge_once(q["query"], format_for_llm(packet), llm, timeout=args.timeout)
            spend.add(None, kind="sufficiency")
            rows.append(row(q["id"], CONTROL, j, snippets=len(packet.snippets),
                            edges=graph_edges(packet)))
            print(f"   {q['id']:12s} control={j.status}")
    finally:
        await db.close_pool()

    write_artifact(out, {
        "artifact_version": ARTIFACT_VERSION,
        "run_id": run_id,
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "labels": Path(args.labels).name, "labels_revision": labels["revision"],
        "tenant": args.tenant, "clearance": args.clearance, "timeout_seconds": args.timeout,
        "judge": fingerprint,
        "population": {"rule": "answerable labels with at least one gold document in the packet",
                       "included": sorted({r["qid"] for r in rows if r["arm"] == ANSWERABLE}),
                       "excluded_gold_not_in_packet": excluded},
        "rows": rows,
    })
    print(f"\n기록: {out}")
    print(f"  채점: python scripts/ko_eval_sufficiency_score.py {out.name} …")
    print(f"  {spend.summary()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", type=Path, default=DEFAULT_LABELS, help="라벨 파일")
    ap.add_argument("--manifest", type=Path, default=MANIFEST, help="팩 매니페스트")
    ap.add_argument("--tenant", default="default", help="측정하는 테넌트(라벨의 서명 테넌트와 같아야 한다)")
    ap.add_argument("--clearance", default="INTERNAL", help="검색 등급")
    ap.add_argument("--model", default="", help="판정기에 쓸 모델(명시 설정으로 기록된다)")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS,
                    help="판정 한 번의 시간 제한(초). 초과는 error(timeout)로 기록")
    ap.add_argument("--controls", action="store_true",
                    help="답할 수 없는 라벨도 판정한다(따로 보고, 주 negative 표본이 아니다)")
    ap.add_argument("--paid", action="store_true", help=paid_flag_help())
    ap.add_argument("--out-dir", type=Path, default=None, help="실행 파일을 쓸 자리(기본: 라벨 옆)")
    args = ap.parse_args(argv)
    if not os.getenv("DATABASE_URL"):
        print("✗ DATABASE_URL 이 없다")
        return 1
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
