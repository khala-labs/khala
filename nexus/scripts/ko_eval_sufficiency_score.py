"""충분성 판정기 실행 파일을 채점한다 (SPEC-nexus-abstention-gate §3.3).

`ko_eval_sufficiency_run.py` 가 남긴 실행 파일을 읽기만 한다. 판정기를 부르지 않는다.

실행마다 낸다:

- **과잉 기권** — answerable 실험군에서 `insufficient` 비율. 관문은 이것만큼 답을 막는다.
  `unparseable`·`error` 는 관문이 막지 않으므로(SPEC §4.2) 따로 센다.
- **탐지** — negative 실험군에서 `insufficient` 비율. `unparseable`·`error` 는 분모에 남고
  분자에는 들지 않는다(SPEC §3.2.3). gold 를 빼도 다른 문서가 답할 수 있으니 하한이다.
  `sufficient` 로 판정된 라벨은 id 로 나열한다 — 사람이 읽을 대상이다.
- 판정 호출 지연 p50·p95 (모든 실험군).
- 비율마다 95% Wilson 구간. 40건이면 라벨 하나가 2.5% 다.

`--x --y --z` 를 주면 통과 규칙을 적용한다. 값은 SPEC §3.3 의 하한보다 **느슨할 수 없다**
(X ≤ 5%, Y ≥ 80%, Z ≤ 10초) — 느슨한 값은 거부한다. 통과는 **모든 실행**이 세 기준을 다 넘을
때이고, 실행이 3회 미만이면 판정하지 않는다.

식별 정보(백엔드·모델 설정·프롬프트·파서)나 대상 라벨이 다른 실행 파일을 섞으면 거부한다 —
다른 판정기의 숫자를 한 줄에 놓으면 변동 폭이 아니라 차이를 보게 된다.

    python scripts/ko_eval_sufficiency_score.py tests/eval/local/packb-sufficiency-run-*.json
    python scripts/ko_eval_sufficiency_score.py runs/*.json --x 0.05 --y 0.8 --z 10
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

ARTIFACT_VERSION = 1
IDENTITY_KEYS = ("backend", "model_setting", "prompt_sha256", "parser_sha256")

#: SPEC §3.3 단계 0 — 서명된 SPEC 이 정한 하한. 고른 값은 이보다 엄격할 수만 있다.
FLOOR_X = 0.05   # 과잉 기권 상한의 최댓값
FLOOR_Y = 0.80   # 탐지 하한의 최솟값
FLOOR_Z = 10.0   # 추가 p95 지연 상한의 최댓값(초)
MIN_RUNS = 3


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson 구간. n == 0 이면 (0, 1) — 모른다는 뜻이다."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, center - half), min(1.0, center + half))


def percentile(values: list[int], q: float) -> int | None:
    """가장 가까운 순위 방식의 백분위. 값이 없으면 None."""
    if not values:
        return None
    s = sorted(values)
    rank = max(1, math.ceil(q * len(s)))
    return s[rank - 1]


@dataclass
class ArmCount:
    n: int = 0
    sufficient: int = 0
    insufficient: int = 0
    unparseable: int = 0
    error: int = 0
    sufficient_qids: list[str] = field(default_factory=list)

    def add(self, r: dict) -> None:
        self.n += 1
        setattr(self, r["status"], getattr(self, r["status"]) + 1)
        if r["status"] == "sufficient":
            self.sufficient_qids.append(r["qid"])


@dataclass
class RunScore:
    run_id: str
    answerable: ArmCount
    negative: ArmCount
    control: ArmCount
    latency_p50_ms: int | None
    latency_p95_ms: int | None
    excluded: list[str]

    @property
    def over_abstention(self) -> float | None:
        a = self.answerable
        return a.insufficient / a.n if a.n else None

    @property
    def detection(self) -> float | None:
        g = self.negative
        return g.insufficient / g.n if g.n else None


class ScoreError(ValueError):
    """채점을 거부하는 이유 — 실행한 사람이 읽을 문장."""


def load_artifact(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("artifact_version") != ARTIFACT_VERSION:
        raise ScoreError(f"{path.name}: 모르는 실행 파일 버전 {data.get('artifact_version')!r}")
    return data


def identity(artifact: dict) -> tuple:
    j = artifact.get("judge") or {}
    return tuple(j.get(k) for k in IDENTITY_KEYS)


def check_comparable(artifacts: list[dict]) -> None:
    """같은 판정기·같은 대상 라벨·같은 라벨 revision 이 아니면 거부한다."""
    if not artifacts:
        raise ScoreError("실행 파일이 없다")
    first = artifacts[0]
    for a in artifacts[1:]:
        if identity(a) != identity(first):
            diff = [k for k, x, y in zip(IDENTITY_KEYS, identity(a), identity(first)) if x != y]
            raise ScoreError(f"{a['run_id']}: 판정기 식별 정보가 다르다 ({', '.join(diff)})")
        if a["population"]["included"] != first["population"]["included"]:
            raise ScoreError(f"{a['run_id']}: 대상 라벨이 다르다 — 같은 모집단의 반복이 아니다")
        if a.get("labels_revision") != first.get("labels_revision"):
            raise ScoreError(f"{a['run_id']}: 라벨 revision 이 다르다")


def score_run(artifact: dict) -> RunScore:
    arms = {"answerable": ArmCount(), "negative": ArmCount(), "control": ArmCount()}
    latencies: list[int] = []
    for r in artifact["rows"]:
        arms[r["arm"]].add(r)
        latencies.append(int(r["latency_ms"]))
    return RunScore(
        run_id=artifact["run_id"], answerable=arms["answerable"], negative=arms["negative"],
        control=arms["control"], latency_p50_ms=percentile(latencies, 0.50),
        latency_p95_ms=percentile(latencies, 0.95),
        excluded=list(artifact["population"].get("excluded_gold_not_in_packet") or []),
    )


def check_floors(x: float, y: float, z: float) -> None:
    """SPEC §3.3 단계 0. 하한보다 느슨한 기준은 기준이 아니다."""
    bad = []
    if x > FLOOR_X:
        bad.append(f"X={x} 가 상한 {FLOOR_X} 보다 느슨하다")
    if y < FLOOR_Y:
        bad.append(f"Y={y} 가 하한 {FLOOR_Y} 보다 느슨하다")
    if z > FLOOR_Z:
        bad.append(f"Z={z}s 가 상한 {FLOOR_Z}s 보다 느슨하다")
    if bad:
        raise ScoreError("; ".join(bad))


def run_passes(s: RunScore, x: float, y: float, z: float) -> list[str]:
    """이 실행이 못 넘은 기준들. 비어 있으면 통과."""
    misses = []
    if s.over_abstention is None or s.over_abstention > x:
        misses.append("X")
    if s.detection is None or s.detection < y:
        misses.append("Y")
    if s.latency_p95_ms is None or s.latency_p95_ms > z * 1000:
        misses.append("Z")
    return misses


def verdict(scores: list[RunScore], x: float, y: float, z: float) -> str:
    """`pass` · `fail` · `undecided`(실행 3회 미만)."""
    if any(run_passes(s, x, y, z) for s in scores):
        return "fail"
    if len(scores) < MIN_RUNS:
        return "undecided"
    return "pass"


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{v * 100:.1f}%"


def _ci(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"[{lo * 100:.1f}–{hi * 100:.1f}%]"


def summary(scores: list[RunScore]) -> dict:
    """기준 파일에 옮겨 적을 수 있는 숫자만 — 라벨 본문은 없다."""
    def spread(vals):
        vals = [v for v in vals if v is not None]
        return {"min": min(vals), "max": max(vals)} if vals else None

    return {
        "runs": [s.run_id for s in scores],
        "over_abstention": spread([s.over_abstention for s in scores]),
        "detection": spread([s.detection for s in scores]),
        "latency_p95_ms": spread([s.latency_p95_ms for s in scores]),
        "per_run": [{
            "run_id": s.run_id,
            "answerable": {k: getattr(s.answerable, k)
                           for k in ("n", "sufficient", "insufficient", "unparseable", "error")},
            "negative": {k: getattr(s.negative, k)
                         for k in ("n", "sufficient", "insufficient", "unparseable", "error")},
            "control": {k: getattr(s.control, k)
                        for k in ("n", "sufficient", "insufficient", "unparseable", "error")},
            "latency_p50_ms": s.latency_p50_ms, "latency_p95_ms": s.latency_p95_ms,
            "excluded": len(s.excluded),
        } for s in scores],
    }


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path, help="실행 파일들")
    ap.add_argument("--x", type=float, help="과잉 기권 상한 (예: 0.05)")
    ap.add_argument("--y", type=float, help="탐지 하한 (예: 0.80)")
    ap.add_argument("--z", type=float, help="판정 지연 p95 상한, 초 (예: 10)")
    ap.add_argument("--json", type=Path, help="숫자 요약을 이 파일에 쓴다(라벨 본문 없음)")
    args = ap.parse_args(argv)

    try:
        artifacts = [load_artifact(p) for p in args.runs]
        check_comparable(artifacts)
        criteria = (args.x, args.y, args.z)
        if any(v is not None for v in criteria):
            if any(v is None for v in criteria):
                raise ScoreError("--x --y --z 는 셋 다 주거나 셋 다 비운다")
            check_floors(*criteria)
    except ScoreError as e:
        print(f"✗ {e}")
        return 1

    j = artifacts[0]["judge"]
    print(f"판정기: {j['backend']} · 모델 설정 {j['model_setting']!r} · "
          f"프롬프트 {j['prompt_sha256'][:12]} · 파서 {j['parser_sha256'][:12]}")
    print(f"라벨 revision {artifacts[0]['labels_revision']} · 실행 {len(artifacts)}회\n")

    scores = [score_run(a) for a in artifacts]
    for s in scores:
        a, g = s.answerable, s.negative
        print(f"{s.run_id}")
        print(f"  과잉 기권 {a.insufficient}/{a.n} = {_pct(s.over_abstention)} {_ci(a.insufficient, a.n)}"
              f"   (unparseable {a.unparseable} · error {a.error})")
        print(f"  탐지      {g.insufficient}/{g.n} = {_pct(s.detection)} {_ci(g.insufficient, g.n)}"
              f"   (unparseable {g.unparseable} · error {g.error})")
        if g.sufficient_qids:
            print(f"    gold 를 뺐는데 sufficient — 읽을 대상: {', '.join(g.sufficient_qids)}")
        if s.control.n:
            c = s.control
            print(f"  대조      insufficient {c.insufficient}/{c.n}"
                  f"   (unparseable {c.unparseable} · error {c.error})")
        print(f"  지연      p50 {s.latency_p50_ms} ms · p95 {s.latency_p95_ms} ms"
              f"   · 제외(gold 가 패킷에 없음) {len(s.excluded)}")
        if args.x is not None:
            misses = run_passes(s, args.x, args.y, args.z)
            print(f"  기준      {'통과' if not misses else '미달: ' + ', '.join(misses)}")
        print()

    if args.x is not None:
        v = verdict(scores, args.x, args.y, args.z)
        print({"pass": f"✓ 통과 — {len(scores)}회 모두 X={args.x}, Y={args.y}, Z={args.z}s 를 넘었다",
               "fail": "✗ 미달 — 기준을 못 넘은 실행이 있다",
               "undecided": f"… 판정 안 함 — 실행이 {len(scores)}회다(최소 {MIN_RUNS}회)"}[v])
        print("  이 숫자는 이 라벨 묶음에서의 반복 측정이다. 일반화된 비율이 아니다(SPEC §3.3).")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary(scores), ensure_ascii=False, indent=1) + "\n",
                             encoding="utf-8")
        print(f"\n요약: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
