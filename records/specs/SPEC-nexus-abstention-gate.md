---
id: SPEC-nexus-abstention-gate
type: spec
title: Abstain before generating when the evidence does not answer the question — measure
  the judge first, then let the answer path branch on it
status: draft
linked_adrs:
- ADR-0002
- ADR-0012
tags:
- nexus
- llm
- grounding
- abstention
---

## 0. Gate declaration

This SPEC names its consumer before it adds any field, as [[ADR-0012]] requires of any successor
that measures evidence sufficiency on the live path ("a new SPEC with a named consumer first and
a column second"). The consumer is the answer path itself: one shared function decides whether
the answering LLM is called at all. Nothing in this SPEC records a verdict that no code reads.

The SPEC has two units. **Unit 2 does not open until Unit 1 passes criteria that are written down
before the confirmation run.** Approval of this SPEC approves the plan for both units; it does not
approve turning the gate on (approved is a signed record, not a statement that something is
implemented or enabled — `records/specs/README.md`).

## 1. The problem

- `abstention()` in `nexus/nexus/llm/answer.py` abstains only when the evidence packet is empty.
  Both HTTP answer paths decide through it.
- The keyword leg returns a full window for almost any query, so the packet is almost never empty.
  `records/governance/open-items.yaml` item `abstention-never-fires` measured **0 of 5** system
  abstentions on the unanswerable Pack B labels (2026-08-07).
- This repository set and removed score thresholds three times: the score distributions of
  answered and should-abstain queries overlapped (`nexus/nexus/llm/sufficiency.py` module docstring,
  `nexus/nexus/search/confidence.py`). A score threshold is not proposed here.
- The answering LLM is instructed to say when it cannot find the information, and on the
  unanswerable controls it did so in text (`SPEC-nexus-answer-quality-ruler`, 5 of 5 refused,
  2026-08-11). That refusal is narration. No code reads it, so the API reports `abstained=false`
  for an answer whose text declines, and `search_log.no_answer` counts zero for it
  (`open-items.yaml`, `abstention-never-fires`).
- What this SPEC therefore buys first is a **machine-readable abstention decided before
  generation**. It is not primarily a hallucination filter, and an over-abstention is a pure loss:
  a correct answer is withheld.

## 2. Decision

- Use the existing judge `nexus/nexus/llm/sufficiency.py` (query + evidence only, never the answer;
  output `sufficient` / `insufficient` / `unparseable`) as the sole gate signal.
- Rejected for this SPEC:
  - A deterministic gate that checks whether the entities named in the question appear in the
    evidence. The known failures are "topic present, fact absent", where the named entities do
    appear, and a vocabulary mismatch has already made a present answer look absent
    (`confidence.py` docstring).
  - A combination of a deterministic first check and the LLM judge. It does not reduce judge calls
    for the cases that matter. Revisit after Unit 1 numbers exist.
  - Any retrieval-score threshold (§1).
- `open-items.yaml` asks for a "deterministic" insufficient-evidence verdict. The LLM judge is not
  deterministic. This SPEC relaxes that word explicitly: the verdict is a value the code branches
  on, produced by a named judge model, and its run-to-run spread is measured (§3.2) instead of
  assumed to be zero.

## 3. Unit 1 — measure the judge offline

### 3.1 What is already known (and its limits)

From `SPEC-nexus-sufficiency-signal` §§ on measurement (one surviving run; earlier runs were
overwritten by a fixed output filename):

- 45 Pack B labels (40 answerable, 5 unanswerable): accuracy 43/45; answerable judged
  `insufficient` 2/40 (`pb-loan-08`, `pb-space-01`); unanswerable judged `insufficient` 5/5.
- Negative arm (gold document dropped from the evidence): 31/38 flipped to `insufficient`
  (81.6%), on a population narrowed after the baseline was seen.
- With n=5 unanswerable labels, a coin-flipping judge clears 4/5 about 19% of the time.

These numbers set the ceiling the criteria in §3.3 must respect. They are not re-used as the
result of this SPEC.

### 3.2 Harness changes (`nexus/scripts/ko_eval_answer_run.py --sufficiency` and its measurement script)

1. **Per-run artifacts.** Every run writes to its own file named by run id; no run overwrites
   another. At least three runs per configuration.
2. **Both arms.** The answerable population (does the judge withhold answers it should give?) and
   a negative population built by dropping the gold document from the evidence of answerable
   labels (does the judge catch absence?). The 5 hand-written unanswerable labels are reported
   separately and are not the main negative sample.
3. **Separate failure kinds.** `unparseable` (the judge answered in the wrong shape) and `error`
   (the call failed or timed out) are counted apart from verdicts, and both count against
   detection in the negative arm. The request path uses `judge_raw`, which does not fold call
   failures into `unparseable`.
4. **Same packet as production.** The judge receives the evidence exactly as the answer path
   serialises it (`format_for_llm`).
5. **Record the judge model** (backend and model name) and the prompt version in every artifact.
6. **Latency.** p50 and p95 of the judge call, and the added time to first answer text on the
   streaming path.
7. Keyless bridge only. A paid-backend measurement needs the owner's permission first.

### 3.3 Criteria and the order of runs

1. **Baseline runs** (three) on the current judge. Report both error rates with their run-to-run
   spread.
2. **Write the criteria into a tracked file before the confirmation run**, in this repository, so
   the write order is in git history. Pack B artifacts are gitignored (partner corpus), so the
   criteria file must carry counts and rates only, not label text. The criteria are two:
   - over-abstention on the answerable arm at most *X*;
   - detection on the negative arm at least *Y*.
3. **Reachability check before freezing.** The file states, for the chosen *X* and *Y*, that the
   baseline values (and §3.1's) lie on the passing side or explains why the judge is expected to
   move. A line no current or proposed judge can reach is not a criterion. For example, "no
   over-abstention at all" or "90% detection" sits outside the known values above.
4. **Confirmation runs** (three), on labels not used to set *X* and *Y* where the label pool
   allows. Unit 1 passes if every confirmation run meets both criteria.
5. If Unit 1 fails, the SPEC records the numbers and Unit 2 stays closed. Judge improvements are a
   new change measured the same way.

## 4. Unit 2 — the gate (only after Unit 1 passes)

### 4.1 Where it sits

- After the final evidence packet is assembled and before any answer text is produced, on both
  `/search/answer` and `/search/answer/stream`. On the streaming path this is before the branch
  at `api.py` that starts `llm_svc.stream`. Once an `answer_delta` has been sent it cannot be
  withdrawn, so the gate must precede the first one.
- `abstention()` takes the verdict as an argument, so both paths still decide through one
  function. Evidence-only requests (`evidence_only`) are not judged.

### 4.2 Behaviour

| Verdict | Answering LLM called | `abstained` | `abstain_reason` | `sufficiency_status` |
|---|---|---|---|---|
| packet empty (unchanged) | no | true | `no_evidence` | `off` |
| `insufficient` | **no** | true | `insufficient_evidence` | `judged` |
| `sufficient` | yes | false | `""` | `judged` |
| `unparseable` | yes | false | `""` | `unparseable` |
| call failed or timed out | yes | false | `""` | `error` |
| gate disabled | yes | false | `""` | `off` |

- An unknown verdict is never treated as `insufficient` (no silent mass abstention when the judge
  breaks) and never reported as `judged` (no silent pass).
- On abstention the response carries the fixed notice already used for the empty-packet case, the
  evidence that was retrieved, an empty citation list, and no number or citation verification
  (`None`, not "passed").
- Streaming order on abstention: `evidence` → optional `graph` → one `answer_delta` with the fixed
  notice → `done` with the same fields as the non-streaming response.
- `weak_evidence` is unchanged and independent: it does not block an answer.

### 4.3 Switches and the model binding

- Off by default. Enabled by an environment variable (name fixed in implementation) and limited
  to a named list of principals or tenants.
- The gate is bound to the judge model that passed Unit 1. If the configured judge model differs
  from the one recorded in the passing criteria file, the gate stays off and the status reports
  `off`. Changing the judge model means re-running Unit 1.
- A judge timeout bounds the added latency. On timeout the status is `error` and generation
  proceeds.
- Rollback is the switch. No migration is added by this SPEC.

### 4.4 Verification for Unit 2

- Contract tests on both paths for every row of §4.2, including that the answering LLM is not
  called on `insufficient` and that no `answer_delta` precedes the gate.
- One end-to-end run on the keyless bridge with the gate on for a test principal, reporting
  abstention counts on the answerable and negative arms against Unit 1's numbers.

## 5. Consumers

1. **The generation decision** (`abstention()`), which branches on the verdict. This is the
   consumer [[ADR-0012]] asks for.
2. **The API's existing `abstained` / `abstain_reason` fields**, already exposed on both paths
   and read by the web client.
3. **Not in this SPEC:** the numerator of `v_image_gap_signal` (migration 011), which waits on a
   machine-readable "answer not available" signal for `SPEC-nexus-screenshot-text-extraction` and
   ADR-0010. `search_log.no_answer` today means "zero search hits", so feeding abstentions into that
   view needs its own approved definition of numerator and denominator. This SPEC only makes such
   a definition possible.

## 6. Out of scope

- Retrieval changes, the cross-lingual channel (`OPEN.md` A95), score thresholds.
- Buffering streamed text until citations are validated (a separate change to the streaming path).
- New `search_log` columns or views. If the image-gap follow-up needs a column, that SPEC adds it.
- Any change to the answering prompt.

## 7. Open questions for the owner

1. The values of *X* and *Y* after the baseline runs (§3.3).
2. Whether Unit 1 may also run once on a paid backend, if the production answer backend differs
   from the keyless bridge (`SPEC-nexus-per-principal-answer-backend`).
3. Which principals or tenants the gate is first enabled for after Unit 1 passes.
