---
id: SPEC-nexus-shared-answer-pipeline
type: spec
title: 'One answer pipeline for every surface: retrieval, evidence shaping and read
  scope are shared, not copied'
status: in_review
linked_adrs:
- ADR-0008
tags:
- nexus
- search
- refactor
date: '2026-11-12T15:42:23Z'
---
# One answer pipeline for every surface: retrieval, evidence shaping and read scope are shared, not copied

## Backstop record

```yaml
backstop:
- row: adr-0008-retrieval-stack
  reread: proposed 2026-11-13 — this SPEC adds no search channel, index backend, tokenizer, embedding model or connector, and no surface gains a retrieval step it does not run today; it moves each surface's existing steps into one function. It also fixes the A2A read clamp and adds response keys; neither touches the retrieval stack.
  clause: none
  ruling: does-not-fire
  declared_by: LivingLikeKrillin
  declared_at: '2026-11-13'
  reason: >-
    Consolidating copies of the existing retrieval sequence does not widen the retrieval stack. The owner confirms this ruling when approving.
```

## 1. Goal

- Consolidate duplicated retrieval flows into a single pipeline function used by all four answer surfaces.
- Consolidate evidence shaping for HTTP answer generation into a single shared helper.
- Consolidate read scope validation, clearance extraction, and out-of-scope logging into a single helper.
- Every surface reaches `packet_for_answer` through one call site in `retrieve_for_answer`, and the seam test checks that call site and that each surface calls the function.
- Eliminate unintended behavioral drift across `POST /search/answer`, `POST /search/answer/stream`, the A2A default answer function, and the CLI `query` command.
- Fix the A2A tenant clamp defect so multi-tenant read tokens can query all authorized tenants.
- Every existing test that patches names on `nexus.api` keeps working without edits to its patch lines.
- Isolate the shared retrieval implementation so non-FastAPI callers (A2A and CLI) avoid import-time side effects from `nexus/nexus/api.py`.

## 2. Non-goals

- Adding new search channels, index backends, tokenizers, embedding models, or data connectors.
- Modifying prompt templates, text generation routines, citation verification, or numeric verification logic.
- Moving `_search_channels`, `_ranked`, or `_search_hit_to_dict` out of `nexus/nexus/api.py` at this time.
- Refactoring the 22 locations executing direct SQL against the graph outside `nexus/nexus/repositories/graph.py`.
- Converting `nexus/nexus/api.py` into an application factory.
- Changing public HTTP request bodies or command-line option flags.
- Removing or renaming any existing response payload attributes.
- Deciding whether `doc_debts` should be emitted to external API consumers.
- Consolidating telemetry: each surface keeps its own `record_search` call where it is today.

## 3. What exists (verified 2026-11-13)

Nexus (`nexus/nexus/`) is a retrieval-augmented generation service in `khala-labs/khala`. It exposes four answer surfaces:
- `POST /search/answer` located in `nexus/nexus/api.py`.
- `POST /search/answer/stream` located in `nexus/nexus/api.py`.
- The A2A default answer function `_default_answer_fn` located in `nexus/nexus/a2a/server.py`.
- The CLI command `query` located in `nexus/nexus/cli.py`.

Upstream clients rely on these endpoints. The Nexus MCP server and the Slack bot are HTTP clients of `POST /search/answer`. They depend on its response structure. `POST /search` in `api.py` provides retrieval without generation. It shares the retrieval front half with the answer endpoints.

A structure review conducted on 2026-11-12 showed that the retrieval sequence was copied across each surface. These copies have drifted. Two defects caused by this drift were recently repaired:
- The streaming endpoint dropped the synthetic-data marker on evidence snippets.
- The `/diff` endpoint omitted the tenant isolation filter.

ADR-0008 is accepted. The repository defines an architectural seam in `nexus/CLAUDE.md`. The rule states that all evidence used for answer generation must pass through `nexus/nexus/search/reconcile.py::packet_for_answer` on every surface. Enforcement currently relies on `tests/test_answer_surfaces_share_the_seam.py`. That test uses Python reflection. It walks the code objects (`co_names`, including nested functions) of each surface handler. It counts whether `packet_for_answer` is present. The invariant is held only by bytecode inspection, not by code structure.

Steps each surface runs today:
- HTTP answer paths and `POST /search`: `_search_channels` (defined in `api.py`) → entity detection → `determine_route(query, req.route, …)` → `hybrid_search`; the two answer paths then always call `packet_for_answer`.
- A2A: entity detection → `determine_route(query, "auto", …)` → `hybrid_search` → `packet_for_answer` always; no `_search_channels`.
- CLI `query`: entity detection → `determine_route(q, route, …)` → `hybrid_search`; `packet_for_answer` only when `--answer` is given and there are hits; no `_search_channels`.

The full execution sequence on the HTTP answer paths contains 14 sequential steps:
1. Resolve read scope (`asked_tenant`, `effective_read_scope`, out-of-scope check).
2. Validate route parameters.
3. Validate conversation history.
4. Load system configuration via `_load_config`.
5. Instantiate embedding service via `embedding_service_from_config`.
6. Instantiate LLM service via `LLMService(provider=principal.llm_provider)` and record backend with `log_answer_backend`.
7. Rewrite query and select search channels via `_search_channels` (calls the LLM only when conversation history is present).
8. Detect entities via gazetteer matching (`_load_gazetteer`, `_build_entity_patterns`, and `find_entities_in_text`).
9. Select retrieval route via `determine_route`.
10. Execute search via `hybrid_search` using 14 keyword arguments.
11. Build reconciliation packet via `packet_for_answer`.
12. Generate answer text via LLM.
13. Perform citation and numerical consistency validation.
14. Record execution telemetry and search signals via `record_search`.

Evidence shaping diverges across the two HTTP endpoints:
- `POST /search/answer` calls `nexus/nexus/llm/answer.py::generate_answer`. Lines 155 to 206 of `answer.py` format evidence snippets, build the provenance list, format graph findings, and calculate `doc_debts`. No surface currently transmits `doc_debts` to clients.
- `POST /search/answer/stream` re-implements evidence shaping inline inside `api.py`. It diverges from `generate_answer` in three ways, none documented as intentional:
  - Provenance items in the stream contain `doc_title`. The standard answer path provides `approved_hash`.
  - Graph observed edges in the stream use key `call_count`. The standard answer path uses key `calls`. The web client at `web/js/views/chat.js` expects `call_count`.
  - The final `done` SSE event in the stream omits four keys present on the non-streaming endpoint: `abstained`, `abstain_reason`, `n_unknown_origin_time`, and `evidence_only`. The stream endpoint takes the same `AnswerRequest` (which has `evidence_only`) but ignores `evidence_only` and always generates. The stream already computes `abstained` as `not packet.snippets`; the answer path sets `abstain_reason = "no_evidence"` under the same condition (`llm/answer.py`).

Read scope handling also diverges across endpoints:
- The read scope preamble (`asked_tenant`, `effective_read_scope`, and the out-of-scope warning log) is duplicated across `/search`, `/search/answer`, and `/search/answer/stream`.
- Endpoint `/search/explain` drops the out-of-scope flag without emitting a warning log.

The non-HTTP answer surfaces diverge further:
- In `a2a/server.py`, `_default_answer_fn` incorrectly calls `effective_scope` instead of `effective_read_scope`. `effective_scope` is the scalar write clamp. Consequently, an A2A token authorized with multiple tenants in `read_tenants` is restricted to reading only its own primary tenant.
- A2A manages its own configuration loading. It calls `hybrid_search` with only 9 keyword arguments and sets `top_k=10`. It hardcodes the route to `auto`. It validates conversation history but discards it immediately (documented as intended).
- In `cli.py`, `query` takes `--tenant` and hardcodes clearance to `"INTERNAL"` because the CLI runs without an authenticated principal. It calls `hybrid_search` with 9 keyword arguments. It builds a reconciliation packet and generates an answer only when `--answer` is passed and search hits exist. If zero search hits return, it writes no answer span row.
- The five `hybrid_search` arguments the HTTP paths pass and A2A/CLI do not: `window`, `channels`, `exclude_doc_types`, `identifier_channel_asked`, `fusion_doc_agreement`. They come from HTTP request fields that A2A and the CLI do not have.
- A2A and the CLI both call `record_search` today.

Test coupling shapes the refactoring boundaries:
- 13 test files contain 118 calls to `monkeypatch.setattr(api, ...)`. This is kept only as a dated snapshot (2026-11-13), not as an acceptance number. These patches target names in the `nexus.api` namespace.
- The most frequently patched names in `nexus.api` are:
  - `record_search`: 15 call sites.
  - `hybrid_search`: 14 call sites.
  - `LLMService`: 11 call sites.
  - `embedding_service_from_config`: 9 call sites.
  - `generate_answer`: 8 call sites.
  - `find_entities_in_text`: 8 call sites.
  - `_load_gazetteer`: 8 call sites.
  - `_load_config`: 8 call sites.
  - `_build_entity_patterns`: 8 call sites.
  - `PostgresGraphRepository`: 8 call sites.
- `_load_gazetteer`, `_build_entity_patterns` and `find_entities_in_text` are defined in `nexus/nexus/index/graph_extractor.py`; `api.py` imports them, which is why tests patch them on `nexus.api`.
- `effective_read_scope` lives in `nexus/nexus/auth/scope.py`; one test file (`tests/test_answer_says_what_it_searched.py`) patches it on `nexus.api`. `packet_for_answer` is patched on `nexus.api` by two test files (`tests/test_answer_context.py`, `tests/test_the_search_can_read_its_own_text.py`).
- `test_answer_surfaces_share_the_seam.py` and `test_answer_backend_per_principal.py` contain no `monkeypatch.setattr(api, ...)` calls; `test_read_paths_use_the_read_clamp.py` contains 13.
- If a shared retrieval function imports these functions directly from their home modules, calls inside `api.py` will bypass the monkeypatches. Tests will execute against unpatched functions and attempt to reach live databases or real LLM providers.
- Neither A2A nor the CLI can import `nexus/nexus/api.py`. Importing `api.py` executes module-level side effects: it reads configuration files, configures CORS middleware, and mounts A2A sub-applications.
- Existing clamp testing is incomplete. `tests/test_read_paths_use_the_read_clamp.py` validates only `PATHS = ["/search", "/search/answer"]`. It omits `/search/answer/stream` and the A2A endpoint.

## 4. Design

### 4.1 Read scope: one helper

Type names in the signatures below (`ReadScope`, `AnswerPacket`, `SearchResult`) are illustrative; the implementation chooses them.

Read scope resolution for HTTP handlers is consolidated into a private helper function in `nexus/nexus/api.py`:

```python
def _resolve_read_scope(
    req: Any,
    principal: Principal,
) -> tuple[ReadScope, str, bool]:
    ...
```

The helper reads `effective_read_scope` from the `nexus.api` namespace at call time, so the existing patch keeps working. Only HTTP handlers use it. It is used by `/search`, `/search/answer`, `/search/answer/stream`, and `/search/explain`.

The helper performs the full resolution sequence:
1. Reads the requested tenant (`asked_tenant`) from the request.
2. Evaluates `effective_read_scope(principal, asked_tenant)`.
3. Determines user clearance from the principal.
4. Checks whether the target tenant falls outside the principal's authorized scope.
5. Emits a structured warning log if the access is out of scope.
6. Returns a tuple of `(scope, clearance, is_out_of_scope)`.

This helper replaces the duplicated preambles in `nexus/nexus/api.py` for `/search`, `/search/answer`, and `/search/answer/stream`. It is also adopted by `/search/explain`, ensuring `/search/explain` logs out-of-scope access identically to the other endpoints.

A2A does not take an HTTP request. It calls `effective_read_scope(principal, req_tenant, req_clearance)` directly (replacing `effective_scope` on its read path; the two ingest paths keep `effective_scope`) and emits the same out-of-scope warning log event as the HTTP helper. An A2A principal with multiple tenants configured in `read_tenants` can now read across its full authorized boundary.

### 4.2 Retrieval: one function, dependencies passed in

A new module is introduced at `nexus/nexus/search/answer_pipeline.py`. It provides a single entry point for answer retrieval:

```python
async def retrieve_for_answer(
    query,
    *,
    scope: ReadScope,
    route,
    top_k,
    deps: RetrievalDependencies,
    channels=None,
    search_opts=None,
    want_packet=True,
    skip_packet_on_zero_hits=False,
) -> Retrieval:
    ...
```

Parameters are handled as follows:
- `channels`: computed by the caller. HTTP callers compute them with `api._search_channels` and pass the rewritten query and channels; A2A and the CLI pass `None`, meaning no channel step, as today. `_search_channels` stays in `api.py`; the pipeline never imports it.
- `route`: the caller's route request (`req.route`; `"auto"` for A2A; the CLI option). The pipeline calls `deps.determine_route` with it.
- `top_k`: passed by each caller (A2A keeps 10).
- `search_opts`: a dict of the five HTTP-only `hybrid_search` arguments; `None` for A2A and the CLI, so they keep `hybrid_search`'s defaults as today.
- The packet is built unless `want_packet` is false, or `skip_packet_on_zero_hits` is true and there are no hits. HTTP answer paths and A2A use the defaults (always build). The CLI passes `want_packet=answer, skip_packet_on_zero_hits=True` (today's condition). `POST /search` passes `want_packet=False`. When no packet is built, `Retrieval.packet` is `None`.

The function executes the retrieval flow in a fixed sequence:
1. Performs entity extraction on the query text using `deps.find_entities_in_text`, `deps.load_gazetteer`, and `deps.build_entity_patterns`.
2. Determines the retrieval route using `deps.determine_route` with `route`.
3. Executes `deps.hybrid_search`. Each surface passes the arguments it passes today (14 on the HTTP answer paths, 9 on A2A and the CLI); an argument a surface does not pass keeps `hybrid_search`'s default. HTTP callers pass `search_opts`; A2A and the CLI pass `None`.
4. Constructs the reconciliation packet using `deps.packet_for_answer` unless `want_packet` is false, or `skip_packet_on_zero_hits` is true and there are no hits.

`retrieve_for_answer` returns a `Retrieval` dataclass containing:
- `search_result`: the raw result returned by `hybrid_search`.
- `packet`: the structured packet returned by `packet_for_answer`, or `None` when no packet is built.
- `channels`: the active search channels passed in by the caller.
- `route`: the selected search route.
- `timings`: the `timing_ms` dict `hybrid_search` already returns, passed through unchanged; `record_search` keeps reading what it reads today.

The module `nexus/nexus/search/answer_pipeline.py` imports no symbols from `nexus.api`. This rule prevents circular dependencies and eliminates import-time side effects.

To preserve test compatibility without modifying existing monkeypatch sites, **`deps` is a dataclass of the callables and services it uses**. `packet_for_answer` is injected so the two test files that patch it keep working. So the seam is held by the single call site plus the test, not by the type system. Its definition specifies all external operations:

```python
@dataclass(frozen=True)
class RetrievalDependencies:
    hybrid_search: Callable[..., Any]
    packet_for_answer: Callable[..., Any]
    find_entities_in_text: Callable[..., Any]
    load_gazetteer: Callable[..., Any]
    build_entity_patterns: Callable[..., Any]
    determine_route: Callable[..., Any]
    graph_repository: Any
    embedding_service: Any
    config: Any
```

Dependency binding follows caller context:
- Inside `nexus/nexus/api.py`, handlers construct `RetrievalDependencies` by resolving names directly from the `nexus.api` module scope at request time. For example, `deps.hybrid_search` is the module global `hybrid_search` read when the request is handled. If a unit test executes `monkeypatch.setattr(api, "hybrid_search", mock_search)`, the pipeline receives `mock_search`. Unmodified tests continue to intercept execution.
- In `nexus/nexus/a2a/server.py` and `nexus/nexus/cli.py`, handlers construct `RetrievalDependencies` using direct imports from underlying modules (`nexus.search.hybrid`, `nexus.search.reconcile`, `nexus.search.router`, `nexus.index.graph_extractor`, `nexus.repositories.graph`, `nexus.config`). Neither surface imports `nexus/nexus/api.py`. No surface gains a step. A2A and CLI `deps` always bind `nexus.search.reconcile.packet_for_answer`.

### 4.3 Evidence view: one shaping function for both HTTP answer paths

Evidence shaping logic is extracted from `nexus/nexus/llm/answer.py::generate_answer` into a reusable helper function located in `llm/answer.py`:

```python
def evidence_view(
    packet: AnswerPacket,
    search_result: SearchResult,
) -> EvidenceView:
    ...
```

The function returns an `EvidenceView` dataclass containing:
- `snippets`: list of evidence snippets with every marker field the answer path sends today (including `provenance_mark`, `labels` and `synthetic`).
- `provenance`: list of source document provenance mappings.
- `graph_findings`: the graph findings, observed edges among them.
- `n_stale`: the count of evidence snippets past their freshness TTL.

`evidence_view` unifies the dictionaries produced for provenance and graph edges by computing their field union:
- Each item in `provenance` includes both `approved_hash` and `doc_title`.
- Each observed graph edge includes both `calls` and `call_count`.
- No consumer loses access to its expected key name. The web frontend (`web/js/views/chat.js`) receives `call_count`. Existing clients expecting `calls` or `approved_hash` receive those keys unchanged.

`POST /search/answer/stream` replaces its inline shaping block with a direct call to `evidence_view`. The stream handler uses `EvidenceView` to populate the initial `evidence` SSE event. In addition, the stream's concluding `done` SSE event is expanded to include three fields currently omitted:
- `abstained`: boolean indicating if the model abstained.
- `abstain_reason`: reason string if the model abstained (`"no_evidence"` when `not packet.snippets`, otherwise `None`, computed by one shared helper used by both paths).
- `n_unknown_origin_time`: the count of hits whose origin time is unknown.

The `done` event does not gain `evidence_only`: the stream ignores that request flag, so sending it would describe a mode the stream does not run. Whether the stream should honour `evidence_only` is an open question (§8).

`generate_answer` continues to calculate `doc_debts` internally for compatibility. It does not export `doc_debts` through `EvidenceView`.

### 4.4 Surfaces

The callers comprise the four answer surfaces plus `POST /search` and `/search/explain`:

1. `POST /search/answer` (`nexus/nexus/api.py`):
   - Calls `_resolve_read_scope(req, principal)` to validate tenancy and clearance.
   - Computes search channels via `api._search_channels` and passes the rewritten query and channels.
   - Instantiates `RetrievalDependencies` from symbols in the local `nexus.api` module scope.
   - Passes `req.route`, `top_k`, and `search_opts` (dict of the five HTTP-only `hybrid_search` arguments).
   - Awaits `retrieve_for_answer`.
   - Calls `generate_answer` with the retrieved packet.
   - `generate_answer` delegates shaping to `evidence_view`.
   - Executes validation and records search metrics via `record_search`.

2. `POST /search/answer/stream` (`nexus/nexus/api.py`):
   - Calls `_resolve_read_scope(req, principal)` to validate tenancy and clearance.
   - Computes search channels via `api._search_channels` and passes rewritten query, channels, `req.route`, `top_k`, and `search_opts`.
   - Instantiates `RetrievalDependencies` from local `nexus.api` module scope symbols.
   - Awaits `retrieve_for_answer`.
   - Calls `evidence_view(retrieval.packet, retrieval.search_result)` to shape initial payload data.
   - Yields the `evidence` SSE event with shaped snippets, provenance, and graph findings.
   - Streams generated tokens.
   - Yields the final `done` SSE event containing complete metadata (`abstained`, `abstain_reason`, and `n_unknown_origin_time`).
   - Records search metrics via `record_search`.

3. A2A `_default_answer_fn` (`nexus/nexus/a2a/server.py`):
   - Calls `effective_read_scope(principal, req_tenant, req_clearance)` directly (replacing `effective_scope`) and emits the out-of-scope warning log event.
   - Instantiates `RetrievalDependencies` directly from source modules, avoiding any import of `nexus.api`.
   - Awaits `retrieve_for_answer` with `route="auto"`, `top_k=10`, `channels=None`, and `search_opts=None`.
   - Validates conversation history and then discards it, retaining current intentional behavior.
   - Runs generation and response formatting.
   - Records search metrics via `record_search`. A2A's backend choice stays as `SPEC-nexus-per-principal-answer-backend` set it.

4. CLI `query` command (`nexus/nexus/cli.py`):
   - Accepts `--tenant` parameter and applies hardcoded clearance `"INTERNAL"`.
   - Instantiates `RetrievalDependencies` directly from domain modules without importing `nexus.api`.
   - Always awaits `retrieve_for_answer` with the CLI route option, `channels=None`, `search_opts=None`, `want_packet=answer`, and `skip_packet_on_zero_hits=True`.
   - Always prints corpus, route, and hits, as today.
   - When `--answer` is given and there are hits, builds the packet and runs generation.
   - With zero hits, generation is skipped and no answer span row is written (today's behaviour; see §8).
   - Records search metrics via `record_search`.

5. `POST /search` (`nexus/nexus/api.py`):
   - Calls `_resolve_read_scope(req, principal)`.
   - Computes search channels via `api._search_channels`.
   - Calls `retrieve_for_answer(..., want_packet=False)`, so its front half is the same code.
   - Returns ranked search hits directly without invoking evidence shaping or text generation.
   - Records search metrics via `record_search`.

6. `/search/explain` (`nexus/nexus/api.py`):
   - Uses `_resolve_read_scope` only to validate tenancy, clearance, and log out-of-scope access.
   - Does not call `retrieve_for_answer`.

Each surface keeps its own `record_search` call where it is today. Consolidating telemetry is out of scope.

## 5. Compatibility

- Request schemas: Unchanged across all surfaces. Request parameters, headers, and JSON bodies accept identical schemas.
- Response schemas: Fully backward compatible. Fields are only added as a superset union:
  - Non-streaming `POST /search/answer` gains `doc_title` in its `provenance` records and `call_count` in its graph edge records.
  - Streaming `POST /search/answer/stream` gains `approved_hash` in its `provenance` records and `calls` in its graph edge records.
  - The stream `done` event gains `abstained`, `abstain_reason`, and `n_unknown_origin_time`.
- A2A read scope: A token whose `read_tenants` lists other tenants can read them over A2A after this change, as it already can over HTTP. No Nexus deployment is running, so no issued token changes behaviour in the field; the owner reviews `read_tenants` in principal config when a deployment is set up.
- Downstream HTTP clients: The MCP server and Slack bot consume `/search/answer`. Both rely on the presence of `synthetic` markers and `provenance_mark` attributes. Every key it has today is kept.
- Web UI: The frontend client at `web/js/views/chat.js` requires `call_count` on graph edge records. Preserving `call_count` across both HTTP endpoints prevents interface regressions.
- Debt tracking: `doc_debts` remains computed within `generate_answer`. It remains omitted from HTTP responses.

## 6. Testing

The test suite must be updated and extended to verify the unified architecture:

- Structural seam verification:
  - Update `tests/test_answer_surfaces_share_the_seam.py` and `tests/test_answer_backend_per_principal.py`.
  - The seam test walks `retrieve_for_answer` and asserts it calls `deps.packet_for_answer` at exactly one site.
  - It walks each surface and asserts it calls `retrieve_for_answer` and does not call `hybrid_search` or `packet_for_answer` itself.
  - A separate assertion checks that the A2A and CLI `deps` builders bind `nexus.search.reconcile.packet_for_answer`.
  - Mutation check mechanism: the test parses `answer_pipeline.py` with `ast`, removes the `packet_for_answer` call node, and runs the same walker on the modified tree; the walker must report a failure. It is an ordinary pytest case in the unit job.

- Response parity verification:
  - Add a new test comparing `/search/answer` and `/search/answer/stream`.
  - Verify that the union of keys emitted across the stream's `evidence` and `done` events is a superset of the keys returned in the `data` dictionary of `/search/answer`, minus a documented allowlist.
  - The parity allowlist is exactly `{"evidence_only"}`, written in the test with its reason (the stream ignores the flag). Any other missing key fails.
  - Verify that evidence snippet dictionaries emitted by both paths contain identical key sets.

- Read clamp verification:
  - Extend `tests/test_read_paths_use_the_read_clamp.py` by adding `/search/answer/stream` to `PATHS` (new cases; the 13 existing patch lines are not edited).
  - Add an A2A test case asserting that a token with `read_tenants` reads its whole read scope.
  - Add a negative A2A test case asserting that a tenant outside the token's `read_tenants` is refused.

- Argument-set verification:
  - Add an argument-set test that records the `hybrid_search` keyword names each surface passes (today 14 on the HTTP answer paths and 9 on A2A and the CLI; `POST /search` as it is) and fails on change.

- CLI verification:
  - Add a test verifying `query --answer` behavior when search returns zero hits. The test must assert current behavior (no answer span row written).

- Regression verification for monkeypatches:
  - Every existing test that patches `nexus.api` passes with its patch lines unchanged.

## 7. Acceptance

The implementation is complete when all of the following criteria are met:

1. Structural consolidation:
   - `POST /search`, `POST /search/answer`, `POST /search/answer/stream`, A2A `_default_answer_fn`, and CLI `query` reach `hybrid_search` only through `retrieve_for_answer`. Answer callers reach `packet_for_answer` exclusively through it.
   - `POST /search/answer` and `POST /search/answer/stream` shape evidence data exclusively through `evidence_view`.
   - `/search`, `/search/answer`, `/search/answer/stream`, and `/search/explain` evaluate tenant scope exclusively through `_resolve_read_scope`.

2. Verification of security clamps:
   - A2A reads with `effective_read_scope` and logs out-of-scope requests.
   - A2A tokens configured with `read_tenants` can search across their full tenant list.
   - `/search/explain` logs out-of-scope requests.

3. Test suite execution:
   - The updated `tests/test_answer_surfaces_share_the_seam.py` passes.
   - The new surface response parity test passes.
   - The extended `tests/test_read_paths_use_the_read_clamp.py` passes.
   - The negative A2A clamp test passes.
   - The argument-set test passes.
   - The full Nexus unit test and PostgreSQL test suites pass.
   - Every existing test that patches names on `nexus.api` passes with its patch lines unchanged.

Acceptance relies strictly on automated test execution. No live Nexus deployment is running today, so automated test suites form the sole acceptance gate.

## 8. Open questions

- Should the stream honour `evidence_only`?
- Should the CLI write an answer span row when `query --answer` returns zero search hits?
- Should `doc_debts` be exposed in the answer payload on any surface, or should its calculation be removed entirely from `generate_answer`?
- When should `_search_channels`, `_ranked`, and `_search_hit_to_dict` be moved out of `nexus/nexus/api.py` into a shared search utility module?
- How should the remaining out-of-scope architectural debt be scheduled? Specifically:
  - Consolidating the 22 locations executing graph SQL queries outside `nexus/nexus/repositories/graph.py`.
  - Converting `nexus/nexus/api.py` into an application factory to remove import-time side effects permanently.
