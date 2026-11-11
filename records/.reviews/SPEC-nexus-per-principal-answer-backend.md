---
target: SPEC-nexus-per-principal-answer-backend
critiqued_hash: sha256:703123a0ae64db280b7428e6aa1812ecf76c1330311a3ba9c644c246684c6ba0
critiqued_at: '2026-11-11T17:42:27Z'
issues:
- issue_id: I-001
  category: missing-invariant
  severity: high
  description: The central invariant is 'public callers are never answered by the
    bridge', but nothing enforces it. A principal with llm_provider=None, which includes
    ANONYMOUS in PUBLIC permissive mode and Cloudflare Access identities, falls back
    to NEXUS_LLM_PROVIDER. If that variable is claude-code, as it is on existing dev
    setups that use the keyless bridge, every anonymous or public caller reaches the
    bridge. §4.3 calls this the operator's responsibility. There is no startup check
    that refuses NEXUS_LLM_PROVIDER=claude-code (or the 'claude' alias with a bridge
    URL set) while permissive/PUBLIC mode or public tokens are active.
  status: accepted
  disposition_reason: null
- issue_id: I-002
  category: missing-invariant
  severity: high
  description: 'Principal has no attribute marking it as ''owner/internal'' versus
    ''public''. So validate_startup() cannot check the rule that llm_provider: claude-code
    may be set only on the subscription holder''s own identities. The only guard is
    a YAML comment (§4.1), so the compliance rule from §1 cannot be checked by machine.
    One option is a required flag such as `owner: true` that the validator cross-checks.'
  status: accepted
  disposition_reason: null
- issue_id: I-003
  category: risky-assumption
  severity: high
  description: §1 says retrieval and evidence assembly are 'identical regardless of
    the backend', and §8 requires 'identical evidence packets for the same query'.
    But §4.3 routes the /search query rewrite through the principal's backend. Different
    backends, and even repeated calls to the same nondeterministic LLM, can rewrite
    a query differently, which changes the channels retrieved and therefore the evidence.
    The acceptance criterion conflicts with the design, or the spec has to state whether
    /search/answer also rewrites through the LLM and pin the rewrite.
  status: accepted
  disposition_reason: null
- issue_id: I-004
  category: risky-assumption
  severity: medium
  description: The 'claude' alias is accepted as a valid principal llm_provider (§4.4),
    but it resolves at call time to anthropic when NEXUS_LLM_BRIDGE_URL is unset.
    A principal configured 'claude' therefore moves between backends depending on
    the environment. That is a silent backend switch, which conflicts with §6's 'no
    silent fallback between backends'. Either reject the alias in principal config
    or define it as strictly claude-code.
  status: accepted
  disposition_reason: null
- issue_id: I-005
  category: missing-invariant
  severity: medium
  description: The backend and model id are explicitly not recorded in search_log
    (§2). With no record, there is no after-the-fact way to audit that no public principal
    was ever answered by the bridge. The spec's core compliance invariant has no runtime
    evidence, so the non-goal undermines the goal. At minimum the spec should log
    the resolved backend per request somewhere.
  status: accepted
  disposition_reason: null
- issue_id: I-006
  category: untestable-requirement
  severity: medium
  description: 'The §7 safe-routing tests cover only NEXUS_LLM_PROVIDER=anthropic.
    They do not cover the dangerous configuration: process default claude-code plus
    ANONYMOUS, Cloudflare Access, or tokens without the field. That is the case that
    breaks the invariant. With no test for it, any regression there is invisible.'
  status: accepted
  disposition_reason: null
- issue_id: I-007
  category: unverifiable-claim
  severity: medium
  description: '§3 asserts there are exactly five LLMService construction sites, and
    the structural test in §7 ''counts the call sites''. Only api.py, a2a/server.py
    and cli.py are listed. Other code may also instantiate LLMService: vision/ingest
    paths, claims/value_query, judges, the MCP server (nexus/nexus/mcp/server.py,
    which ADR-0004 names as an agent answer surface) or scripts. If any of those answers
    a principal, the spec should name it. The test should also define whether it counts
    call sites by grep or by AST, so that LLMService(...) inside helpers is not missed.'
  status: accepted
  disposition_reason: null
- issue_id: I-008
  category: risky-assumption
  severity: medium
  description: '§5 claims the predecessor''s bridge security properties ''remain unchanged''.
    Those properties were reasoned about for a dev-only, local topology. Letting a
    server process route to the bridge introduces a new topology: a served/tunnelled
    Nexus (ADR-0004 §3: hosted via local + tunnel + tokens) calling a bridge on the
    developer host. The spec does not re-check bridge reachability, how the bridge
    token is exposed to a served process, or load on the bridge''s concurrency limit.'
  status: accepted
  disposition_reason: null
- issue_id: I-009
  category: undefined
  severity: medium
  description: 'The spec does not say how llm_provider is set or represented for Cloudflare
    Access identities and A2A principals beyond ''leave None''. The owner reaching
    Nexus through Cloudflare Access therefore cannot use the bridge. It is also undefined
    whether A2A callers (policy.py via resolve_principal) can carry llm_provider:
    claude-code. A2A is an external-agent entry point (ADR-0001/0004 §5), so ''owner-only''
    needs an explicit rule there.'
  status: accepted
  disposition_reason: null
- issue_id: I-010
  category: adr-contradiction
  severity: low
  description: ADR-0004 §5 says A2A has no active consumer and 'stays minimal and
    is not extended until a real agent pulls it'. This spec modifies a2a/server.py
    and adds behaviour to it. The change is small, and justified by keeping the invariant
    uniform, but the spec should say so and reconcile it with the ADR's freeze.
  status: accepted
  disposition_reason: null
- issue_id: I-011
  category: undefined
  severity: low
  description: 'How to normalize llm_provider values is not specified: case (''Claude-Code''),
    surrounding whitespace, and an empty string versus null in YAML. It is unclear
    whether validate_startup and LLMService agree on these. A value that passes validation
    could still raise ValueError at call time, or the reverse.'
  status: accepted
  disposition_reason: null
- issue_id: I-012
  category: undefined
  severity: low
  description: §5 leaves the decision on whether to add a retractions.yaml entry for
    the superseded predecessor sentences 'to the reviewer'. The supersession record
    is unresolved, so the predecessor's 'dev convenience, not a server backend' text
    stays stamped and unretracted, and it contradicts this spec.
  status: rejected
  disposition_reason: retractions.yaml withdraws a claim later proven wrong (CONVENTIONS.md).
    The predecessor's non-goals were not wrong; this SPEC deliberately widens the
    scope, so the successor SPEC is the record. §5 now states this decision instead
    of leaving it to the reviewer.
- issue_id: I-013
  category: unverifiable-claim
  severity: low
  description: The §1 summary of Anthropic's subscription terms has no URL, quotation
    or retrieval date. The whole rationale for the invariant rests on it, so it should
    be cited at a specific point in time.
  status: accepted
  disposition_reason: null
- issue_id: I-014
  category: untestable-requirement
  severity: low
  description: §8 acceptance ('within the same minute', identical packets) cannot
    be run because no deployment exists, and the spec puts the unit tests in its place.
    That leaves no end-to-end check that both backends coexist in one process, for
    example per-request LLMService construction with no shared module-level backend
    state. An in-process integration test with a stub bridge could cover this today.
  status: accepted
  disposition_reason: null
approved_by: LivingLikeKrillin
approved_at: '2026-11-11T18:32:44Z'
---

