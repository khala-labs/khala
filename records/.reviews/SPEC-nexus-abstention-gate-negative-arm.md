---
target: SPEC-nexus-abstention-gate-negative-arm
critiqued_hash: sha256:51a4f3fb5d8b2cb8f7f9a24bd85d375b34a1103086fe8339f64b01d89b44a01d
critiqued_at: '2026-11-28T01:06:37Z'
issues:
- issue_id: I-001
  category: risky-assumption
  severity: high
  description: §2.2 says a judge revision starts only if the re-baseline leaves X
    or Y unreachable. But §2.1 leaves the answerable arm unchanged, and the baseline
    already put X at 10.3–20.5% against a ≤5% floor, which §1.1 calls unreachable.
    Re-baselining on a new negative arm cannot move X. Unless run-to-run variance
    alone brings X down, the 'only if' branch is effectively certain, and the SPEC
    presents as conditional a revision that is all but decided. Say this outright,
    or explain how the re-baseline could make X reachable.
  status: accepted
  disposition_reason: null
- issue_id: I-002
  category: scope-creep
  severity: high
  description: §0 says this SPEC does not change the gate SPEC's pass rule (§3.3 step
    5). §2.4 then requires the floors to hold on both Pack B and Pack A. Adding a
    second required population changes the pass rule. Either drop the claim in §0
    or route the Pack A requirement through the gate SPEC's own amendment or retraction
    path.
  status: accepted
  disposition_reason: null
- issue_id: I-003
  category: risky-assumption
  severity: high
  description: §2.1 drops every document whose text contains any must_contain group.
    If those groups include common tokens (numbers, generic nouns, product names),
    this can strip most on-topic documents. The negative packets then become sparse
    or off-topic, much easier to call insufficient than realistic near-miss retrieval.
    That would inflate Y, the opposite of the bias this SPEC sets out to remove. No
    measure of how topical the remaining packet is gets recorded (only drop counts),
    and §5 admits that how much evidence remains is unknown.
  status: accepted
  disposition_reason: null
- issue_id: I-004
  category: missing-invariant
  severity: high
  description: There is no minimum size for the negative arm after the §2.1 exclusions.
    If the rule keeps only a handful of labels, Wilson intervals widen until the ≥80%
    Y floor is meaningless or trivially met. Define a minimum n, or a maximum exclusion
    rate, below which the arm is invalid and the run does not count.
  status: accepted
  disposition_reason: null
- issue_id: I-005
  category: missing-invariant
  severity: medium
  description: '§2.4 treats Pack A as an untouched confirmation set, but nothing says
    what happens when the frozen revised judge fails on Pack A. If a further revision
    is allowed, Pack A has been read and is no longer untouched. The SPEC needs a
    rule: either a Pack A failure ends the attempt, or a third untouched set is needed.
    There is also no cap on how many revise-and-rerun cycles Pack B may absorb.'
  status: accepted
  disposition_reason: null
- issue_id: I-006
  category: untestable-requirement
  severity: medium
  description: '''The judge''s verdicts on Pack A are not read until the revised judge''s
    identity is frozen in a commit'' has no enforcing mechanism, such as a recorder
    refusing Pack A runs without a committed identity hash, or an audit trail. Compliance
    cannot be checked afterwards.'
  status: accepted
  disposition_reason: null
- issue_id: I-007
  category: unverifiable-claim
  severity: medium
  description: The claim that 'the judge has not been run on it [Pack A] in this work'
    leaves prior work open. ADR-0012 keeps the offline harness `ko_eval_answer_run.py
    --sufficiency`, which writes sufficiency × outcome grids into run artifacts. Earlier
    Pack A runs with that harness would mean the judge's Pack A behaviour has already
    been seen. State whether any such artifacts exist.
  status: accepted
  disposition_reason: null
- issue_id: I-008
  category: undefined
  severity: medium
  description: §2.4 does not say whether the §2.1 negative-arm rule applies to Pack
    A, or whether Pack A's 5 unanswerable labels take part in the pass computation.
    With 'floors on both packs', the Pack A population for X and Y is unspecified.
  status: accepted
  disposition_reason: null
- issue_id: I-009
  category: adr-contradiction
  severity: medium
  description: Candidate B claims to keep the ADR-0002 reading ('system decides, LLM
    narrates') because code derives the verdict. But the found/absent/conflicting
    marks are themselves LLM judgments, and code just ORs them, so the decision still
    rests on the LLM. A judge that lists zero required facts also yields 'sufficient'
    by vacuous truth. The claim needs an argument, plus an invariant such as 'at least
    one fact must be listed, or the output is unparseable'.
  status: accepted
  disposition_reason: null
- issue_id: I-010
  category: adr-contradiction
  severity: medium
  description: ADR-0012 removed `judge_identity()` from `nexus/llm/sufficiency.py`.
    It also kept the judge module as an offline evaluation instrument, separate from
    any live path, which must start from a new SPEC with a named consumer. This SPEC
    relies on a 'judge identity (prompt or parser hash)' without saying where that
    identity is now computed. Revising `sufficiency.py` (work item 4) also silently
    changes the judge used by the retained offline `--sufficiency` grid, which breaks
    comparability with earlier grids. The SPEC should also note that ADR-0012 is still
    Proposed.
  status: accepted
  disposition_reason: 'Body now says where the identity is computed and that the --sufficiency
    grid changes with the judge. The issue''s remark that ADR-0012 is Proposed is
    false (front matter: status accepted) and was not acted on.'
- issue_id: I-011
  category: scope-creep
  severity: medium
  description: Candidate A adds a row to the signed gate SPEC's §4.2 table, with approval
    taken 'in this SPEC'. §0 limits this SPEC's effect on the signed body to one retraction
    through CONVENTIONS §Retracting a claim. Changing a table in a signed document
    is a body change outside that mechanism.
  status: accepted
  disposition_reason: null
- issue_id: I-012
  category: unverifiable-claim
  severity: medium
  description: The recommendation for B rests on 'the paper cited (arXiv 2411.06037)
    says structural change is needed and prompt improvement is not enough'. No section
    or quote is given. The cited work is mainly about a sufficient-context autorater
    and selective generation, and may not support the claim as worded. Quote the passage,
    or soften the claim.
  status: accepted
  disposition_reason: null
- issue_id: I-013
  category: risky-assumption
  severity: low
  description: Candidate C is rejected because it 'triples judge calls' against p95.
    Three votes issued in parallel cost concurrency, not three times the latency;
    per-call p95 would rise only from bridge queueing at concurrency 3. The rejection
    conflates throughput with added latency, and the measured p95 already includes
    eval-time queueing at concurrency 3, which may not match live-path latency.
  status: accepted
  disposition_reason: null
- issue_id: I-014
  category: undefined
  severity: low
  description: §2.1 excludes labels whose packet becomes empty, on the grounds that
    the gate's empty-packet path abstains anyway. Those are exactly the cases the
    gate handles correctly, so excluding them shifts Y. The SPEC should say whether
    excluded labels count toward any reported figure, and state the direction of the
    bias.
  status: accepted
  disposition_reason: null
- issue_id: I-015
  category: risky-assumption
  severity: low
  description: §2.1 relies on listing every negative-arm label judged sufficient by
    id as the guard against paraphrase misses. §4 puts hand review of label lists
    out of scope, so nobody is assigned to check whether those listed cases are real
    misses or judge errors. The guard is disclosure without adjudication.
  status: accepted
  disposition_reason: null
- issue_id: I-016
  category: unverifiable-claim
  severity: low
  description: The §1.3 reason taxonomy (6/9/3/2) is the basis for choosing between
    candidates A and B, yet it is one reader's unreviewed classification of free-text
    REASON lines (§5 says so). The recommendation should be conditioned on that, or
    a second classification pass added before choosing.
  status: accepted
  disposition_reason: null
approved_by: LivingLikeKrillin
approved_at: '2026-11-28T01:24:04Z'
---

