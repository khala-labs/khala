"""판정기 오프라인 측정 하니스 (SPEC-nexus-abstention-gate §3.2 · §3.3).

DB 와 LLM 없이 도는 부분만 시험한다: 패킷 조작, 판정 한 번의 분류, 실행 파일 쓰기, 채점.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nexus.llm import sufficiency  # noqa: E402
from nexus.search.evidence_packet import EvidencePacket, Provenance  # noqa: E402
from scripts import ko_eval_sufficiency_run as run  # noqa: E402
from scripts import ko_eval_sufficiency_score as score  # noqa: E402


def _snip(key: str):
    return SimpleNamespace(source_uri=f"notion:{key}", doc_title=key)


def _packet(*keys: str) -> EvidencePacket:
    return EvidencePacket(snippets=[_snip(k) for k in keys],
                          provenance=[Provenance(doc_rid=k, source_uri=f"notion:{k}") for k in keys])


class _LLM:
    provider = "claude-code"
    model = "m"

    def __init__(self, reply=None, exc=None, delay=0.0):
        self.reply, self.exc, self.delay = reply, exc, delay

    async def generate(self, system, user):
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.exc:
            raise self.exc
        return self.reply


# ── 패킷 조작 ───────────────────────────────────────────────────────────────────

def test_doc_key_follows_the_label_rule():
    assert run.doc_key("notion:abc") == "abc"
    assert run.doc_key("git:path/x.md:extra") == "path/x.md"
    assert run.doc_key("bare") == ""


def test_drop_gold_removes_every_gold_document_and_leaves_the_original_alone():
    p = _packet("g1", "x", "g2", "y")
    neg = run.drop_gold(p, ["g1", "g2"])
    assert [run.doc_key(s.source_uri) for s in neg.snippets] == ["x", "y"]
    assert [run.doc_key(v.source_uri) for v in neg.provenance] == ["x", "y"]
    assert len(p.snippets) == 4


def test_gold_in_packet_keeps_only_what_reached_the_evidence():
    assert run.gold_in_packet(_packet("a", "g2"), ["g1", "g2"]) == ["g2"]
    assert run.gold_in_packet(_packet("a"), ["g1"]) == []


# ── 판정기 식별 정보 ─────────────────────────────────────────────────────────────

def test_fingerprint_has_four_parts_and_keeps_an_unset_model_unset():
    fp = run.judge_fingerprint(_LLM(), None)
    assert fp["backend"] == "claude-code"
    assert fp["model_setting"] is None
    assert len(fp["prompt_sha256"]) == 64 and len(fp["parser_sha256"]) == 64


def test_prompt_fingerprint_moves_with_the_system_prompt(monkeypatch):
    before = run.prompt_sha256()
    monkeypatch.setattr(sufficiency, "SYSTEM", sufficiency.SYSTEM + " ")
    assert run.prompt_sha256() != before


# ── 판정 한 번 ──────────────────────────────────────────────────────────────────

def _judge(llm, timeout=5.0):
    return asyncio.run(run.judge_once("q", "e", llm, timeout=timeout))


def test_a_well_formed_reply_is_a_verdict():
    j = _judge(_LLM("VERDICT: insufficient\nREASON: 없다"))
    assert (j.status, j.reason, j.error_kind) == ("insufficient", "없다", "")


def test_a_malformed_reply_is_unparseable_not_an_error():
    assert _judge(_LLM("충분해 보인다")).status == "unparseable"


def test_a_failed_call_is_an_error_not_unparseable():
    j = _judge(_LLM(exc=ConnectionError("down")))
    assert (j.status, j.error_kind) == ("error", "ConnectionError")


def test_a_timeout_is_an_error_of_kind_timeout():
    j = _judge(_LLM("VERDICT: sufficient", delay=0.5), timeout=0.05)
    assert (j.status, j.error_kind) == ("error", "timeout")


# ── 실행 파일 ───────────────────────────────────────────────────────────────────

def test_an_artifact_is_never_overwritten(tmp_path):
    p = tmp_path / "packb-sufficiency-run-x.json"
    run.write_artifact(p, {"a": 1})
    with pytest.raises(FileExistsError):
        run.write_artifact(p, {"a": 2})
    assert json.loads(p.read_text(encoding="utf-8")) == {"a": 1}


def test_run_ids_differ_within_the_same_second():
    assert run.new_run_id() != run.new_run_id()


# ── 채점 ────────────────────────────────────────────────────────────────────────

_JUDGE = {"backend": "claude-code", "model_setting": "m", "model_effective": "m",
          "prompt_sha256": "p" * 64, "parser_sha256": "q" * 64}


def _artifact(run_id="r1", ans=(), neg=(), ctl=(), judge=None, included=None, latency=100):
    rows = ([{"qid": q, "arm": "answerable", "status": s, "latency_ms": latency} for q, s in ans]
            + [{"qid": q, "arm": "negative", "status": s, "latency_ms": latency} for q, s in neg]
            + [{"qid": q, "arm": "control", "status": s, "latency_ms": latency} for q, s in ctl])
    return {"artifact_version": 1, "run_id": run_id, "labels_revision": 3,
            "judge": judge or _JUDGE,
            "population": {"included": included or sorted({q for q, _ in ans}),
                           "excluded_gold_not_in_packet": []},
            "rows": rows}


def test_wilson_matches_the_interval_quoted_in_the_spec():
    lo, hi = score.wilson(2, 40)
    assert round(lo, 3) == 0.014 and round(hi, 3) == 0.165


def test_percentile_is_nearest_rank():
    assert score.percentile([5, 1, 3, 2, 4], 0.5) == 3
    assert score.percentile(list(range(1, 21)), 0.95) == 19
    assert score.percentile([], 0.95) is None


def test_failures_count_against_detection_but_not_as_over_abstention():
    a = _artifact(ans=[("a", "sufficient"), ("b", "unparseable"), ("c", "error"), ("d", "insufficient")],
                  neg=[("a", "insufficient"), ("b", "unparseable"), ("c", "error"), ("d", "sufficient")])
    s = score.score_run(a)
    assert s.over_abstention == 0.25          # insufficient 만 답을 막는다
    assert s.detection == 0.25                # unparseable·error 는 분모에만 있다
    assert s.negative.sufficient_qids == ["d"]


def test_runs_of_different_judges_are_not_scored_together():
    other = dict(_JUDGE, prompt_sha256="z" * 64)
    with pytest.raises(score.ScoreError, match="prompt_sha256"):
        score.check_comparable([_artifact(), _artifact("r2", judge=other)])


def test_runs_of_different_populations_are_not_scored_together():
    with pytest.raises(score.ScoreError, match="대상 라벨"):
        score.check_comparable([_artifact(included=["a"]), _artifact("r2", included=["a", "b"])])


@pytest.mark.parametrize("x,y,z", [(0.06, 0.8, 10), (0.05, 0.79, 10), (0.05, 0.8, 11)])
def test_criteria_looser_than_the_floors_are_refused(x, y, z):
    with pytest.raises(score.ScoreError):
        score.check_floors(x, y, z)


def test_stricter_criteria_are_accepted():
    score.check_floors(0.025, 0.9, 5)


def _good(run_id):
    ans = [(f"q{i}", "sufficient") for i in range(19)] + [("q19", "insufficient")]
    neg = [(f"q{i}", "insufficient") for i in range(17)] + [(f"q{i}", "sufficient") for i in (17, 18, 19)]
    return score.score_run(_artifact(run_id, ans=ans, neg=neg))


def test_three_passing_runs_pass_and_fewer_are_undecided():
    runs = [_good("r1"), _good("r2"), _good("r3")]
    assert score.verdict(runs, 0.05, 0.8, 10) == "pass"
    assert score.verdict(runs[:2], 0.05, 0.8, 10) == "undecided"


def test_one_missing_run_fails_the_unit():
    slow = score.score_run(_artifact("r3", ans=[("q0", "sufficient")], neg=[("q0", "insufficient")],
                                     latency=20_000))
    assert score.run_passes(slow, 0.05, 0.8, 10) == ["Z"]
    assert score.verdict([_good("r1"), _good("r2"), slow], 0.05, 0.8, 10) == "fail"


def test_cli_end_to_end_on_written_artifacts(tmp_path, capsys):
    paths = []
    for rid in ("r1", "r2", "r3"):
        ans = [(f"q{i}", "sufficient") for i in range(20)]
        neg = [(f"q{i}", "insufficient") for i in range(20)]
        p = tmp_path / f"{rid}.json"
        p.write_text(json.dumps(_artifact(rid, ans=ans, neg=neg)), encoding="utf-8")
        paths.append(str(p))
    out = tmp_path / "summary.json"
    assert score.main([*paths, "--x", "0.05", "--y", "0.8", "--z", "10", "--json", str(out)]) == 0
    assert "통과" in capsys.readouterr().out
    s = json.loads(out.read_text(encoding="utf-8"))
    assert s["over_abstention"] == {"min": 0.0, "max": 0.0}
    assert "q0" not in out.read_text(encoding="utf-8")   # 요약에는 라벨 id 도 없다


def test_cli_refuses_looser_criteria(tmp_path):
    p = tmp_path / "r1.json"
    p.write_text(json.dumps(_artifact(ans=[("a", "sufficient")])), encoding="utf-8")
    assert score.main([str(p), "--x", "0.1", "--y", "0.8", "--z", "10"]) == 1
