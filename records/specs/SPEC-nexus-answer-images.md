---
id: SPEC-nexus-answer-images
type: spec
title: 'Images in and out of the answer: a caller may attach one image, and a machine-read
  citation can show the image it was read from'
status: in_review
linked_adrs:
- ADR-0004
- ADR-0008
- ADR-0010
tags:
- nexus
- answer
- vision
- web
date: '2026-11-13T05:48:30Z'
---
# Images in and out of the answer: a caller may attach one image, and a machine-read citation can show the image it was read from

## Backstop record

```yaml
backstop:
- row: adr-0008-retrieval-stack
  reread: proposed 2026-11-13 — this SPEC adds no search channel, index backend, tokenizer, embedding model or connector; text read from an attached image reaches search only through the existing `search_text` field; the image route reuses the existing Notion source's block read at request time and adds no new source or connector.
  clause: none
  ruling: does-not-fire
  declared_by: LivingLikeKrillin
  declared_at: '2026-11-13'
  reason: >-
    Reading an attached image to text and passing part of it through an existing search field does not widen the retrieval stack. The owner confirms this ruling when approving.
```

## 1. Goal

This specification defines two capabilities for the chatbot answer paths (`POST /search/answer` and `POST /search/answer/stream`):
- A caller attaches one image to a question (for example a screenshot: "what does this setting mean?"), and the answer uses what the image shows.
- When an answer cites a chunk whose text was machine-read from an image at ingest (`provenance_tier = machine_read`), the web UI can show that original image next to the citation.

The answer still comes only from corpus evidence. **An attached image is the caller's material, not evidence: it is never cited, and numbers that appear only in it are reported as coming from the caller, not from the corpus.**

## 2. Non-goals

- No audio, video, PDF or multi-image attachments.
- No image embeddings and no image-similarity search. The embedding model stays text-only (`nomic-embed-text`). There is no new search channel.
- The answer model still receives text only. This specification does not add an image-capable answer call to any backend, and does not change `/v1/generate` on the keyless bridge.
- No change to ingest-time extraction (`NEXUS_VISION`, `vision_store`, the marker format, or the durable `vision_extractions` store).
- Nexus does not start storing image bytes (see §5).
- No attachments on Slack, MCP or A2A in this specification.
- No prompt-injection detector. None exists today and this specification does not build one.

## 3. What exists (verified 2026-11-13)

All paths are under `nexus/nexus/`.

- Request models inherit `RequestModel` with `extra="forbid"` (`api.py:239-260`), so an unknown field returns a 422. `AnswerRequest` (`api.py:313-392`) fields are all strings, lists or booleans; none can carry an image. `SearchAnswerRequest` adds only `evidence_only`. The stream endpoint takes plain `AnswerRequest`.
- `answer_context: str | None` (max `ANSWER_CONTEXT_MAX = 8000` characters, `api.py:236`) is requester-supplied material. It goes only into the answer prompt (`llm/prompts.py` `ANSWER_CONTEXT_HEADER`, `ANSWER_CONTEXT_RULE`, `ANSWER_CONTEXT_CLOSING`, and `build_user_prompt`), never into search, the rewriter, the sufficiency judge, or query-text retention. Only its length and hash are recorded (migration 046). The response carries `answer_context_len`.
- `search_text: str | None` is read by the search side instead of `query`. When given, the rewriter does not run. The response carries `search_text_len`. `search_text` is recorded only as `search_text_len` and `search_text_sha256` (`search/signals.py:153-157`). Query-text retention stores `req.query`, not `search_text` (`api.py:952`). So image text that reaches search through `search_text` is not stored there.
- `validate_numbers(answer_text, evidence_text, query="", context="")` (`llm/numbers.py:71`) reports each significant number with `grounded` and `found_in` from `SOURCES = ("evidence", "query", "context")`.
- No request body size limit exists: the only middleware is CORS (`api.py:1948`), and uvicorn runs without limit flags. History is capped (`MAX_TURNS = 8`, `MAX_BYTES = 8 * 1024`, returning 413 when exceeded).
- Image reading exists for ingest only: `ingest/vision.py::read_image(data, media_type, llm_svc, usage_out=None) -> Extraction` sends exactly one image, with no tools and no filesystem access, through `vision_extract` on the vision backend (`vision.vision_service()`, which maps the vision model to a backend through `VISION_BACKENDS`: the default `DEFAULT_VISION_MODEL = "gemini-3.6-flash"` maps to `_GeminiBackend`, and the models mapped to `claude` go through the keyless bridge's `/v1/vision` when `NEXUS_LLM_BRIDGE_URL` is set). It strips injected markers (`strip_markers`) and caps output (`MAX_OUTPUT_TOKENS = 4096`, `MAX_EXTRACTED_CHARS = 20000`). `extractor_identity()` is `{model}/{prompt_sha}`. Backends accept any media type; there is no allowlist.
- `ingest/scanner.py::scan_content(content, pii_patterns)` is the regex PII scan (`aws_key`, `jwt`, `credit_card`, `korean_ssn`) that ingest runs on extracted image text before storing it.
- Ingest-time vision writes a marker into machine-read chunks: `![](){: derived=vision extractor=<model/prompt_sha> img=<sha256[:16]> }` (`vision.build_block`). The unique index `idx_vision_handle` is on `(tenant, left(image_sha256, 16), extractor_identity)` (migration 016). `ingest/vision_source.py::resolve_source(tenant, chunk_text)` turns such a chunk into `SourceRef(source_uri, block_id, image_sha256, extractor_identity)`, or `Unresolvable(reason)`, or `None` for authored chunks. It raises `AmbiguousHandle` rather than choosing between two rows. Today it is called only from tests and `scripts/vision_roundtrip_probe.py`, which re-fetches the Notion block, gets a fresh signed URL, and checks that the bytes hash matches `image_sha256` (3 / 3 on the live corpus, SPEC-nexus-vision-source-ref). The Notion source reads its token from `NOTION_TOKEN`.
- No HTTP endpoint serves an image or resolves a citation to one. Image bytes are not stored anywhere (table `vision_extractions` holds tenant, sha256, extractor identity, text, error, truncated, block id, source uri).
- Citations sent to clients carry `{title, section, verified, provenance_tier, provenance_mark}`; evidence snippets carry `provenance_tier`, `provenance_mark`, `source_uri` among others (`llm/answer.py::evidence_view`). The web UI (`web/js/views/chat.js`) shows citation chips and the mark as text; it renders no images. The web UI authenticates with an `Authorization: Bearer` header (`web/js/api.js`). The chat input is a plain `<textarea>` with no paste or drop handling; `web/js/api.js::streamAnswer` sends `query`, `history`, `top_k`, `route`, `classification_max`, `tenant`.
- The web UI is served by the same FastAPI app (`/` and `/static`); no Content-Security-Policy is set.
- Slack (`slack/bot.py`, `slack/formatter.py`) handles text mentions and DMs only; MCP `nexus_answer` returns a string; A2A reads only text parts.
- Parity rule: every `/search/answer` response key must also appear in the stream's `evidence` or `done` payload (`tests/test_the_stream_sends_what_the_answer_sends.py`).

## 4. Design

This section covers the attachment extraction flow, prompt and search placement, guardrails, citation image resolution, and client interfaces.

### 4.1 One attached image, read to text before anything else

`AnswerRequest` gains a new optional field: `image: {media_type: str, data: str}`, where `data` is base64. Because `SearchAnswerRequest` inherits `AnswerRequest`, both `POST /search/answer` and `POST /search/answer/stream` accept it. An absent `image` field preserves today's behaviour, byte for byte.

Attachments get their own reader setting, `NEXUS_ATTACHMENT_VISION_MODEL`, mapped through the same `VISION_BACKENDS` table. If unset, attachments are refused with 503, not falling back to the ingest model. `vision_model()` and the ingest `extractor_identity()` are untouched, so switching the attachment reader never re-keys ingest.

The server decodes the base64 string and calls the existing `read_image` function using the backend resolved from `NEXUS_ATTACHMENT_VISION_MODEL`. It reuses the exact reader, prompt, and constraints from ingest: one image, no tools, and no filesystem access. Nothing new is built for reading images.

The extracted text is then put through `scan_content` with the configured `pii_patterns`. This enforces the same processing order as ingest: read, then scan, then use.

Neither the image bytes nor the extracted text are stored. Invariant: no retention path receives the image text: search log, query-text retention, rewrite record, stage spans. The search log records only `image_sha256`, the media type, the extracted character length, and the extractor identity. This is implemented via a new database migration adding nullable columns, matching what migration 046 did for `answer_context`.

The repository forbids paid calls in development runs. A development run must set `NEXUS_ATTACHMENT_VISION_MODEL` to a vision model mapped to `claude` with the keyless bridge configured. Tests use a test double and make no call at all.

### 4.2 Where the attachment's text goes

On the answer path, the extracted text enters the answer prompt as caller material. In the prompt, the image text has its own labelled block stating it was machine-read from the caller's image, separate from `answer_context`. If the caller also sent `answer_context`, both appear in the prompt. Machine-read caller material is kept apart from typed caller material. The extracted text is never added to the evidence packet and cannot be cited. Evidence formatting and citation verification remain unchanged.

For numeric validation, `validate_numbers` takes `attachment` as its own argument, so `answer_context` and image text are checked separately and neither replaces the other. `validate_numbers` gains a fourth source, `attachment`. A number found only in the image text reports `found_in = "attachment"`, never `found_in = "context"` or `found_in = "evidence"`.

On the search path, if the caller did not supply `search_text`, search reads `query` followed by the first portion of the extracted image text, capped (500 characters proposed), through the existing `search_text` path. If the caller supplied `search_text`, the image text does not touch search. This reuses the existing field rather than adding a new search channel.

The query rewriter does not run when the image text is used for search. This follows the existing rule applied to `search_text`.

The response gains an `attachment` field containing `{media_type, image_sha256, extracted_chars, truncated, extractor}`, or `null` when no image was provided. By the parity rule, the stream endpoint sends this identical object in its `done` payload.

The `prompt_version` string is updated because the answer prompt gains a labelled block.

### 4.3 Limits and refusals

A request may contain at most one image. Allowed media types are `image/png`, `image/jpeg`, `image/webp`, and `image/gif`. Any other media type returns 422.

A size cap applies to decoded image bytes (5 MiB proposed). An image exceeding this cap returns 413. The server never silently downscales or crops an oversized image.

The request body cap is enforced on bytes read, not on the header. A small wrapper on the two answer routes counts body bytes as they arrive and stops with 413 at the cap, with or without `Content-Length`. A declared `Content-Length` over the cap is rejected before reading.

When `NEXUS_ATTACHMENT_VISION_MODEL` is unset, requests with attachments are refused with 503. If `read_image` returns an error, the request fails with 502. If `read_image` yields empty text, the request fails with 422 indicating nothing readable was found. The server never silently answers without the image, as that would mislead the caller into thinking the image was used.

If `scan_content` flags a PII pattern in the extracted text, the request is refused with 422, explicitly naming the matched pattern types. This adheres to the repository rule of refusing rather than silently cutting content.

On the stream route, decoding, `read_image` and `scan_content` finish before the response starts, so 413, 422, 502 and 503 are real HTTP statuses.

Clearance and tenant scope remain unchanged. The attached image confers no additional read permissions.

### 4.4 A machine-read citation can show its image

A new route is added: `GET /evidence/image/{handle}?tenant=<t>`, where `handle` is the 16-character image handle from the chunk marker.

Invariant: the image is served only if the principal can read at least one chunk in tenant `<t>` whose marker carries the handle, and the check runs over all such chunks, not one picked chunk. The bytes are identical for every chunk carrying the handle, so a principal who can read one of them already sees text read from those bytes; serving the image discloses nothing beyond that chunk. If the principal cannot read at least one such chunk, the endpoint returns 404.

When no Notion token is configured (`NOTION_TOKEN`, the variable the Notion source reads), the route returns 503 with "source resolution not configured". Concurrent requests for the same handle share one upstream fetch. Upstream work is bounded by a per-process limit (proposed 4) and a timeout (proposed 10 seconds), over which the route returns 503 with a retry hint. A rate limit per principal is not added.

The route resolves the chunk with `resolve_source`. It reuses the existing Notion source's block read at request time to obtain a fresh signed URL, downloads the image bytes, and computes their sha256 hash, adding no new source or connector. These steps reproduce `scripts/vision_roundtrip_probe.py`.

The hash check runs first. The computed sha256 hash is checked against the stored `image_sha256`:
- On a match, the route sniffs the downloaded bytes against the four allowed signatures (PNG, JPEG, WebP, GIF) and serves the sniffed type with `Cache-Control: private, max-age=300`. The media type is not stored and is not taken from the upstream `Content-Type`. Sniffing only ever sees the bytes that were read. Downloaded bytes that match none of the allowed signatures return 502. Nexus does not write the image bytes to disk or the database.
- On a mismatch, the endpoint returns 409 with "the image changed since it was read". The citation points at text read from an image that no longer exists in that form, and the reader must be told.
- If `resolve_source` returns `Unresolvable`, the endpoint returns 404 with the reason.
- A second row for one handle is prevented by the unique index `idx_vision_handle` on `(tenant, left(image_sha256, 16), extractor_identity)` (migration 016), so a 64-bit collision fails at ingest rather than at view time. `AmbiguousHandle` at view time therefore means the index is missing or broken. The endpoint logs the error and returns 500 telling the reader "the image reference is ambiguous; it cannot be shown".
- If the upstream source fetch fails, the endpoint returns 502. Missing resources and upstream fetch failures are never merged.

Evidence snippets with `provenance_tier = machine_read` gain an `image_handle` field containing the 16-character string, so clients do not parse the marker. Citations for these chunks receive the same field. Authored chunks carry `null`.

Today, only Notion-sourced images can be resolved. Other sources return 404 with "no resolvable source".

### 4.5 Surfaces

In the web UI (`web/js/views/chat.js` and `web/js/api.js`):
- The chat input accepts one pasted or dropped image file, displaying a preview with a removal button.
- `web/js/api.js::streamAnswer` sends the payload with the new `image` field.
- Citations and evidence snippets with an `image_handle` display a thumbnail loaded lazily from `/evidence/image/{handle}?tenant=<t>`. Because `web/js/api.js` authenticates with an `Authorization: Bearer` header, which an `<img src>` request does not send, thumbnails are fetched with the same header, turned into a blob and shown through an object URL. The existing machine-read provenance mark remains visible beside the thumbnail.
- If thumbnail loading fails, the UI displays the returned reason text (such as "source resolution not configured" when `NOTION_TOKEN` is unset) instead of a broken image icon.

The Content-Security-Policy header is set only on the web UI routes (`/` and `/static`), not app-wide. The policy is defined once, by one helper shared with SPEC-nexus-answer-visuals, setting the exact full policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; font-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'`.

Both `POST /search/answer` and `POST /search/answer/stream` accept `image`. Slack (`slack/bot.py`, `slack/formatter.py`), MCP (`nexus_answer`), and A2A do not send attachments, and their outputs do not gain images. Returning images through MCP in the future is out of scope.

## 5. Relation to ADR-0004 and ADR-0010

ADR-0004 fixes Nexus as an index, not a store. ADR-0010 §3.1 relies on that principle ("it does not keep the bytes") and establishes the re-resolvable reference as the recourse for machine-read text. Section 4.4 makes that recourse visible: it fetches image bytes dynamically at view time and retains nothing in Nexus storage. Neither ADR changes.

ADR-0010 §4 requires the provenance tier to survive every surface Nexus controls. The web UI displays the thumbnail next to the existing machine-read mark, never in place of it.

ADR-0010 §6 limits the vision reader to one image, with no tools and no filesystem access. Section 4.1 reuses that reader unchanged, applying the same constraints to caller attachments. Injected text inside an attached image can steer the extracted text, but it cannot make the reader execute tools or access the filesystem. Machine-read caller material is kept apart from typed caller material. In the prompt, the image text has its own labelled block stating it was machine-read from the caller's image, separate from `answer_context`.

Text extracted from an attached image is not assigned a provenance tier. It is never stored as a chunk and is never treated as corpus evidence.

## 6. Error handling

All error responses use the shape the API already returns through FastAPI's `HTTPException`: `{"detail": "<reason>"}`. The 500 case goes through the existing internal-error helper, which returns `internal error (ref …)` and logs the cause. On `POST /search/answer/stream`, decoding, `read_image`, and `scan_content` finish before the response starts, so 413, 422, 502, and 503 return as real HTTP status codes.

For `GET /evidence/image/{handle}`, **the image is served only if the principal can read at least one chunk in that tenant whose marker carries the handle, and the check runs over all such chunks, not one picked chunk**. The bytes are identical for every chunk carrying the handle, so a principal who can read one of them already sees text read from those bytes; serving the image discloses nothing beyond that chunk. Otherwise, the route returns 404.

Concurrent requests for the same handle share one upstream fetch. Upstream work is bounded by a per-process limit (proposed 4) and a timeout (proposed 10 seconds), over which the route returns 503 with a retry hint. When no Notion token is configured (`NOTION_TOKEN`, the variable the Notion source reads), the route returns 503 ("source resolution not configured") and the UI shows that text. A rate limit per principal is not added here.

The table below lists the HTTP status codes, conditions, and routes:

| HTTP Status | Condition | Endpoint |
| :--- | :--- | :--- |
| 404 Not Found | Principal cannot read at least one chunk in that tenant whose marker carries the handle (checked across all such chunks), chunk is `Unresolvable`, or source is not Notion | `GET /evidence/image/{handle}` |
| 409 Conflict | Image hash does not match stored `image_sha256` ("the image changed since it was read") | `GET /evidence/image/{handle}` |
| 413 Payload Too Large | Declared `Content-Length` over cap rejected before reading, body byte count via route wrapper reaches cap (with or without `Content-Length`), or decoded bytes exceed cap (5 MiB proposed) | `POST /search/answer`, `POST /search/answer/stream` |
| 422 Unprocessable Entity | Media type is not `image/png`, `image/jpeg`, `image/webp`, or `image/gif` | `POST /search/answer`, `POST /search/answer/stream` |
| 422 Unprocessable Entity | `read_image` returns empty text ("nothing readable") | `POST /search/answer`, `POST /search/answer/stream` |
| 422 Unprocessable Entity | `scan_content` flags PII patterns in extracted text, naming pattern types | `POST /search/answer`, `POST /search/answer/stream` |
| 500 Internal Server Error | `resolve_source` raises `AmbiguousHandle` (unique index missing or broken; logged, reader told "the image reference is ambiguous; it cannot be shown") | `GET /evidence/image/{handle}` |
| 502 Bad Gateway | Vision backend fails during `read_image` | `POST /search/answer`, `POST /search/answer/stream` |
| 502 Bad Gateway | Upstream fetch of source Notion block or signed URL fails | `GET /evidence/image/{handle}` |
| 502 Bad Gateway | Downloaded bytes match no allowed image signature (PNG, JPEG, WebP, GIF) | `GET /evidence/image/{handle}` |
| 503 Service Unavailable | Attachment reader not configured (`NEXUS_ATTACHMENT_VISION_MODEL` unset) | `POST /search/answer`, `POST /search/answer/stream` |
| 503 Service Unavailable | Source resolution not configured (no `NOTION_TOKEN`; "source resolution not configured") | `GET /evidence/image/{handle}` |
| 503 Service Unavailable | Upstream concurrency limit (proposed 4) or timeout (proposed 10 seconds) reached (returns retry hint) | `GET /evidence/image/{handle}` |

## 7. Testing

All tests run without paid API calls. The vision backend is replaced with a test double across all automated test suites.

- Absent `image`: Golden tests verify that the generated prompt and executed SQL remain byte-identical to current behaviour, matching existing `answer_context` golden tests.
- Attached image processing: Tests verify that `read_image` is called once with exactly one image. Extracted text is verified to enter its own labelled prompt block stating it was machine-read from the caller's image, separate from `answer_context`, and not the evidence packet.
- Attachment path security: Tests on the attachment path verify that the request it sends has no tool definitions (Anthropic backend), the bridge call uses `/v1/vision` with the argv closed by `_DOORS_CLOSED`, and the reader receives bytes, never a path.
- Numeric validation: `validate_numbers` takes `attachment` as its own argument, so `answer_context` and image text are checked separately and neither replaces the other. A test verifies that a number present only in the image text reports `found_in = "attachment"`, never `found_in = "context"` or `found_in = "evidence"`. Extracted image text is verified never to appear in `citations`.
- Search text integration: When `search_text` is omitted, tests verify that search receives `query` concatenated with the capped image text. When `search_text` is supplied, tests confirm the image text does not reach search.
- Limits and validation: Tests cover invalid media types (422), oversized decoded images (413), a declared `Content-Length` over the cap rejected before reading, body byte counting via the route wrapper stopping with 413 at the cap with or without `Content-Length`, unset `NEXUS_ATTACHMENT_VISION_MODEL` refusing attachments (503), vision reader failures (502), empty extracted text (422), and PII pattern detections (422).
- Retention audit: Tests verify the invariant that **no retention path receives the image text**. Tests verify each path: search log (which records only `image_sha256`, media type, extracted character length, and extractor identity, with `search_text` recorded only as `search_text_len` and `search_text_sha256`), query-text retention (which stores `req.query`, not `search_text`), rewrite record, and stage spans.
- Streaming parity: Tests verify that decoding, `read_image`, and `scan_content` finish before the response starts on `POST /search/answer/stream`, and verify that 413, 422, 502, and 503 are returned as real HTTP status codes on the stream route as well. Tests verify that the `attachment` dictionary appears in both `POST /search/answer` and the stream's `done` event.
- Evidence image route (`GET /evidence/image/{handle}`):
  - The hash check runs first, so sniffing only ever sees the bytes that were read.
  - On hash match, the route sniffs downloaded bytes against the four allowed signatures (PNG, JPEG, WebP, GIF) and serves image bytes with the sniffed media type and cache headers.
  - Downloaded bytes matching none of the allowed signatures return 502.
  - Hash mismatch returns 409.
  - `Unresolvable` returns 404 with reason.
  - `AmbiguousHandle` returns 500 (logged, and the reader receives "the image reference is ambiguous; it cannot be shown").
  - Verifies the invariant: the image is served only if the principal can read at least one chunk in that tenant whose marker carries the handle, evaluated across all matching chunks. If the principal cannot read any such chunk, returns 404 (not 403, preventing existence leaks).
  - Concurrent requests for the same handle share one upstream fetch.
  - Upstream work exceeding the concurrency limit (proposed 4) or timeout (proposed 10 seconds) returns 503 with a retry hint.
  - Missing `NOTION_TOKEN` returns 503 ("source resolution not configured").
  - Verifies that no image bytes are written to disk or the database.
- Snippets and citations: Tests ensure `image_handle` is present on machine-read chunks and `null` on authored chunks.
- Web UI: Vitest unit tests (`*.test.js`) cover paste and drop handling, preview rendering, removal button logic, payload formatting, fetching thumbnails with the `Authorization: Bearer` header, turning them into blobs and displaying them through object URLs, and rendering failure text when image loading fails.

## 8. Acceptance

- All tests described in §7 pass.
- Existing tests pass without changes to expectations, except for updating `prompt_version` and adding `attachment` and `image_handle` to response key checks.
- A local manual run on the restored 2026-11-10 database dump:
  - One screenshot question is answered through the keyless bridge vision backend.
  - One machine-read citation loads its thumbnail through `/evidence/image/{handle}`. This requires a Notion token in the local environment (`NOTION_TOKEN`). Acceptance requires the thumbnail step; without a Notion token the SPEC is not accepted yet, rather than accepted with the step skipped.

## 9. First use

- The feature will first be exercised during the owner's manual run of the improvement loop (SPEC-nexus-improvement-loop, currently paused for a hand run). No date is set because the improvement loop's hand run has none.
- Nexus is used during real work, where screenshot questions and machine-read citations naturally appear.
- That run is where this functionality is first used and judged.
- First use gets an observable record: the improvement-loop hand run records how many questions carried an image and how many thumbnails were opened, in that run's record.
- If the run records no use of the image capabilities, that outcome is documented directly rather than explained away.

## 10. Open questions

- The search-text character limit (500 characters proposed), the decoded image size cap (5 MiB proposed), and upstream source resolution limits (concurrency 4 proposed, timeout 10 seconds proposed) remain open for final decision.
- Whether `GET /evidence/image/{handle}` should also accept a citation reference format instead of only the 16-character handle.
- Whether the streaming endpoint should send the `attachment` object earlier in the `evidence` event instead of waiting for the `done` event.
