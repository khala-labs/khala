---
target: SPEC-nexus-improvement-loop
critiqued_hash: sha256:8c010664b9eb55feeadf6c1c3b28ed6336db35097ff2ac6b7ea674b60edcf3fb
critiqued_at: '2026-11-13T01:02:03Z'
issues:
- issue_id: I-001
  category: risky-assumption
  severity: high
  description: '§3.2/§3.3: the U2 re-search must resend the retained question under
    the same conditions, but it also has to carry the fixed prefix `[khala-synthetic]`.
    The prefix changes the query text, so the request no longer reproduces the production
    question: tokenisation, BM25 and vector hits, and the answer can all change. The
    classification is then made on a different input. If the prefix is left off, the
    re-search and the U3 before/after resends (§3.4 never mentions the prefix) write
    back into the retention rows with no prefix. That raises seen_count and leaves
    the replays looking like real user questions to export and candidate generation.
    Neither option keeps both ''same question'' and ''synthetic rows are excluded''.'
  status: open
  disposition_reason: null
- issue_id: I-002
  category: undefined
  severity: high
  description: §3.3 decides the 'generation failure' class by whether `facts_present`
    against the 'candidate requirement' is mostly false. Requirements (`must_contain`)
    are only extracted and signed after a candidate is chosen ('빠진 문서 사례의 순서', label
    promotion). So at classification time there is no requirement to score against,
    and the step is circular. The spec does not say who writes the provisional requirement,
    when, or what it is checked against.
  status: open
  disposition_reason: null
- issue_id: I-003
  category: untestable-requirement
  severity: high
  description: Pass condition ① in §3.4 needs 2 of the 3 before runs to fall into
    one of the U2 classes. The 'wrong evidence' class is triggered by 👎 `wrong_evidence`,
    which is human feedback on the original production answer. It is not a field of
    a fresh before-N.json response, so it cannot be judged per run or by machine.
    Also, `unverified_citations` is listed as a column in `search_log` and the spec
    never shows it in the `/search/answer` response body. If it is absent there, before-N.json
    cannot carry it either.
  status: open
  disposition_reason: null
- issue_id: I-004
  category: undefined
  severity: medium
  description: '''다수'' (majority) in `facts_present` is used in two senses and neither
    is defined. In U2 and ②, it could mean a majority of the `must_contain` items
    within one response, or a majority of runs. ② says ''after 3회 중 2회 이상 요구 성립(facts_present
    다수)'', which stacks both. U2 also never says how many re-search runs are made
    per candidate: one, or three to match §0.2-3.'
  status: open
  disposition_reason: null
- issue_id: I-005
  category: missing-invariant
  severity: medium
  description: Condition ④ is false whenever a run has snippets but an empty `usage`,
    which is what happens when the LLM call itself fails (`llm_failed`). A question
    whose before runs show that failure, the most direct generation failure, can therefore
    never pass, even if the fix works. The spec needs to say whether ④ applies to
    the after runs only, or that LLM-call failures cannot be the subject of a first
    pass-through.
  status: open
  disposition_reason: null
- issue_id: I-006
  category: risky-assumption
  severity: medium
  description: §3.4 ③ assumes every allowed fix moves exactly one of the three version
    values. A change to retrieval code (ranking or filter logic in `hybrid.py` or
    `answer_pipeline.py`) is not a runtime setting, so `search_fingerprint` does not
    move. It is not the prompt module either, so `prompt_version` does not move. With
    no version value changing, ③ is false for a whole kind of 'search setting/ranking'
    fix. In the other direction, `prompt_version` hashes the entire module source,
    so a non-prompt edit inside that module looks like a prompt change. The live app
    runs `--reload` from the main checkout, so unrelated merges inside the window
    can shift these values too.
  status: open
  disposition_reason: null
- issue_id: I-007
  category: risky-assumption
  severity: medium
  description: §3.2 checks the U2 classes again after 3 empty 14-day windows and stops
    the spec after 6, which is 42 and 84 days. The recommended `retain_days` is 30,
    and `expiry.json` has to expire at or before `first_seen + retain_days`. Questions
    that arrive early are therefore deleted before the re-review happens, and a candidate
    found late may expire before the U2→U3 work finishes. The spec has no rule for
    a candidate whose raw text expires partway through the loop.
  status: open
  disposition_reason: null
- issue_id: I-008
  category: missing-invariant
  severity: medium
  description: The reduced `record.json` is kept with no expiry (§7-4 recommends indefinite)
    and survives `query-text disable`. It holds a 'request options hash'. The request
    includes the query text, so if that hash is a plain sha256 over the query or the
    full request, it can be recovered by dictionary attack or joined to `search_log.query_sha256`.
    That undoes the expiry of the raw layer and goes against the Non-goal of not creating
    keys shared with `query_sha256`. The hash input needs to be specified, salted,
    or made to exclude the query.
  status: open
  disposition_reason: null
- issue_id: I-009
  category: risky-assumption
  severity: medium
  description: U2 signs the label against a Pack B snapshot tenant (`corpus.tenant=<snapshot>`),
    and the harness requires `corpus.tenant == --tenant`. U3 runs against live T over
    HTTP. A corpus fix loads into live T, so the snapshot does not include it until
    `extend`/`align`. The harness regression check therefore measures a different
    corpus as well as a different retrieval path (§0.3-3). Its result says nothing
    about the fix, even as 'reference'.
  status: open
  disposition_reason: null
- issue_id: I-010
  category: adr-contradiction
  severity: medium
  description: §1 grounds the 'critique → disposition → approve ledger gate' for implementing
    this spec on ADR-0003 §4. ADR-0003 §4 is about an accountable human promoting
    stream artifacts to canonical, with the specledger critique/approve flow mentioned
    only as an analogy. It does not set a gate on implementing a spec. ADR-0002, ADR-0003
    and ADR-0004 also still say 'Proposed', so citing them as binding authority for
    the gate overstates their status.
  status: open
  disposition_reason: null
- issue_id: I-011
  category: adr-contradiction
  severity: low
  description: ADR-0002's principles and ADR-0003's 'Design now, build on the gate'
    require each feature to be gated on an observed signal. The spec builds U0-a/b
    and the U1 `query-text enable` command (new surface) before any signal exists,
    and calls U4 (a new view plus `health --by-version`) 'operational observation'
    with no gate other than the first pass-through. If the demand-pull clause is no
    longer in force, the spec should cite the ADR or decision that retired it instead
    of leaving the linked ADRs unaddressed.
  status: open
  disposition_reason: null
- issue_id: I-012
  category: untestable-requirement
  severity: medium
  description: The U1 break test 'shared token across two sessions → the runbook check
    catches the premise violation (doc check)' cannot catch anything. Principals are
    not stored (`query_retention.py:69-70`), and a document check cannot see that
    two sessions are using one token at runtime. Condition ⑤'s 'token name' is also
    self-reported by the client writing before-N.json, so nothing in the system verifies
    it.
  status: open
  disposition_reason: null
- issue_id: I-013
  category: undefined
  severity: low
  description: §3.4's corpus-freeze step says T loads manually, so loading can be
    paused, and then says that if periodic reload is configured, its container is
    stopped for the window. The second branch contradicts the premise. The spec also
    does not define how the freeze is checked, for example by asserting `corpus_version`
    is unchanged across before-1..after-3, or by checking the absence of `doc_reingest_events`
    from ADR-0006 in that window.
  status: open
  disposition_reason: null
- issue_id: I-014
  category: unverifiable-claim
  severity: low
  description: Line citations disagree within the document. `abstained`/`abstain_reason`
    is at `api.py:977-978` in §0.2-9 and at `api.py:975-976` in §2.1. The harness
    `--limit` is at `:260` in §0.1-5 and `:261` in §2.4. 'does not write to search_log'
    is at `:481` in §0.1-5 and `:482-483` in §2.4. The header says all of them were
    rechecked on 2026-11-13.
  status: open
  disposition_reason: null
- issue_id: I-015
  category: risky-assumption
  severity: low
  description: §0.3-1 and §3.3 treat `abstained` as equivalent to `evidence_snippets`
    being empty, based on `abstention()` checking 'answer evidence is 0'. The spec
    does not show that the response's `evidence_snippets` is the same set as the answer
    evidence `abstention()` evaluates. If it is filtered or truncated differently,
    the two can disagree and a run could be misclassified.
  status: open
  disposition_reason: null
- issue_id: I-016
  category: missing-invariant
  severity: low
  description: The U2 re-search and the U3 before/after runs are 6 or more live LLM
    calls per question over HTTP. The spec requires a backend declaration and spend
    reporting only for the harness regression run. The HTTP runs need the same rule
    (a keyless backend or prior approval) and should record the backend in `record.json`.
  status: open
  disposition_reason: null
- issue_id: I-017
  category: undefined
  severity: low
  description: U4 groups by `corpus_version`, which depends on caller clearance (§0.3-5),
    but the view has no clearance column, even though the U4 test fixture mixes clearances.
    Rows from different clearances therefore show up as separate corpus versions with
    nothing to tell them apart.
  status: open
  disposition_reason: null
approved_by: null
approved_at: null
---

