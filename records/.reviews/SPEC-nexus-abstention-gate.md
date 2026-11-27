---
target: SPEC-nexus-abstention-gate
critiqued_hash: sha256:1171c3bdd6490133675395ccc47dae539423c60e860299d35401287f944986d0
critiqued_at: '2026-11-27T12:52:34Z'
issues:
- issue_id: I-001
  category: adr-contradiction
  severity: high
  description: ADR-0002 places 'system decides, LLM narrates' under the mission as
    the integrity layer. §2 makes a non-deterministic LLM judge the only signal that
    decides whether an answer is generated at all. It relaxes open-items' word 'deterministic'
    but never squares this with ADR-0002's principle. Either that conflict needs an
    explicit reconciliation (or a successor ADR), or the SPEC must argue why a judge
    verdict the code branches on counts as 'system decides'.
  status: accepted
  disposition_reason: null
- issue_id: I-002
  category: risky-assumption
  severity: medium
  description: §0 rests its gate declaration on ADR-0012 as a requirement ('as [[ADR-0012]]
    requires'). ADR-0012's status is Proposed, not accepted. If ADR-0012 is revised
    or rejected, this SPEC's gate rationale has no authority behind it. The SPEC should
    state that it depends on ADR-0012 being accepted, or derive its gate from an accepted
    record.
  status: rejected
  disposition_reason: 'ADR-0012 front matter is status: accepted with approved_by
    set; the premise that it is Proposed is false, so the gate rationale rests on
    an accepted record.'
- issue_id: I-003
  category: adr-contradiction
  severity: medium
  description: 'ADR-0012 §Decision 2 removed exactly the live-path plumbing that Unit
    2 needs again: _judge_with_timeout, the concurrency slot (_try_take_slot/_release_slot),
    NEXUS_SUFFICIENCY_TIMEOUT, judge_identity() and the tenant allow-list. §4.3 brings
    back a timeout, a judge-model identity check and a principal/tenant allow-list
    without saying it is undoing that removal. It also doesn''t say whether the old
    names, env vars or tests come back. test_the_sufficiency_signal_is_gone.py asserts
    that no NEXUS_SUFFICIENCY* variable is read, so it will fail if Unit 2 reuses
    that prefix. The SPEC doesn''t address this.'
  status: accepted
  disposition_reason: null
- issue_id: I-004
  category: undefined
  severity: high
  description: '§4.3 binds the gate to ''the judge model that passed Unit 1'' as recorded
    in the criteria file. It never says how running code learns the configured judge
    model or reads the criteria file: the path, the format, when the file is parsed,
    or what happens if it is missing or malformed. ADR-0012 removed judge_identity(),
    and the keyless claude-code bridge may not report a stable model id. As written,
    the binding cannot be built or tested.'
  status: accepted
  disposition_reason: null
- issue_id: I-005
  category: missing-invariant
  severity: medium
  description: §3.2.5 records the prompt version in every artifact. §4.3 binds the
    gate only to the judge model. A change to build_prompt or the parser under the
    same model would leave the gate on with a judge that Unit 1 never measured. The
    binding should cover model + prompt version (and parser), or the SPEC should say
    why the prompt is exempt.
  status: accepted
  disposition_reason: null
- issue_id: I-006
  category: missing-invariant
  severity: medium
  description: 'The gate covers only /search/answer and /search/answer/stream, and
    §4.1 says ''both paths still decide through one function''. ADR-0012 lists other
    answer-producing call sites: cli.py and a2a/server.py. The SPEC doesn''t say whether
    those paths are gated, exempt, or kept from producing answers that skip the judge.
    One gate function doesn''t guarantee every answer surface goes through it.'
  status: accepted
  disposition_reason: null
- issue_id: I-007
  category: risky-assumption
  severity: medium
  description: §3.3 step 3 requires that baseline values sit on the passing side of
    X and Y before the criteria are frozen. Combined with an owner choosing X and
    Y after seeing the baselines, this lets the thresholds be fitted to whatever the
    baseline shows. Pre-registration then only fixes the order of commits; it doesn't
    constrain the outcome. The SPEC needs a value-independent floor (for example,
    the minimum detection that justifies withholding answers) set before the baseline
    runs.
  status: accepted
  disposition_reason: null
- issue_id: I-008
  category: untestable-requirement
  severity: medium
  description: §3.3 step 4 holds out labels 'where the label pool allows'. With 45
    Pack B labels (40 answerable), there is no stated rule for when the pool allows
    a holdout, so the requirement can always be waived. The SPEC should state the
    split, or the minimum pool size below which confirmation reuses the tuning labels,
    and how that weakens the claim.
  status: accepted
  disposition_reason: null
- issue_id: I-009
  category: unverifiable-claim
  severity: medium
  description: The answerable arm has 40 labels and the negative arm about 38, measured
    three times. The SPEC doesn't say what over-abstention resolution this gives (one
    label is 2.5%) or how run-to-run spread enters the pass decision. A criterion
    such as 'at most X' over 40 items with a non-deterministic judge can pass or fail
    on one label's flip, and §3.1 already notes how weak small samples are.
  status: accepted
  disposition_reason: null
- issue_id: I-010
  category: risky-assumption
  severity: medium
  description: The negative arm drops only the gold document. Other retrieved documents
    may still contain the answer, or may cover the topic without the fact. §2 rejects
    the entity check because of 'topic present, fact absent', but the negative arm
    doesn't sample that failure kind on purpose. §3.1's 81.6% came from a population
    narrowed after the baseline was seen, and §3.2 doesn't fix how the negative population
    is filtered before the runs.
  status: accepted
  disposition_reason: null
- issue_id: I-011
  category: undefined
  severity: medium
  description: The SPEC doesn't say who writes and commits the criteria file. Approving
    the SPEC approves 'the plan for both units' while X and Y are still unknown. If
    the agent writes X and Y and opens Unit 2, that is self-approval of the actual
    gate, which the repo's review rules forbid. The SPEC should require that the criteria
    file is a signed or owner-approved record before the confirmation run.
  status: accepted
  disposition_reason: null
- issue_id: I-012
  category: adr-contradiction
  severity: medium
  description: §0 says 'Nothing in this SPEC records a verdict that no code reads',
    and ADR-0012 demands a named consumer. §4.2 adds a new response field, sufficiency_status,
    with values judged/unparseable/error/off, and a new abstain_reason value, insufficient_evidence.
    §5 names no reader for sufficiency_status. That is the same pattern of ungated
    observation with no consumer that ADR-0012 reversed.
  status: accepted
  disposition_reason: null
- issue_id: I-013
  category: unverifiable-claim
  severity: low
  description: §5.2 says abstained/abstain_reason are 'read by the web client' and
    gives no file or symbol. It also doesn't show that the client handles the new
    reason value insufficient_evidence correctly, for example by showing a distinct
    message rather than treating it as no_evidence.
  status: accepted
  disposition_reason: null
- issue_id: I-014
  category: undefined
  severity: medium
  description: §1 names as part of the problem that search_log.no_answer counts zero
    for refusals. §6 then forbids new search_log columns, and §5.3 defers the logging
    definition. After Unit 2, gate abstentions on the live path are recorded nowhere
    durable. It is unclear how §4.4's end-to-end abstention counts are collected,
    or how anyone will later see that the gate over-abstains in production.
  status: accepted
  disposition_reason: null
- issue_id: I-015
  category: risky-assumption
  severity: medium
  description: On the live path the judge call comes before every answer. It runs
    on the same keyless bridge as the answering LLM, which has limited concurrency
    (ADR-0012 removed the old slot limiter). The SPEC measures latency (§3.2.6) but
    sets no acceptable latency budget. It doesn't address queueing or contention between
    judge and answer calls, or the case where judge timeouts under load quietly turn
    the gate into status=error everywhere.
  status: accepted
  disposition_reason: null
- issue_id: I-016
  category: undefined
  severity: low
  description: The judge timeout value, the enabling env var name ('fixed in implementation')
    and the format of the principal/tenant list are left undefined. These shape §4.2's
    error row and §4.4's contract tests, so tests can't be written against the SPEC
    alone.
  status: accepted
  disposition_reason: null
- issue_id: I-017
  category: missing-invariant
  severity: low
  description: Unparseable and error verdicts fall through to generation, which is
    correct for avoiding mass abstention. But the SPEC sets no ceiling or alert on
    their rate while the gate is on. A judge that breaks quietly turns the gate off
    without anyone noticing, which is the same 'built-but-blind' failure the repo
    has hit before.
  status: accepted
  disposition_reason: null
- issue_id: I-018
  category: risky-assumption
  severity: low
  description: Unit 1 measures the judge on the keyless bridge only (§3.2.7), and
    the gate is bound to that model. If production answers run on a different backend
    (open question 2, SPEC-nexus-per-principal-answer-backend), the gate either stays
    off in production indefinitely or needs an unbudgeted paid measurement. The SPEC
    leaves this unresolved while presenting Unit 2 as the deliverable.
  status: accepted
  disposition_reason: null
approved_by: LivingLikeKrillin
approved_at: '2026-11-27T13:33:01Z'
---

