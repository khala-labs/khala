---
target: SPEC-nexus-answer-images
critiqued_hash: sha256:48822e50d20ce27ee6476e251ae76857a158ebc49d365178520ddcb3c7daaffe
critiqued_at: '2026-11-13T06:04:13Z'
issues:
- issue_id: I-001
  category: undefined
  severity: high
  description: '§4.4 says a hash match returns the bytes ''with the stored media type'',
    but §3 lists what `vision_extractions` stores (tenant, sha256, extractor identity,
    text, error, truncated, block id, source uri) and media type is not in it. `SourceRef`
    does not carry it either. The SPEC never says where the media type comes from:
    a new column, the upstream Content-Type, or byte sniffing. Each option has different
    trust and test consequences.'
  status: open
  disposition_reason: null
- issue_id: I-002
  category: risky-assumption
  severity: high
  description: '§4.1 says a development run ''must use a vision model mapped to claude
    with the keyless bridge configured''. §10 admits that `vision_model()` also sets
    the ingest `extractor_identity()`. Following §4.1 therefore changes the identity
    that ingest writes and checks. ADR-0010 §5 says changing the extractor is a migration,
    a deliberate act with a recorded reason, never a silent re-read. A config switch
    made only to answer attachments would re-key ingest without anyone noticing. The
    SPEC treats this as an open question when it is a precondition: attachments need
    a separate reader setting, or §4.1 must forbid the switch on any environment that
    ingests.'
  status: open
  disposition_reason: null
- issue_id: I-003
  category: missing-invariant
  severity: high
  description: §4.4 'locates a chunk in tenant <t> carrying the handle' and checks
    that chunk's classification. The same image (same sha256[:16]) can appear in several
    chunks or documents with different classifications. Which chunk the server picks
    decides whether a lower-clearance principal gets the image. No invariant says,
    for example, 'serve only if the principal can read at least one chunk carrying
    the handle, and check against that chunk'. This is a clearance leak.
  status: open
  disposition_reason: null
- issue_id: I-004
  category: missing-invariant
  severity: high
  description: §4.2 sends `query` plus up to 500 characters of image text down the
    existing `search_text` path. Section 3 confirms that `answer_context` never reaches
    query-text retention or the search log, but says nothing equivalent for `search_text`.
    If `search_text` is logged or retained, text read from the image is stored. That
    contradicts §4.1 ('neither the image bytes nor the extracted text are stored').
    The PII scan only catches four regex patterns, so it does not close this gap.
    The SPEC needs to check the existing `search_text` retention and state the invariant,
    and §7 needs a test for it.
  status: open
  disposition_reason: null
- issue_id: I-005
  category: adr-contradiction
  severity: medium
  description: ADR-0010 §2 says machine-read text is 'never presented as equal to
    authored text'. Its failure mode is that the reader invents. §4.2 puts attachment
    text in the same slot as `answer_context`, 'under the same rule', and `validate_numbers`
    reports its numbers as `found_in = "context"`, the same value used for text the
    caller typed. A number the vision model invented then reads as 'the caller said
    so'. The SPEC needs a distinct `found_in` value, or a label in the answer, that
    separates machine-read caller material from caller-typed material.
  status: open
  disposition_reason: null
- issue_id: I-006
  category: undefined
  severity: medium
  description: §4.2 does not say how `validate_numbers(context=...)` combines `answer_context`
    and image text when both are sent. The function takes one `context` string. Concatenating
    them loses the source, and replacing one with the other drops caller material
    from grounding.
  status: open
  disposition_reason: null
- issue_id: I-007
  category: risky-assumption
  severity: medium
  description: §4.5 loads thumbnails with `<img>` from `/evidence/image/{handle}?tenant=<t>`.
    If the API authenticates with a bearer header, which is how `api.js` calls the
    answer paths, an `<img src>` request carries no Authorization header. Every thumbnail
    would then come back 404, given §6 returns 404 for a missing principal. The SPEC
    should either specify fetch-to-blob with the header (consistent with `blob:` in
    the CSP) or state the auth mechanism the route accepts.
  status: open
  disposition_reason: null
- issue_id: I-008
  category: missing-invariant
  severity: medium
  description: §4.3 limits body size only by checking `Content-Length` per route.
    A chunked request without `Content-Length` skips the check and is buffered whole
    before base64 decoding, which is the exact case §4.3 is meant to stop. There is
    no invariant for requests that have no `Content-Length` header (reject them, or
    cap bytes while streaming).
  status: open
  disposition_reason: null
- issue_id: I-009
  category: undefined
  severity: medium
  description: For `POST /search/answer/stream`, the SPEC does not say whether `read_image`
    and `scan_content` finish before the response stream starts. If they run after
    headers are sent, the 413, 422 and 502 statuses in §6 cannot be delivered and
    would need an in-stream error event, which is not specified. §7 does not test
    status codes on the stream route.
  status: open
  disposition_reason: null
- issue_id: I-010
  category: risky-assumption
  severity: medium
  description: §4.4 calls the Notion API and downloads the signed URL on every thumbnail
    view, with only a 5-minute private cache. An answer with N machine-read citations
    triggers N or more Notion calls each time the page renders. The SPEC has no rate
    limit, concurrency bound, timeout or server-side dedup. It also assumes a Notion
    token is available on the request path for every tenant, but §8 shows the token
    may not exist locally.
  status: open
  disposition_reason: null
- issue_id: I-011
  category: undefined
  severity: medium
  description: §4.4 maps `AmbiguousHandle` to 500 through the internal-error helper.
    This is a predictable data condition (two rows share a handle), not an unexpected
    fault. The SPEC does not say whether the reader learns why the image is missing,
    which conflicts with §4.4's own principle that 'the reader must be told'. The
    16-character handle (64 bits of sha256) makes collisions across documents in a
    tenant possible, but the SPEC does not say how likely they are or how they will
    be detected.
  status: open
  disposition_reason: null
- issue_id: I-012
  category: adr-contradiction
  severity: low
  description: The ADR-0008 backstop is marked 'does-not-fire' and declared by the
    author, with the note that 'the owner confirms this ruling when approving'. ADR-0008
    §5 lists 'connector work beyond the existing two sources' as a backstop event.
    §4.4 adds a request-time Notion block re-fetch and image download inside the serving
    app, which is a new runtime use of the connector. The backstop entry should cover
    the connector, not only search.
  status: open
  disposition_reason: null
- issue_id: I-013
  category: unverifiable-claim
  severity: low
  description: §5 says injected text 'cannot make the reader execute tools or access
    the filesystem' because the reader is reused unchanged. §7 tests only that `read_image`
    is called once with one image. ADR-0010 §6 says the SPEC 'must implement and test'
    all three constraints. No test asserts that the reader has no tools or filesystem
    access on this new, caller-controlled path.
  status: open
  disposition_reason: null
- issue_id: I-014
  category: scope-creep
  severity: low
  description: §4.5 adds an app-wide Content-Security-Policy header to the FastAPI
    app, which has had none until now. That is a security-policy change for every
    route, not just a support for thumbnails. Allowing `data:` is not needed for blob
    previews or same-origin thumbnails. A header that sets only `img-src` also suggests
    protection the policy does not give.
  status: open
  disposition_reason: null
- issue_id: I-015
  category: untestable-requirement
  severity: low
  description: §9 says the feature is 'first used and judged' in a hand run of a loop
    that is currently paused, but it gives no success criterion and no date. Acceptance
    in §8 also allows the thumbnail step to be recorded as not exercised. As written,
    nothing can fail.
  status: open
  disposition_reason: null
approved_by: null
approved_at: null
---

