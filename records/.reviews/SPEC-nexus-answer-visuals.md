---
target: SPEC-nexus-answer-visuals
critiqued_hash: sha256:7da7c75cab1cffc23392a090b2dacc4148496c2389004c7eab73168d114f0f0c
critiqued_at: '2026-11-13T06:05:06Z'
issues:
- issue_id: I-001
  category: missing-invariant
  severity: high
  description: §1 says every number in a visual is checked, but §4.3 sends values
    through validate_numbers, which only counts percentages, decimals and integers
    of 10 or more (§3). Chart values such as 3, 5 or 7 are never checked. They are
    not counted as unverified, and they are not listed as unchecked either, so a chart
    made of small invented integers reports zero unverified values. The SPEC needs
    to state that every numeric datum in a visual is checked whatever its size, or
    that values below the threshold are counted as unchecked.
  status: open
  disposition_reason: null
- issue_id: I-002
  category: missing-invariant
  severity: high
  description: The allowed transforms `calculate`, `aggregate` and `fold`, plus encoding-level
    aggregates (sum/mean in `encoding.*.aggregate`) and `params` expressions, produce
    the values the reader actually sees, such as bar heights and tooltip numbers.
    Those values come from grounded inputs but were never checked themselves. Only
    the raw `data.values` are checked. Either derived values must be marked as unchecked
    in `checks` and in the footer, or computed aggregates must be refused.
  status: open
  disposition_reason: null
- issue_id: I-003
  category: missing-invariant
  severity: high
  description: The rules against `url`, `name` and `href` are stated only for the
    top-level `data` and encoding. Vega-Lite v5 allows nested views (`layer`, `concat`/`hconcat`/`vconcat`,
    `facet`, `repeat`, `spec`), and each can carry its own `data.url`, `href` or `image`
    marks with a URL. The SPEC does not require the allowlist and refusals to apply
    recursively to every nested view and mark, so a nested spec can bypass the §5
    security guarantees.
  status: open
  disposition_reason: null
- issue_id: I-004
  category: risky-assumption
  severity: high
  description: '§4.2 refuses Mermaid `click` directives and HTML labels on the server,
    but no Python Mermaid parser is named. A regex or line-based check is easy to
    get around, and the SPEC lists no other ways to get links or HTML into a diagram:
    `href` and `call` forms, `link`/`links` in sequenceDiagram, `%%{init}%%` directives
    that change `securityLevel` or `htmlLabels`, markdown-string labels, entity escapes.
    It also does not say how node count is measured without parsing. Name the parsing
    approach and the full deny list, including init directives.'
  status: open
  disposition_reason: null
- issue_id: I-005
  category: adr-contradiction
  severity: medium
  description: 'ADR-0004 §2 requires an answer''s grounding character to stay distinct
    and visible: live code constants (Archon `code_constant`, with a drift warning)
    versus the document index. §4.3 checks visual values only against evidence text,
    and `checks` carries no grounding-source type. A chart of claim or code-constant
    values would therefore look the same as document-derived values, and the drift
    and authority signal ADR-0004 says must not be hidden would disappear. `checks`
    should carry provenance or grounding type, with handling for claim-backed values.'
  status: open
  disposition_reason: null
- issue_id: I-006
  category: adr-contradiction
  severity: medium
  description: §4.5 adds `visuals` to the A2A data part. ADR-0004 §5 says A2A has
    no active consumer and stays minimal, and is not extended until a real agent pulls
    it. Extending the A2A payload contradicts that standing decision. Either drop
    the A2A change or say why it does not count as an extension.
  status: open
  disposition_reason: null
- issue_id: I-007
  category: risky-assumption
  severity: medium
  description: validate_numbers decides `grounded` by finding the value in the evidence
    text. In a chart of up to 200 rows, common values like 10, 12 or 50% will often
    appear somewhere in the evidence regardless of the series or category they are
    assigned to. A datum can be marked grounded even when its value belongs to a different
    entity, month or metric. The SPEC presents this check as 'checked like the text',
    but a match on value alone is weaker for tabular data, and the gap is not acknowledged.
  status: open
  disposition_reason: null
- issue_id: I-008
  category: undefined
  severity: medium
  description: 'The order of the post-generation steps is not given. Do the text answer''s
    validate_numbers and validate_citations run on the answer before or after the
    fences are removed? If before, numbers and citations inside the fences are double-counted
    in the text-level `unverified_count`. If after, the existing text-level reports
    change meaning. Also unstated is whether `[출처: ...]` inside `cite` fields or Mermaid
    `%% cite` comments are picked up by the text citation extractor.'
  status: open
  disposition_reason: null
- issue_id: I-009
  category: undefined
  severity: medium
  description: '''A visual whose numbers are all unverified is shown collapsed'' does
    not cover visuals with no numbers. Most diagrams and graphs have none, so ''all
    unverified'' is either always true (every such visual is collapsed) or never true.
    The rule also ignores citations: a diagram whose cites are all fabricated is shown
    expanded.'
  status: open
  disposition_reason: null
- issue_id: I-010
  category: undefined
  severity: medium
  description: The 'allowlist of top-level keys' for nexus-chart is never listed.
    The 'vendored v5 JSON schema' does not name an exact Vega-Lite version or say
    how the schema stays aligned with the vendored vega-lite runtime. Validation behaviour
    cannot be reviewed or tested without those.
  status: open
  disposition_reason: null
- issue_id: I-011
  category: risky-assumption
  severity: medium
  description: §5 sets the CSP on the whole FastAPI app (`script-src 'self'`, no inline
    script). The same app serves other HTML routes, for example the FastAPI /docs
    and /redoc pages, which use inline script and CDN assets by default. The SPEC
    checks only that `index.html` has no inline script. It does not say which routes
    get the header or check that other HTML routes and the existing vis-network and
    graph views still work under it.
  status: open
  disposition_reason: null
- issue_id: I-012
  category: risky-assumption
  severity: low
  description: The SPEC assumes vega, vega-lite, vega-embed, vega-interpreter and
    a current mermaid all ship as browser globals that can be vendored into a no-build
    `index.html`. Recent mermaid and vega-interpreter releases are mainly ESM. No
    versions or files are named, so 'vendored like the existing ones' is not shown
    to be feasible without a build step or `<script type=module>`.
  status: open
  disposition_reason: null
- issue_id: I-013
  category: undefined
  severity: low
  description: Streaming placeholder behaviour is undefined. The SPEC does not say
    how the client detects the start of a `nexus-*` fence in partial `answer_delta`
    chunks, for example when the backticks and the tag arrive split across chunks,
    or what happens if the stream ends with an unterminated fence or ends in `error`
    before `done`.
  status: open
  disposition_reason: null
- issue_id: I-014
  category: undefined
  severity: low
  description: The UI chart-form switch is allowed 'where the encoding allows', but
    there are no rules for which encodings can become bar, line or table. A §7 test
    only checks that the local copy changes, not that the switch is valid.
  status: open
  disposition_reason: null
- issue_id: I-015
  category: untestable-requirement
  severity: medium
  description: §8 acceptance requires a hand run in which a comparison question 'yields
    a chart with all values grounded'. The output depends on the model and is not
    deterministic, and no question text, evidence or pass rule over repeated runs
    is given. The result cannot be reproduced and can pass or fail by chance. Name
    the fixed questions, the number of runs and the pass threshold.
  status: open
  disposition_reason: null
- issue_id: I-016
  category: unverifiable-claim
  severity: low
  description: §9 'First use' gives no observable criterion for 'whether their checks
    hold', and no record location or format. Any outcome satisfies it.
  status: open
  disposition_reason: null
- issue_id: I-017
  category: undefined
  severity: low
  description: §7 says an answer with no fence gives 'the same answer and prompt-independent
    keys as today'. 'Prompt-independent keys' is not defined, and `prompt_version`
    changes by design, so it is unclear which keys must be byte-identical.
  status: open
  disposition_reason: null
- issue_id: I-018
  category: risky-assumption
  severity: low
  description: 'The CSP is coordinated with SPEC-nexus-answer-images only by ''whichever
    lands second extends the same header''. There is no single owner or test of the
    merged header. If the images SPEC needs external `img-src` hosts, or this SPEC''s
    `img-src ''self'' blob: data:` conflicts with it, the second change can quietly
    widen or narrow the policy.'
  status: open
  disposition_reason: null
approved_by: null
approved_at: null
---

