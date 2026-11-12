---
target: SPEC-nexus-shared-answer-pipeline
critiqued_hash: sha256:d8f4235f315678bf679cea631535feef451440894b4a3f1d099c0a153dfc0e8a
critiqued_at: '2026-11-12T15:43:46Z'
issues:
- issue_id: I-001
  category: adr-contradiction
  severity: high
  description: §4.2 says A2A and the CLI build RetrievalDependencies from direct imports
    and never import nexus/nexus/api.py. But step 1 of retrieve_for_answer needs deps.search_channels,
    and §2 keeps _search_channels in api.py. _load_gazetteer and _build_entity_patterns
    are patched in the nexus.api namespace, so they are probably defined there too,
    and they are missing from the A2A/CLI import list (nexus.search.hybrid, reconcile,
    router, index.graph_extractor, repositories.graph, config). The design cannot
    work for A2A and the CLI unless those helpers move, which the non-goals forbid.
  status: accepted
  disposition_reason: 'Fixed. Channels are computed by the caller: HTTP handlers call
    api._search_channels and pass the result; A2A and the CLI pass None, as neither
    runs that step today. The pipeline never imports _search_channels. The guess that
    _load_gazetteer and _build_entity_patterns live in api.py was wrong: they are
    in nexus/index/graph_extractor.py and api.py imports them, which is why tests
    patch them there.'
- issue_id: I-002
  category: risky-assumption
  severity: high
  description: The single fixed sequence in retrieve_for_answer (rewrite queries and
    select channels, detect entities with the gazetteer, determine_route) assumes
    A2A and the CLI run these steps today. §3 says A2A hardcodes route 'auto' and
    drops history, and the CLI passes 9 kwargs with no mention of channel selection
    or gazetteer matching. If they do not run these steps today, routing them through
    the pipeline changes their retrieval behaviour. §5 Compatibility does not cover
    that change, and it undercuts the 'only moves existing retrieval steps' basis
    of the ADR-0008 backstop ruling.
  status: accepted
  disposition_reason: 'Fixed. §3 now lists the steps each surface runs today (A2A
    and the CLI: entity detection, route, search, no channel step), and the pipeline
    runs only those steps per caller. No surface gains a step.'
- issue_id: I-003
  category: adr-contradiction
  severity: medium
  description: The backstop ruling that ADR-0008 does-not-fire rests on 'no search
    channel added' and 'removes accidental differences'. If A2A and the CLI gain query
    rewrite or channel selection they do not have today, a surface's retrieval stack
    is materially expanded, which is the kind of event ADR-0008 §5 says should trigger
    a re-read. The SPEC should state per surface which retrieval steps are new, or
    limit the pipeline to steps each surface already performs. Separately, ADR-0008
    is still 'In review' (binding on acceptance), so the backstop row cites an ADR
    that is not yet binding.
  status: accepted
  disposition_reason: 'Fixed by the I-001/I-002 change; the backstop reread now says
    no surface gains a retrieval step. The second point is wrong: ADR-0008 is accepted,
    not in review.'
- issue_id: I-004
  category: unverifiable-claim
  severity: high
  description: Goal §1 promises that evidence passing through packet_for_answer is
    guaranteed 'by structural design'. In the design, though, packet_for_answer is
    an injected callable (deps.packet_for_answer), and the CLI skips it conditionally
    through want_packet. Any caller can pass a substitute or set want_packet=False.
    Enforcement still comes from the co_names bytecode walker that §3 calls insufficient,
    so the structural guarantee is claimed but not delivered.
  status: accepted
  disposition_reason: Fixed. The 'by structural design' claim is removed. packet_for_answer
    stays injected because two test files patch it on nexus.api; the SPEC says the
    seam is held by one call site plus the test, and the A2A and CLI deps always bind
    reconcile.packet_for_answer.
- issue_id: I-005
  category: untestable-requirement
  severity: medium
  description: 'The extended co_names walker in §6 will find the name ''packet_for_answer''
    as an attribute access on deps whatever callable is injected. The seam test would
    therefore pass even if a surface supplied a no-op. The proposed mutation check
    (''a test variant that removes packet_for_answer from retrieve_for_answer'') has
    no defined mechanism: it does not say whether this is source rewriting, a fixture
    or mutmut, or how it runs in CI. Its pass condition cannot be reproduced as written.'
  status: accepted
  disposition_reason: 'Fixed. The seam test asserts surfaces call retrieve_for_answer
    and not hybrid_search/packet_for_answer themselves, and checks what the A2A/CLI
    deps bind. The mutation check is defined: parse answer_pipeline.py with ast, drop
    the call node, run the same walker, expect failure; an ordinary pytest case in
    the unit job.'
- issue_id: I-006
  category: undefined
  severity: high
  description: The SPEC never says which module resolve_read_scope lives in, or whether
    it calls effective_read_scope, the clearance helpers and the logger through the
    nexus.api namespace at request time. Tests that run monkeypatch.setattr(api, 'effective_read_scope'
    / clearance helpers, ...) would silently bypass their patches if the helper imports
    these directly. That would break the 'all 118 pass unmodified' acceptance criterion,
    which is the same failure mode §3 describes for hybrid_search.
  status: accepted
  disposition_reason: Fixed. _resolve_read_scope is a private helper in api.py and
    reads effective_read_scope from the nexus.api namespace at call time, so the existing
    patch in test_answer_says_what_it_searched.py keeps working.
- issue_id: I-007
  category: missing-invariant
  severity: medium
  description: Read-scope consolidation leaves A2A out. Per §4.4.3, _default_answer_fn
    calls effective_read_scope directly instead of resolve_read_scope, so A2A still
    has its own read-scope code with no out-of-scope warning log. This contradicts
    the goal of a single read-scope/clearance/out-of-scope helper. Acceptance item
    1 also does not list A2A among the surfaces that must use resolve_read_scope.
  status: accepted
  disposition_reason: Fixed in part. A2A has no HTTP request, so it calls effective_read_scope
    directly, but it now emits the same out-of-scope warning event; acceptance lists
    A2A.
- issue_id: I-008
  category: risky-assumption
  severity: medium
  description: The A2A tenant-clamp fix widens what A2A tokens can read. Every A2A
    principal whose read_tenants lists other tenants will be able to read across them
    as soon as this ships. The SPEC treats this as a defect fix inside a refactor.
    It does not check that existing A2A tokens' read_tenants values were set with
    cross-tenant reads in mind, and it has no negative test that a token without those
    tenants is still refused.
  status: accepted
  disposition_reason: Fixed. §5 states the widening (A2A then matches what HTTP already
    allows). No Nexus deployment is running, so no issued token changes in the field.
    A negative test pins that a tenant outside read_tenants is refused.
- issue_id: I-009
  category: missing-invariant
  severity: medium
  description: Each surface keeps its current hybrid_search argument set (14 kwargs
    on HTTP, 9 on A2A/CLI, A2A top_k=10). That keeps the drift the SPEC says it eliminates.
    Which 5 arguments differ, and whether that difference is intended, is never stated.
    No invariant or test pins the per-surface argument set, so future drift stays
    invisible.
  status: accepted
  disposition_reason: Fixed. The five HTTP-only arguments are named (window, channels,
    exclude_doc_types, identifier_channel_asked, fusion_doc_agreement); they come
    from HTTP request fields A2A and the CLI do not have. An argument-set test pins
    each surface's set.
- issue_id: I-010
  category: undefined
  severity: medium
  description: Several parts of the pipeline contract are undefined. want_packet is
    not in the retrieve_for_answer signature, and QueryInputs is called 'illustrative'.
    The design does not say what Retrieval.packet is when want_packet is false. It
    does not say how A2A's route 'auto' and top_k=10 reach the pipeline ('passes explicit
    parameters' where?). Retrieval.timings has no defined stages or units, and nothing
    says whether record_search consumes it.
  status: accepted
  disposition_reason: Fixed. The signature is defined (route, top_k, channels, search_opts,
    want_packet), Retrieval.packet is None when not built, and timings is hybrid_search's
    timing_ms passed through unchanged.
- issue_id: I-011
  category: missing-invariant
  severity: medium
  description: POST /search shares the retrieval front half with the answer paths
    (§3), but §4.4.5 keeps its own hybrid_search call outside retrieve_for_answer
    ('uses the shared channel selection logic' without saying how). /search can therefore
    still drift from the answer surfaces. Acceptance item 1 does not cover /search's
    retrieval path at all.
  status: accepted
  disposition_reason: Fixed. POST /search runs the same front half today, so it calls
    retrieve_for_answer with want_packet=False and is in acceptance.
- issue_id: I-012
  category: undefined
  severity: medium
  description: The stream's done event is to carry evidence_only, defined as 'whether
    the request asked for evidence without calling the model'. §5 says the stream's
    request schema is unchanged, and the SPEC does not show that the stream endpoint
    accepts an evidence_only request mode. The value's source on the stream path is
    undefined. The SPEC also does not say how abstained/abstain_reason are computed
    on the streaming path, or whether that reuses generate_answer logic or duplicates
    it.
  status: accepted
  disposition_reason: Fixed. The stream takes evidence_only in its request but ignores
    it, so the done event does not gain evidence_only; whether the stream should honour
    it is an open question. abstained/abstain_reason come from one shared helper (not
    packet.snippets → 'no_evidence').
- issue_id: I-013
  category: untestable-requirement
  severity: low
  description: The parity test subtracts 'a documented allowlist' from the keys compared,
    but the SPEC does not give the allowlist's contents or say where it is documented
    and reviewed. An unbounded allowlist can turn the superset check into a no-op.
  status: accepted
  disposition_reason: Fixed. The allowlist is exactly {evidence_only}, written in
    the test with its reason.
- issue_id: I-014
  category: risky-assumption
  severity: low
  description: §6 requires updating test_answer_surfaces_share_the_seam.py and test_answer_backend_per_principal.py,
    while §6/§7 require all 118 monkeypatch tests to pass with zero edits to test
    code. If either file contains monkeypatch.setattr(api, ...) calls (the backend-per-principal
    test plausibly patches api.LLMService), the two requirements conflict. The SPEC
    should say whether these files are among the 13 counted.
  status: accepted
  disposition_reason: 'Fixed. Neither seam test file patches nexus.api (verified:
    0 calls); the clamp test''s 13 patch lines stay as they are and only new cases
    are added.'
- issue_id: I-015
  category: untestable-requirement
  severity: low
  description: The acceptance criterion hardcodes '118 existing monkeypatch test cases'
    across 13 files, a count taken on 2026-11-13. The count changes as tests are added
    or removed, and no mechanism (for example a grep-based count in CI) ties the criterion
    to the suite as it stands at merge.
  status: accepted
  disposition_reason: Fixed. Acceptance is 'every existing test that patches nexus.api
    passes with its patch lines unchanged'; 118 stays only as a dated snapshot in
    §3.
- issue_id: I-016
  category: scope-creep
  severity: low
  description: §4.4 lists 'five surfaces' (it adds POST /search and the /search/explain
    adoption), while Goal §1 and §3 define four answer surfaces. The SPEC also bundles
    a security behaviour change (the A2A read clamp) and API payload additions (the
    union fields, four new done-event keys) into a refactor that the backstop ruling
    describes as only moving existing steps.
  status: accepted
  disposition_reason: Fixed. §4.4 is 'Callers' (four answer surfaces plus /search
    and /search/explain), and the backstop reread names the clamp fix and the added
    keys and says neither touches the retrieval stack.
- issue_id: I-017
  category: missing-invariant
  severity: low
  description: Telemetry stays divergent. The SPEC does not say whether A2A and the
    CLI call record_search or log_answer_backend, or how LLMService is chosen for
    an A2A principal (llm_provider). Execution telemetry is part of the 14-step sequence,
    but only the HTTP paths are specified, so record_search drift between surfaces
    is left unaddressed.
  status: deferred
  disposition_reason: Telemetry consolidation is out of scope. Each surface keeps
    its record_search call where it is today (A2A and the CLI both call it), and A2A's
    backend choice stays as SPEC-nexus-per-principal-answer-backend set it. The SPEC
    now says so.
approved_by: LivingLikeKrillin
approved_at: '2026-11-12T16:53:45Z'
---

