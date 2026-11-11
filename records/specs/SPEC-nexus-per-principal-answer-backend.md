---
id: SPEC-nexus-per-principal-answer-backend
type: spec
title: 'The answer backend is chosen per principal: an API key by default, the keyless
  bridge only for named identities'
status: approved
linked_adrs:
- ADR-0004
tags:
- nexus
- llm
- provider
- auth
date: '2026-11-11T17:41:05Z'
approved_by: LivingLikeKrillin
reviewed_at: '2026-11-11T18:32:44Z'
content_hash: sha256:1a6c85a5be82c8ec315d56e7c0ae0d20c9a20ac6017bde94f82bd547519dba47
---
# The answer backend is chosen per principal: an API key by default, the keyless bridge only for named identities

## 1. Goal

Today, a single Nexus process has exactly one answer backend. It is chosen at startup by the environment variable `NEXUS_LLM_PROVIDER`. The default value is `anthropic`, which routes requests through a paid Anthropic API key. The alternative value is `claude-code`, which routes requests through a keyless bridge that runs `claude -p` on a host under the developer's Claude subscription.

The goal is to let a single Nexus process answer different callers through different backends. The backend branches on the authenticated principal represented by the bearer token. Any caller exposed to the public, including anonymous callers and public tokens, must be answered through an API-key backend. The owner's own internal identities may be answered through the keyless bridge.

Only the path branches. Nothing else about answering changes. Retrieval, evidence assembly, prompt generation, citation and number verification, abstention, and signal emission remain identical regardless of the backend selected. The query rewrite used by `/search`, `/search/answer`, and `/search/answer/stream` calls the LLM only when the request carries conversation history; without history no rewrite LLM call is made. With history, two backends (or two calls to one backend) may rewrite differently, which can change the channels searched and therefore the evidence. So the claim that retrieval and evidence are identical holds for requests without history; with history only the deterministic stages after the rewrite are identical.

The bridge must not answer public callers due to Anthropic's subscription terms. Claude Code docs, "Legal and compliance" (https://code.claude.com/docs/en/legal-and-compliance), read 2026-11-12, state: "Anthropic does not permit third-party developers to offer Claude.ai login into their own applications, or to route requests through Free, Pro, Max, or Ultra plan credentials on behalf of their users." The page also says OAuth authentication "is designed to support ordinary use of Claude Code and other native Anthropic applications". Developers building products must use API keys instead.

## 2. Non-goals

- No new answer backends. The system will not add backends for Gemini answers, OpenAI, or Ollama. The only supported answer backends remain `anthropic` and `claude-code`. The existing Gemini backend stays vision-only.
- No changes to vision or ingest backend selection. The `vision_backend` argument and its resolution rules remain unchanged.
- No per-request choice by the caller. The JSON request body cannot pick a backend. Only server-side configuration bound to the principal's token can select a backend.
- No changes to the CLI. The command-line interface in `cli.py` has no principal and continues reading `NEXUS_LLM_PROVIDER` from the environment.
- No new rate limiting, cost caps, or anonymous public read paths in this specification. Those are separate work.
- No changes to what is recorded in `search_log`. The `search_log` schema stays unchanged. The model identifier and backend in `search_log` remain a separate, known gap. Runtime evidence is provided via structured logging instead.

## 3. What exists (verified 2026-11-12)

- `nexus/nexus/providers/llm.py`:
  `LLMService.__init__(model=None, api_key=None, pricing=None, vision_backend=None)` reads `NEXUS_LLM_PROVIDER`. If unset, the environment variable defaults to `anthropic`. The string `claude` is accepted as an alias that resolves to `claude-code` when `NEXUS_LLM_BRIDGE_URL` is set, and to `anthropic` otherwise. The constructor instantiates `_AnthropicBackend` or `_ClaudeCodeBackend`. It raises `ValueError` on an unknown provider string. It sets `configured` based on the instantiated backend: `_AnthropicBackend` requires an API key to be present, and `_ClaudeCodeBackend` requires `NEXUS_LLM_BRIDGE_URL` to be set.

- `nexus/nexus/auth/principal.py`:
  `Principal` is a frozen dataclass with `name`, `tenant`, `clearance`, `capabilities`, and `read_tenants`. The function `resolve_principal()` constructs a `Principal` from entries under `auth.principals[]` in `config.yaml` using constant-time matching on `token_sha256`.

- Other constructors of `Principal`:
  `nexus/nexus/auth/deps.py` constructs `ANONYMOUS` for permissive mode (`PUBLIC`). The same file constructs Cloudflare Access identities. A2A principals do not come from `auth.principals`: `A2AConfig` builds them from `a2a.principals` plus an optional single env token (`NEXUS_A2A_TOKEN`), and `resolve_a2a_principal` passes them to the same `resolve_principal`. A2A has no startup validator today. A2A is off by default.

- `nexus/nexus/auth/config.py`:
  `AuthConfig.validate_startup()` iterates over `self.principals` during boot and raises `RuntimeError` on invalid entries. It currently validates `read_tenants`.

- Answer-backend construction sites:
  The construction sites were re-checked on 2026-11-12. Besides the five listed, `LLMService` is constructed only by the vision/ingest path (`ingest/vision.py`, via `vision_backend`, not an answer surface). The MCP server (`nexus/nexus/mcp/server.py`) is an HTTP client of `/search` and `/search/answer`, so it is covered by those sites and by the token it sends. Nexus instantiates `LLMService` across five answer call sites:
  1. `api.py` in `/search` for query rewriting via `_search_channels(req, LLMService())`.
  2. `api.py` in `/search/answer` via `llm_svc = LLMService()`.
  3. `api.py` in `/search/answer/stream` via `llm_svc = LLMService()`.
  4. `a2a/server.py` via `llm_svc = LLMService()`.
  5. `cli.py` via `llm_svc = LLMService()`.
  Every site except `cli.py` already has a resolved `Principal` in scope.

## 4. Design

### 4.1 A principal may name its answer backend

Add an optional field `llm_provider: str | None = None` to `Principal` in `nexus/nexus/auth/principal.py`. Add an optional boolean field `owner: bool = False` to principal config entries and to `Principal`.

A value of `None` means "use the process default" (`NEXUS_LLM_PROVIDER`). This preserves current behavior so every existing token behaves exactly as before.

The function `resolve_principal()` copies `llm_provider` and `owner` from the matching `config.yaml` entry under `auth.principals[]`. If omitted, `llm_provider` defaults to `None` and `owner` defaults to `False`.

The `ANONYMOUS` principal (permissive mode) and Cloudflare Access identities built in `nexus/nexus/auth/deps.py` leave `llm_provider` set to `None` and can never be owner (`owner: false`). The owner reaching Nexus through Access therefore cannot use the bridge; the owner uses a bearer token for that. This is a deliberate limit.

Define the "resolved backend" of a principal as its `llm_provider` if set, else the process default from `NEXUS_LLM_PROVIDER`.

**Load-bearing rule: any principal whose resolved backend is `claude-code` must have `owner: true`; otherwise Nexus refuses to start, naming the principal.**

Consequence: if the process default resolves to `claude-code`, startup is refused while permissive mode is on or Access is enabled, and every configured token must carry `owner: true`. Example: a team-facing token such as the existing `slack-bot` principal is not an owner, so a deployment with default `claude-code` that still lists it refuses to start — that is intended.

A configuration comment stays in `config.yaml` next to `principals` as documentation. It states that `llm_provider: claude-code` and `owner: true` may be set only on identities used by the subscription holder themself, in accordance with Anthropic's subscription terms. The YAML comment stays as documentation but is no longer the guard.

### 4.2 `LLMService` takes the choice as an argument

`LLMService.__init__` in `nexus/nexus/providers/llm.py` gains a keyword argument:
`provider: str | None = None`.

Values of `llm_provider` are normalised by a single function used by both validation and `LLMService`: strip surrounding whitespace, lowercase. An empty string is an error, not "unset" (YAML `null` / absent means unset).

When `provider` is provided, `LLMService` normalises it and uses that value instead of reading `NEXUS_LLM_PROVIDER`. When `provider` is `None`, the constructor falls back to `NEXUS_LLM_PROVIDER`.

In principal config only `anthropic` and `claude-code` are accepted; the alias `claude` is rejected there, because it resolves to a different backend depending on whether `NEXUS_LLM_BRIDGE_URL` is set, which would be a silent backend switch. The alias keeps its current meaning only in the `NEXUS_LLM_PROVIDER` env var, for backward compatibility; the owner rule uses its resolved value.

Any unknown provider string raises `ValueError`.

The `provider` argument does not affect `vision_backend`. The `vision_backend` parameter retains priority as it does today.

### 4.3 The call sites pass the principal's choice

The four call sites with a principal in scope pass `provider=principal.llm_provider`:
1. `api.py` in `/search`: The query-rewrite call becomes `_search_channels(req, LLMService(provider=principal.llm_provider))`. The query rewrite must branch to prevent public queries from reaching the bridge.
2. `api.py` in `/search/answer`: `llm_svc = LLMService(provider=principal.llm_provider)`.
3. `api.py` in `/search/answer/stream`: `llm_svc = LLMService(provider=principal.llm_provider)`.
4. `a2a/server.py`: `llm_svc = LLMService(provider=principal.llm_provider)`.

The CLI site in `cli.py` remains untouched (`llm_svc = LLMService()`) and continues reading `NEXUS_LLM_PROVIDER`.

The default direction is the safe one: a deployment that serves the public sets `NEXUS_LLM_PROVIDER=anthropic`. The bridge is used only for principals whose configuration entry explicitly sets `llm_provider: claude-code`. Nothing that lacks the field can reach the bridge unless the operator also set the process default to `claude-code`.

### 4.4 Configuration is checked at startup

A2A principals do not come from `auth.principals`: `A2AConfig` builds them from `a2a.principals` plus an optional single env token (`NEXUS_A2A_TOKEN`), and `resolve_a2a_principal` passes them to the same `resolve_principal`. A2A has no startup validator today. The env-token A2A principal has no `owner` field, so it is never owner. A2A is off by default.

The owner/provider check is one function used by both `AuthConfig.validate_startup()` and A2A configuration loading, so the two cannot diverge.

The shared validator normalises provider strings using the single normalisation function (strip whitespace, lowercase). An empty string raises `RuntimeError`. In principal config, only `anthropic` and `claude-code` are accepted; the alias `claude` or any unknown value raises `RuntimeError` and names the principal.

The validator determines the resolved backend of each principal. It enforces the load-bearing owner rule: any principal whose resolved backend is `claude-code` must have `owner: true`; otherwise Nexus refuses to start, naming the principal.

If the process default resolves to `claude-code`, startup is refused while permissive mode is on, Access is enabled, or any configured token (such as `slack-bot` or an A2A token) lacks `owner: true`.

A principal configured with `llm_provider: claude-code` while `NEXUS_LLM_BRIDGE_URL` is unset is not a boot error. It surfaces as the existing unconfigured path at call time. This was decided to keep startup independent of the bridge process, which may start after Nexus boots.

### 4.5 Runtime structured logging

Each answer request emits one structured log event (structlog) carrying the principal name and the resolved backend. The `search_log` schema stays unchanged (model id and backend in `search_log` remain a separate, known gap). This gives after-the-fact evidence that no non-owner was answered by the bridge.

## 5. Relation to SPEC-nexus-claude-code-llm-dev-backend

`SPEC-nexus-claude-code-llm-dev-backend` was approved on 2026-07-11. Section 2 (Non-goals) of that specification stated that the bridge is "a dev convenience, not a server backend," that "Team/prod deploys keep `NEXUS_LLM_PROVIDER=anthropic`," and that "Changing the four call sites" was a non-goal because backend selection occurred inside `LLMService`.

This specification succeeds `SPEC-nexus-claude-code-llm-dev-backend` on those two points only:
1. It modifies the call sites to pass the principal's choice.
2. It allows a server process to route requests to the bridge for explicitly named identities.

The default for public and team deployments remains `anthropic`, consistent with the predecessor's intent.

The predecessor specification's body is stamped and is not edited. There is no `retractions.yaml` entry. That mechanism withdraws a claim later proven wrong; here the scope was deliberately widened, so this successor SPEC is the record.

ADR-0004 §5 says A2A stays minimal and is not extended until a real agent pulls it. This SPEC changes one argument in `a2a/server.py` so that the owner/provider invariant holds on every answer surface; it adds no A2A capability.

The security properties established in Section 5 of the predecessor specification remain unchanged. The bridge must not become a vector for arbitrary host execution, and the authentication token between the application and the bridge remains required.

## 6. Error handling

- Unknown or invalid `llm_provider` in configuration: `validate_startup()` and A2A configuration loading refuse to boot and name the principal if `llm_provider` is an empty string, an unknown string, or the rejected alias `claude`.
- Owner rule violations at startup: If any principal has a resolved backend of `claude-code` and lacks `owner: true`, validation raises `RuntimeError` naming the principal. If the process default resolves to `claude-code`, startup is refused if permissive mode is enabled, if Cloudflare Access is enabled, or if any principal in configuration (including `slack-bot` or an A2A token) lacks `owner: true`.
- Unconfigured backend at call time: If a principal selects `anthropic` without an API key, or `claude-code` without `NEXUS_LLM_BRIDGE_URL`, `LLMService.configured` is `False`. The existing unconfigured provider path applies, triggering `llm_failed`. Evidence and citations are still returned to the caller.
- There is no silent fallback between backends: if a backend is unconfigured or fails, Nexus must not fall back to the alternative backend. Falling back from a public principal's failing API-key path to the keyless bridge would breach Anthropic's subscription terms and violate the core invariant of this specification.

## 7. Testing

The test suite must cover:
- Configuration parsing: `resolve_principal()` populates `llm_provider` and `owner` from config. If fields are omitted, it sets `llm_provider` to `None` and `owner` to `False`.
- Normalisation and validation: The shared normalisation function strips surrounding whitespace and lowercases provider strings. Empty strings raise errors. The alias `claude` is rejected in principal config.
- Provider selection in `LLMService`: `LLMService(provider="anthropic")` and `LLMService(provider="claude-code")` instantiate their respective backends regardless of `NEXUS_LLM_PROVIDER`. `LLMService(provider=None)` falls back to `NEXUS_LLM_PROVIDER`. An unknown string or empty string raises `ValueError`.
- Call site wiring: A structural test counts names reachable from each surface's code object including nested functions (`co_names`), the same method as `tests/test_answer_surfaces_share_the_seam.py`, not a text grep. The test verifies that all four principal-aware answer sites pass `provider=principal.llm_provider`. Construction sites were re-checked on 2026-11-12: besides the five answer sites, `LLMService` is constructed only by the vision/ingest path (`ingest/vision.py`, via `vision_backend`, not an answer surface). The MCP server (`nexus/nexus/mcp/server.py`) is an HTTP client of `/search` and `/search/answer`, covered by those sites and by the token it sends.
- Safe routing defaults and owner rule: When `NEXUS_LLM_PROVIDER=anthropic`, a request from a principal without `llm_provider` never constructs `_ClaudeCodeBackend`. A request from a principal with `llm_provider: claude-code` and `owner: true` constructs `_ClaudeCodeBackend`. Validation raises `RuntimeError` and names the principal when resolved backend is `claude-code` without `owner: true`. Tests verify startup refusal when default is `claude-code` and permissive mode is active, Access is enabled, or a token lacks `owner: true` (e.g. `slack-bot`).
- A2A configuration: Tests verify that `AuthConfig.validate_startup()` and A2A configuration loading use the exact same validation function. Tests verify that the env-token principal (`NEXUS_A2A_TOKEN`) has no `owner` field, is never owner, and refuses startup if the resolved default is `claude-code`.
- In-process dual-principal test: An in-process test where one process, with `NEXUS_LLM_PROVIDER=anthropic`, serves two principals in sequence — an owner with `llm_provider: claude-code` against a stub bridge (the bridge transport is already injectable, `_bridge_transport`) and one without the field against a stub Anthropic client — checking that each request constructs its own backend with no shared module-level backend state, and that both get the same evidence packet for the same question without history.
- Runtime structured logging: Tests assert that each answer request emits a structlog event carrying the principal name and the resolved backend.
- No fallback behavior: A request using `llm_provider: claude-code` when `NEXUS_LLM_BRIDGE_URL` is unset enters the unconfigured path (`llm_failed`). It never falls back to `_AnthropicBackend`.

## 8. Acceptance

With `NEXUS_LLM_PROVIDER=anthropic`, a single running Nexus process must answer a token configured with `llm_provider: claude-code` through the bridge and a token without the field through the API key, within the same minute, returning identical evidence packets for the same query.

The identical-evidence criterion applies to a question sent without history. Query rewriting calls the LLM only when the request carries conversation history; without history no rewrite LLM call is made, ensuring identical retrieval and evidence assembly across backends.

This acceptance criterion is not verifiable today because no Nexus deployment is currently running. Passing the unit and structural tests detailed in Section 7 serves as the acceptance gate until a deployment is available.

## 9. Limits

- Bridge topology: The bridge listens on the developer host, so only a Nexus process that can reach that host (same machine, or the container via `host.docker.internal`) can use it; the bridge token is supplied to the Nexus process by env as today.
- Bridge concurrency: Bridge concurrency defaults to 1 (`NEXUS_LLM_BRIDGE_CONCURRENCY`), so owner requests queue behind one another; public requests do not use the bridge and are unaffected.
- Operator assertion: "Owner" is a claim the operator makes in config; Nexus cannot verify who holds a token.
- Cloudflare Access: Access identities keep `llm_provider` unset and can never be owner. The owner reaching Nexus through Access therefore cannot use the bridge; the owner uses a bearer token for that. This is a deliberate limit.
