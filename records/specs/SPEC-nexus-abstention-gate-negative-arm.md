---
id: SPEC-nexus-abstention-gate-negative-arm
type: spec
title: Measure the sufficiency judge on a negative arm that no longer holds the answer
  — re-baseline, then revise the judge and confirm it on a second pack
status: approved
linked_adrs:
- ADR-0002
- ADR-0012
tags:
- nexus
- llm
- grounding
- abstention
approved_by: LivingLikeKrillin
reviewed_at: '2026-11-28T01:24:04Z'
content_hash: sha256:ada6196332c129c77484c1c86b7791abe45489613c374e303262c879ae8f37dd
---

## 0. Relation to SPEC-nexus-abstention-gate

- This SPEC changes how Unit 1 of [[SPEC-nexus-abstention-gate]] builds its negative arm, and sets the order in which the sufficiency judge may be revised.
- It adds one condition to that SPEC's pass rule (§3.3 step 5): the floors must also hold on a second pack (§2.4). The added condition only makes passing harder. It is recorded here, not in the signed body.
- It does not change that SPEC's floors (X ≤ 5%, Y ≥ 80%, Z ≤ 10 s), the criteria-file step, or Unit 2. Unit 2 stays closed until Unit 1 passes.
- Any change to the gate SPEC's §4.2 table (candidate A in §2.3 would need one) is out of scope here and needs its own successor SPEC.
- The gate SPEC's body is signed. On approval of this SPEC, the sentence "Detection on this arm is therefore a lower bound." in its §3.2 is retracted under CONVENTIONS.md §Retracting a claim in a signed document (entry in records/specs/retractions.yaml, retracted_by this SPEC). Its body is not edited.

## 1. What the baseline showed

### 1.1 The baseline

The baseline run under [[SPEC-nexus-abstention-gate]] §3.3 step 1 was executed on 2026-11-28 using the keyless bridge (no spend).
The recorder was `nexus/scripts/ko_eval_sufficiency_run.py` and the scorer was `nexus/scripts/ko_eval_sufficiency_score.py`.
Labels came from `packb-labels.yaml` revision 9, tenant `default`, clearance INTERNAL, with a timeout of 120 s.
The judge identity in all three runs was identical: backend `claude-code`, model setting `claude-sonnet-5`, prompt SHA-256 `1c940f44f693…`, and parser SHA-256 `cc5d64df07bd…`.
The population was 39 answerable labels; 1 answerable label was excluded because its gold document did not reach the packet.
Unanswerable controls were not run (`--controls` not used).
Each run executed 78 judge calls in about 9 minutes.
Across all three runs, `unparseable` was 0 and `error` was 0.

| Run | Over-abstention (X) | Detection (Y) | Latency p50 | Latency p95 |
| :--- | :--- | :--- | :--- | :--- |
| run 1 | 8/39 = 20.5% [10.8–35.5%] | 28/39 = 71.8% [56.2–83.5%] | 6,415 ms | 9,775 ms |
| run 2 | 4/39 = 10.3% [4.1–23.6%] | 30/39 = 76.9% [61.7–87.4%] | 6,554 ms | 8,644 ms |
| run 3 | 8/39 = 20.5% [10.8–35.5%] | 30/39 = 76.9% [61.7–87.4%] | 6,416 ms | 10,598 ms |

The floors from §3.3 step 0 are X (max over-abstention) ≤ 5%, Y (min detection) ≥ 80%, and Z (max added p95) ≤ 10 s.
Every run misses X and Y; run 3 also misses Z.
Under §3.3 step 3 reachability, no allowed X lies on the passing side of the baseline (10.3–20.5% vs ≤ 5%), and no allowed Y does (71.8–76.9% vs ≥ 80%).
No criteria file was written and Unit 2 stays closed (§3.3 step 6).
X is measured on the answerable arm. §2.1 below does not change that arm, so no change to the negative arm can make X reachable.

### 1.2 The negative arm still holds the answer

Packet contents were checked after the runs with no LLM through the `retrieve_for_answer` path, dropping gold documents as the recorder does.
Presence of `must_contain` groups was tested against `format_for_llm(packet)` text using `facts_present` from `nexus/scripts/ko_eval_answer_quality.py`.
Full (answerable) packets contain every `must_contain` group for 39/39 labels.
On the negative packets, 16/39 still contain every `must_contain` group after gold documents are dropped; 23/39 do not.
A judge that is right on those 16 (calls them sufficient) scores at most 23/39 = 59.0% detection on this arm, below the 80% floor.
The floor on this arm is reachable only by a judge that calls answer-bearing packets insufficient.
The current judge called 8 of those 16 insufficient in all three runs.
Of the 11 labels the judge called sufficient in the negative arm in at least one run, 8 are among the 16.
On the 23 negative packets without the facts, insufficient verdicts were 20/23 (87.0%), 21/23 (91.3%), and 21/23 (91.3%).
This subset was chosen after the runs; it is only a diagnostic, not a result.
Misses on this subset were 2 labels in all three runs, and 1 label in one run.
Checking `must_contain` presence is string matching. It misses paraphrases and can match a string used in another context.
On this arm Y rewards a judge for calling answer-bearing packets insufficient, while X penalises the same behaviour on the answerable arm; the two criteria pull against each other on one failure, so tuning the judge against this arm would optimise the wrong thing.

### 1.3 Why the judge over-abstains

Across the three runs, there were 20 `insufficient` verdicts on the answerable arm (12 distinct labels; 2 labels in all three runs).
These reasons were classified by one reader from the judge's REASON line, with no review by anyone else:

| Reason category | Verdict count |
| :--- | :--- |
| Evidence documents contradict each other (older and newer version of a policy) | 6 |
| Asks for detail the question does not ask for (exact implementation steps, numbers, direct comparison) | 9 |
| Reads question as asking for this project's actual decision while evidence gives example value | 3 |
| The question is underspecified (which field, what "visible" means) | 2 |

Stability across the three runs:
- Answerable-arm verdict was identical in all three runs for 29/39 labels.
- Negative-arm verdict was identical in all three runs for 36/39 labels.

### 1.4 Latency leaves no room for more calls

Bridge concurrency is 3 (`NEXUS_LLM_BRIDGE_CONCURRENCY=3`).
Baseline p95 latencies were 9,775 ms in run 1, 8,644 ms in run 2, and 10,598 ms in run 3.
With p95 already at 8.6–10.6 s against a 10 s Z floor, latency leaves no room for more calls.

## 2. Decision

### 2.1 A negative arm without the answer

- Rule, fixed before any run under this SPEC: for each answerable label whose gold document reaches the packet, drop the gold documents; then drop every remaining document in whose text any of the label's must_contain groups is present (`facts_present` from `nexus/scripts/ko_eval_answer_quality.py`, the scorer the repository already uses). The label enters the negative arm only if, after that, no must_contain group is present in the serialised packet. Otherwise it is excluded and listed by id with the reason.
- The rule depends only on the label and the packet, never on a verdict.
- Disclosure: this rule was chosen after the 2026-11-28 baseline was seen. It is not tuned to verdicts, but the owner should weigh that order.
- String matching still misses paraphrases. Every negative-arm label judged sufficient is still listed by id and stays in the denominator.
- If no document remains, the label is excluded with that reason. An empty packet is not judged; the gate SPEC's empty-packet path already abstains on it. Excluding these removes cases that are easy to call insufficient, so it lowers Y rather than raising it.
- Each negative row records how many documents were dropped for gold, how many for `must_contain`, and how many remain.
- **Common strings.** A `must_contain` group made of common words can strip most on-topic documents and leave an easy, off-topic packet, which would raise Y for the wrong reason. Every label for which the rule dropped more than half of the non-gold documents is listed by id, and Y is reported with and without those labels.
- **Minimum size.** The arm counts only if at least 30 labels remain. Below that the run reports the arm as invalid, no Y is computed from it, and the owner decides how to proceed. At 30, one label is 3.3% of the arm.
- Every report gives the excluded count for each exclusion reason.
- The listed `sufficient` labels are disclosed, not adjudicated. No one is assigned to decide whether each is a paraphrase the rule missed or a judge error, and Y is reported as computed.
- The answerable arm is unchanged.

### 2.2 Re-baseline before any judge change

- Three runs of the current judge (the identity in §1.1) on the new arm.
- The answerable arm is unchanged, so the re-baseline cannot move X except through run-to-run spread, and the baseline's X (10.3–20.5%) is two to four times the floor. A judge revision is therefore expected. This SPEC does not present it as open.
- The re-baseline is still needed. It gives the current judge's Y on the new arm, which is the reference any revision is compared against.
- If the re-baseline nevertheless makes all floors reachable, [[SPEC-nexus-abstention-gate]] §3.3 steps 2–5 apply, with §2.4's second pack.

### 2.3 Judge revision, if needed — candidates

Three candidates. Each produces a new judge identity (a prompt or parser hash change) and is measured from step 1. The identity is computed by the recorder (`judge_fingerprint` in `nexus/scripts/ko_eval_sufficiency_run.py`); the gate SPEC's §4.3 pins it as a constant only when Unit 2 is built. Revising `nexus/nexus/llm/sufficiency.py` also changes the judge that `ko_eval_answer_run.py --sufficiency` uses, so its grids before and after the change are not comparable. The earlier prompt stays recoverable from git history.
- Candidate A — a third verdict for conflicting evidence: `sufficient | conflicting | insufficient`; the gate withholds generation only on `insufficient`; `conflicting` proceeds to generation as today. Addresses the 6 conflict verdicts. Changes the parser. It also needs a new row in the gate SPEC's §4.2 table, which is a change to a signed body and needs its own successor SPEC (§0).
- Candidate B — requirement first: the judge lists the fact(s) the question asks for, one line each, and marks each `found` (with the evidence number), `absent` or `conflicting`. Code derives the verdict from the marks: any `absent` → insufficient; otherwise sufficient. Addresses the 9 "detail not asked for" and the 3 "example vs decision" verdicts by making the judge state what the question requires before judging; also covers A's conflict case.
  - The marks are still LLM judgments; code only combines them. This is the same kind of decision as today, where code reads a verdict line, at a finer grain. It does not make the judge deterministic, and the [[ADR-0002]] reading in the gate SPEC's §2 is unchanged by it, not strengthened.
  - An output that lists no required fact is `unparseable`, never `sufficient`. A mark outside the three values is `unparseable`.
  - One call; the output is longer, so latency must be measured against Z.
- Candidate C — three votes, withhold only on unanimous insufficient. Rejected for now. Issued in parallel, the added time is the slowest of three calls, whose p95 is above a single call's p95, and that is already 8.6–10.6 s against a 10 s Z. Each request would also hold three of the bridge's three slots. The measured p95 comes from sequential offline runs and may differ from the live path.
- Recommendation for the owner: B. By §1.3's classification it addresses 18 of the 20 over-abstention verdicts (the 9 detail, 3 example and 6 conflict verdicts), A addresses 6, and C does not address any reason class. That classification is one reader's. Before the owner chooses, a second reader that has not seen the first classification classifies the same 20 reasons, and the recommendation stands only if the two agree on the order of the classes.

### 2.4 Confirm on a pack the revision was not designed on

- Any revision is designed from Pack B's failure classes. Confirming it on Pack B alone would grade it on the material it was fitted to.
- **Pack A is not untouched.** Six tracked artifacts in `nexus/tests/eval/ko/` from 2026-08-12 and 2026-08-13 (`packa-answer-quality-r3`, `-r6-citation-fix`, `-r7-clearance`, `-rev3-r1`, `-rev3-r2`, `-rev3-r3`) hold an earlier judge's verdict on each of the 40 answerable labels, with 2 to 4 `insufficient` per artifact. That judge's identity was not recorded. The author of this SPEC has read those counts and no per-label verdict.
- Pack A (`nexus/tests/eval/ko/answer-labels.yaml`, revision 4, tenant `ko_eval_packa`: 40 answerable labels with gold documents and `must_contain`, 5 unanswerable) is therefore a pack the revision was not designed on, not an untouched one. Whoever designs the revision does not open the per-label verdicts in those six artifacts or in any new Pack A run before the revised judge's identity is committed.
- **Enforcement.** The recorder writes the commit of `nexus/nexus/llm/sufficiency.py` into every artifact and refuses a Pack A run while that file has uncommitted changes. Git history then shows that the identity was committed before the first Pack A artifact of that identity.
- **Population on Pack A.** The same §2.1 rule and minimum size apply. The 5 unanswerable labels run as controls and are reported, not used for passing.
- **A failure on Pack A ends the attempt.** A further revision would have seen Pack A, so it needs a confirmation set the owner chooses. At most two revisions are tried on Pack B before the owner reviews the approach.
- Pass requires the gate SPEC's floors on both packs: Pack B (the gate SPEC's population) and Pack A, three runs each, every run passing. Both report Wilson intervals.
- Before any Pack A run, the recorder's document-key rule is checked against Pack A source URIs (`split_part(source_uri, ':', 2)`; not yet checked).

## 3. Work items

1. Recorder: implement §2.1 (exclusion reasons, drop and remaining counts, the common-string list, the minimum-size check; tests with no DB or LLM).
2. Recorder: write the judge file's commit and refuse runs with uncommitted judge changes (§2.4); confirm Pack A runs (labels `nexus/tests/eval/ko/answer-labels.yaml`, manifest `nexus/tests/eval/ko/answer-manifest.json`, tenant `ko_eval_packa`); test for the document key.
3. Re-baseline: three runs, keyless bridge, record in `records/audit/`.
4. Second classification of the 20 over-abstention reasons (§2.3), before the owner chooses a candidate.
5. Only if 3 leaves the floors unreachable: implement the chosen candidate in `nexus/nexus/llm/sufficiency.py` under a new identity; three runs per pack.

## 4. Out of scope

- Unit 2 and its switches.
- The floors.
- Any paid backend (keyless bridge only; a paid run needs the owner's permission first).
- Hand review of label lists.

## 5. Not verified

- The §1.3 classification is one reader's reading of the judge's reasons.
- `must_contain` matching is string-level (§1.2).
- How many labels the §2.1 rule keeps, and how much evidence is left in their packets.
- Pack A document keys (§2.4).
- The identity of the judge behind the 2026-08 Pack A verdicts.
- Whether candidate B fits within Z.

## 6. Questions for the owner

1. Accept §2.1 as the negative arm for every run under the gate SPEC, and the retraction in §0?
2. If a revision is needed, B, A, or another?
3. Pack A as a required second pack for passing, given that an earlier judge's verdicts on it exist?
4. The minimum arm size of 30 labels (§2.1) and the cap of two revisions (§2.4)?
