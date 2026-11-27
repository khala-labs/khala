---
id: SPEC-nexus-abstention-gate
type: spec
title: Abstain before generating when the evidence does not answer the question —
  measure the judge first, then let the answer path branch on it
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
reviewed_at: '2026-11-27T13:33:01Z'
content_hash: sha256:9f3f98c18e80a57abe76113e92a82782f340449037e26b92ac92f8a4846a4da3
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
- [[ADR-0002]] keeps "system decides, LLM narrates" as the integrity layer. This SPEC reads that
  principle as a constraint on the **answering** LLM: it must not decide whether it speaks or what
  the evidence is. Under this SPEC the answering LLM still decides neither. The decision is a code
  branch on a verdict from a separate judge that sees the query and the evidence and never the
  answer. The verdict can only withhold generation. It cannot add content, citations or numbers.
  When the judge fails, the code falls back to today's behaviour (§4.2). Whether this reading
  holds is the owner's call (§7, question 4). If ADR-0002 is read as requiring deterministic code
  for this decision, a successor ADR comes first and this SPEC waits for it.

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
   - The negative population is fixed before the first baseline run: every answerable label whose
     gold document is in the packet, with that document dropped. No label is removed after any
     run has been seen. (§3.1's 81.6% came from a population narrowed after the baseline. This
     SPEC does not repeat that.)
   - The remaining documents were retrieved for the same query. So this arm is mostly the
     "topic present, fact absent" case that §2 rejects the entity check for. It is not built to
     contain only that case.
   - Dropping the gold document does not prove that the answer is gone. Another retrieved document
     may still answer the question. Every negative-arm label the judge calls `sufficient` is
     listed by label id in the run artifact, for the owner to review. It stays in the denominator.
     Detection on this arm is therefore a lower bound.
3. **Separate failure kinds.** `unparseable` (the judge answered in the wrong shape) and `error`
   (the call failed or timed out) are counted apart from verdicts, and both count against
   detection in the negative arm. The request path uses `judge_raw`, which does not fold call
   failures into `unparseable`.
4. **Same packet as production.** The judge receives the evidence exactly as the answer path
   serialises it (`format_for_llm`).
5. **Record the judge identity** in every artifact. It has four parts: the backend, the model
   name as configured, the SHA-256 of the prompt template in `build_prompt`, and the SHA-256 of
   the verdict parser source. §4.3 binds the gate to this whole identity, not to the model
   alone.
6. **Latency.** p50 and p95 of the judge call, and the added time to first answer text on the
   streaming path.
7. Keyless bridge only. A paid-backend measurement needs the owner's permission first.

### 3.3 Criteria and the order of runs

0. **Floors fixed by this SPEC, before any run.** Signing this SPEC fixes these floors. The
   baseline cannot move them.
   - *X* (maximum over-abstention on the answerable arm) is never above **5%**, which is 2 of 40.
   - *Y* (minimum detection on the negative arm) is never below **80%**.
   - *Z* (maximum added p95 time to first answer text on the streaming path) is never above
     **10 s**.
   The owner may pick stricter values in step 2, never looser ones. §3.1's values sit right at
   the first two floors (2/40, 81.6%). That is a reason to expect a narrow pass or a fail. It is
   not a reason to lower the floors.
1. **Baseline runs** (three) on the current judge. Report both error rates and the latency with
   their run-to-run spread.
2. **Write the criteria into a tracked file before the confirmation run:**
   `records/research/abstention-gate-criteria.md`. Git history then shows the write order.
   - Pack B artifacts are gitignored (partner corpus), so the file carries counts and rates only,
     never label text.
   - The file holds the values of *X*, *Y* and *Z*, and the judge identity (§3.2.5) the runs
     used.
   - The owner chooses the values. The change that adds the file is merged only with the owner's
     approval, and the agent that ran the baseline does not merge it. Unit 2 does not open on a
     criteria file the owner has not approved.
3. **Reachability check before freezing.** For the chosen values, the file states whether the
   baseline values lie on the passing side. A value that no current or proposed judge can reach
   is not a criterion. Examples: "no over-abstention at all", or "90% detection" against a
   baseline near 80%.
4. **Confirmation runs** (three) on the same labels and the same judge identity. There is no
   holdout split. The pool is too small for one: 20 answerable labels would make one label worth
   5%, the whole of *X*. *X*, *Y* and *Z* are bounded by the floors in step 0 and are not fitted
   to labels. So the confirmation is a repeat measurement on this pool. It shows that the judge
   is stable here. It does not show that the judge generalises, and Unit 1's result says so.
5. **Pass rule.** Unit 1 passes only if **every** confirmation run meets all three criteria.
   Run-to-run spread enters through this rule: one run that misses fails Unit 1.
   - Each run reports counts with a 95% Wilson interval.
   - At this size one label is 2.5% of the answerable arm and about 2.6% of the negative arm. A
     pass at 2/40 has an upper bound near 16.5%. Unit 1's result states this and does not claim
     a general over-abstention rate.
6. If Unit 1 fails, the SPEC records the numbers and Unit 2 stays closed. Judge improvements are a
   new change, measured the same way from step 1, under a new judge identity.

## 4. Unit 2 — the gate (only after Unit 1 passes)

### 4.1 Where it sits

- After the final evidence packet is assembled and before any answer text is produced, on both
  `/search/answer` and `/search/answer/stream`. On the streaming path this is before the branch
  at `api.py` that starts `llm_svc.stream`. Once an `answer_delta` has been sent it cannot be
  withdrawn, so the gate must precede the first one.
- `abstention()` takes the verdict as an argument, so both paths still decide through one
  function. Evidence-only requests (`evidence_only`) are not judged.
- Two more call sites produce answers. `nexus/nexus/cli.py` and `nexus/nexus/a2a/server.py` both
  call `generate_answer` ([[ADR-0012]] §Decision 2 lists the same four sites). Both go through
  the same gate function under the same switch and principal rules, so none of the four answers
  around the judge.
- A guard test lists every call of `generate_answer` in product code. It fails if a call is not
  preceded by the gate function. The same pattern as `test_the_sufficiency_signal_is_gone.py`: a
  fifth answer surface cannot skip the gate without the test failing.

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

- **Switches.** Off by default.
  - `NEXUS_ABSTENTION_GATE=on` enables the gate. Any other value, or an unset variable, means off.
  - `NEXUS_ABSTENTION_GATE_PRINCIPALS` limits it to principal ids, comma-separated.
    `NEXUS_ABSTENTION_GATE_TENANTS` does the same for tenant names. A request is gated only if
    its principal or its tenant is listed. Empty lists gate nothing.
  - `NEXUS_ABSTENTION_GATE_TIMEOUT_SECONDS` sets the judge timeout. The default is the p95 judge
    latency from the passing criteria file, rounded up to a whole second. It is capped so that
    the added p95 time to first text stays within *Z*.
- **Reintroduced plumbing.** [[ADR-0012]] §Decision 2 removed the live-path judge plumbing.
  Unit 2 brings back three things it named: a judge timeout, a judge identity and an allow-list.
  - None returns under its old name. `_judge_with_timeout`, `judge_identity()`, `_enabled_for`
    and the `NEXUS_SUFFICIENCY*` variables stay removed.
  - `nexus/tests/test_the_sufficiency_signal_is_gone.py` is unchanged and must keep passing. The
    new names do not match its patterns.
  - The concurrency slot (`_try_take_slot` / `_release_slot`) does not return. See the load note
    below.
- **Judge identity binding.** The passing judge identity (§3.2.5) is pinned as a constant in the
  gate module. It changes only in the same change that adds or updates an owner-approved criteria
  file.
  - At startup the gate computes the configured identity: the judge backend, the configured model
    setting, and the two hashes of the prompt template and parser as loaded.
  - If any part differs from the pin, the gate stays off and the status reports `off`. The
    process logs one warning that names the differing part.
  - If the backend reports no model name (the keyless bridge may not), the identity uses the
    explicitly configured model setting. An unset model setting never matches.
  - Running code never reads the criteria file. The constant is the binding, and the file is the
    record of why it has that value.
  - Changing the model, the prompt template or the parser means running Unit 1 again.
- **Backend.** Unit 1 measures on the keyless bridge only (§3.2.7). So a principal whose judge
  would run on another backend fails the identity check, and the gate stays off for it. Turning
  the gate on there needs a Unit 1 run on that backend, and that is a paid run that needs the
  owner's permission (§7, question 2). Unit 2 is therefore deliverable only for principals whose
  judge runs on the measured backend.
- **Load.** The judge call and the answer call run in sequence within one request, so a request
  holds at most one bridge call at a time. A judge timeout gives `error`, and generation
  proceeds. Timeouts under load are therefore counted, not silent: the report in §5 counts them,
  and the stop condition in §5 acts on them.
- **Rollback** is the switch. The migration in §5 adds nullable columns only. Turning the gate
  off leaves them `NULL` and needs no down-migration.

### 4.4 Verification for Unit 2

- Contract tests on both HTTP paths for every row of §4.2, including that the answering LLM is not
  called on `insufficient` and that no `answer_delta` precedes the gate.
- The same rows on the CLI and A2A paths, plus the call-site guard test (§4.1).
- Tests for the identity binding: each of the four parts, when changed, turns the gate `off`; an
  unset model setting never matches.
- `test_the_sufficiency_signal_is_gone.py` still passes.
- One end-to-end run on the keyless bridge with the gate on for a test principal. It reports
  abstention counts on the answerable and negative arms against Unit 1's numbers, the `error` and
  `unparseable` rates, and the added p95 time to first text against *Z*. The report script in §5
  produces these numbers from `search_log`.

## 5. Consumers

1. **The generation decision** (`abstention()`), which branches on the verdict. This is the
   consumer [[ADR-0012]] asks for.
2. **The API's existing `abstained` / `abstain_reason` fields**, already exposed on both paths.
   No web client code reads them today. The readers in this repository are the evaluation
   scripts (`nexus/scripts/ko_eval_answer_run.py` and the scripts beside it).
   - On abstention the answer text is the fixed notice (§4.2), so a client that shows the answer
     text shows the notice without change.
   - A client that tells `insufficient_evidence` apart from `no_evidence` is a follow-up and not
     part of this SPEC.
3. **The gate record and its report.** Without these, a gate abstention on the live path would
   be recorded nowhere durable. So would the `error` and `unparseable` rates, and a judge that
   broke quietly would turn the gate into a no-op without anyone seeing it.
   - Unit 2 adds two nullable columns to `search_log`: `abstain_reason` and
     `abstention_gate_status`. The second holds the `sufficiency_status` value of §4.2.
   - Both are written on every answer request from the four call sites. Neither name matches
     the columns that `test_the_sufficiency_signal_is_gone.py` guards.
   - Their reader is a report script, `nexus/scripts/abstention_gate_report.py`. For a time
     window and a principal or tenant list it prints counts by `abstain_reason`, counts by
     `abstention_gate_status`, and the added latency.
   - The report is run at the end of the §4.4 end-to-end run, and before any principal or tenant
     is added to the allow-list (§7, question 3).
   - **Stop condition.** Turn the gate off if, in a report window, `error` plus `unparseable` is
     more than 10% of gated requests, or the added p95 time to first text exceeds *Z*. Turning it
     off is the switch in §4.3.
   - The API field `sufficiency_status` has the same values as `abstention_gate_status`. Its
     readers are the contract tests (§4.4), and through the column, the report and its stop
     condition.
4. **Not in this SPEC:** the numerator of `v_image_gap_signal` (migration 011), which waits on a
   machine-readable "answer not available" signal for `SPEC-nexus-screenshot-text-extraction` and
   ADR-0010. `search_log.no_answer` today means "zero search hits", so feeding abstentions into that
   view needs its own approved definition of numerator and denominator. This SPEC only makes such
   a definition possible.

## 6. Out of scope

- Retrieval changes, the cross-lingual channel (`OPEN.md` A95), score thresholds.
- Buffering streamed text until citations are validated (a separate change to the streaming path).
- New `search_log` views, and any `search_log` column other than the two in §5.3. If the
  image-gap follow-up needs a column or a view, that SPEC adds it.
- Web client handling of `insufficient_evidence` (§5.2).
- Any change to the answering prompt.

## 7. Open questions for the owner

1. The values of *X*, *Y* and *Z* after the baseline runs, within the floors of §3.3 step 0. The
   owner approves the criteria file (§3.3 step 2).
2. Whether Unit 1 may also run once on a paid backend. Without that run, the gate stays off for
   every principal whose judge would run on a backend other than the keyless bridge (§4.3,
   `SPEC-nexus-per-principal-answer-backend`).
3. Which principals or tenants the gate is first enabled for after Unit 1 passes.
4. Whether §2's reading of [[ADR-0002]] holds: a code branch on a separate judge's verdict counts
   as "system decides". If not, a successor ADR comes before this SPEC.
