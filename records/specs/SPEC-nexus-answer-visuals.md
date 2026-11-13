---
id: SPEC-nexus-answer-visuals
type: spec
title: Answers can carry interactive visuals as declarative specs, and every value
  in a visual is checked against the evidence like the text is
status: in_review
linked_adrs:
- ADR-0004
tags:
- nexus
- answer
- web
- visuals
date: '2026-11-13T05:48:30Z'
---
# Answers can carry interactive visuals as declarative specs, and every value in a visual is checked against the evidence like the text is

## 1. Goal

The chatbot answer may include visuals the model generates: charts, diagrams and relation graphs, which the reader can interact with in the web UI (hover for values, click to highlight or filter, toggle series, change a parameter with a slider or dropdown, switch between chart forms, pan and zoom a graph).

The model writes **declarative specs only, never code**. The web UI renders them with vendored libraries.

**A value in a visual is a claim like a sentence in the answer: every number and every citation in it is checked against the evidence with the same verifiers the text uses, and the result is shown to the reader.** Labels that no verifier can check are counted as unchecked, never as verified. A chart drawn from invented numbers looks more credible than a wrong sentence; that is why this rule is load-bearing.

## 2. Non-goals

- No model-written HTML, JavaScript or SVG, and no sandboxed-iframe execution. That option was considered and not chosen: it cannot be checked value by value, and corpus text that reaches the prompt could become code running in the reader's browser.
- No image generation (raster pictures).
- No visuals on Slack or MCP beyond the fallbacks in §4.5. A2A output is not extended (ADR-0004 §5).
- No change to retrieval, evidence assembly, citation syntax or abstention. No new answer backend and no structured-output API mode (none exists today).
- No saving, sharing or editing visuals after the answer; interaction is local to the page.

## 3. What exists (verified 2026-11-13)

Paths are under `nexus/nexus/` on `master`, verified 2026-11-13.

- Answers are generated as Markdown text by `llm/answer.py::generate_answer` (non-stream) and directly in the stream handler (`api.py`, via `build_prompts` and `llm_svc.stream`). Both answer backends (`anthropic`, `claude-code` keyless bridge) take a text prompt and return text; no JSON mode, response schema or tool schema is used for answers.
- Verification after generation: `llm/numbers.py::validate_numbers(answer_text, evidence_text, query="", context="")` returns `NumberReport{numbers: [NumberCheck(value, grounded, found_in)], unverified_count}`; a significant number is a percentage, a decimal, or an integer of 10 or more. `llm/citations.py::validate_citations(answer_text, packet)` returns `CitationReport{citations: [Citation(title, section, verified, provenance_tier)], unverified_count}`; citation syntax is `[출처: ...]` (`search/citation_syntax.py`).
- Response keys produced by generation are listed in `_NARRATION_KEYS` (`api.py:412`); they are `None` when `evidence_only` is set. Parity rule: every `/search/answer` key must also appear in the stream's `evidence` or `done` payload (`tests/test_the_stream_sends_what_the_answer_sends.py`). Stream events are `evidence`, `graph`, `answer_delta`, `done`, `error`.
- Web UI (`web/`): vanilla JS, no build step (`package.json` has only `vitest`). Vendored as globals in `index.html`: `marked` 15.0.12, `DOMPurify` 3.4.10, `vis-network` 9.1.13. `components/markdown.js` renders answers with `DOMPurify.sanitize(marked.parse(text))`, default options; code fences get marked's default `language-*` class; no highlighter, Mermaid or Vega exists. `vis-network` is already used for the graph view (`views/graph.js`) and an inline graph in chat (`views/chat.js::renderInlineGraph`, from the stream's `graph` event).
- The web UI is served by the same FastAPI app at `/` and `/static`. No Content-Security-Policy is set anywhere.
- Slack formats answers as mrkdwn text blocks (`slack/formatter.py`); MCP `nexus_answer` returns a string; A2A returns a text part plus a data part.
- A sibling SPEC drafted at the same time, SPEC-nexus-answer-images, states the same full Content-Security-Policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; font-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'`. It is set only on `/` and `/static` by one shared helper; whichever lands first adds the helper.

## 4. Design

### 4.1 Three kinds, one fence syntax

The model may end its answer with up to two fenced blocks (proposed cap), each tagged with one of three kinds:
- ` ```nexus-chart ` — a Vega-Lite v5 spec (JSON) with inline `data.values` only. For comparisons, trends, distributions.
- ` ```nexus-diagram ` — JSON (`{type: flowchart|state, nodes, edges}` or `{type: sequence, participants, messages}`). For processes and states.
- ` ```nexus-graph ` — JSON `{nodes: [{id, label, group?}], edges: [{from, to, label?}]}` rendered with the already-vendored `vis-network`. For relations.

Every chart datum, diagram node or edge, and graph node or edge may carry a `cite` field using the existing citation syntax.

A fence is used because both backends return plain text and stream it; a fence survives streaming and needs no API mode. The answer text stays readable without the visual.

### 4.2 Server-side parsing and validation

After generation (both paths), a new module `llm/visuals.py` extracts the fenced blocks from the answer text and removes them from `answer` first. The existing text checks run on the answer without fences, so their meaning is unchanged (today's answers have no fences) and the text citation extractor never sees `cite` fields. Visual checks run on the fence contents separately.

Validation checks each extracted block:
- `nexus-chart`: JSON parse; Vega-Lite schema check against a vendored v5 JSON schema with `jsonschema` (already pinned in `nexus/constraints.txt`). The runtime and its schema are vendored from the same 5.x release. Allowed top-level keys are `$schema`, `description`, `title`, `width`, `height`, `data`, `mark`, `encoding`, `transform`, `params`, `layer`, `concat`, `hconcat`, `vconcat`, `facet`, `repeat`, `spec`. `data` must be `{values: [...]}` (no `url`, no `name`), at most a proposed 200 rows. Validation walks the whole spec recursively, including `layer`, `concat`, `hconcat`, `vconcat`, `facet`, `repeat` and `spec`. At any depth it refuses a `url` key, an `href` channel, the `image` mark, `datasets` and `usermeta`. Transforms and encodings that compute new values are refused (`calculate`, `aggregate`, `joinaggregate`, `window`, `bin`, `density`, `regression`, `loess`, and encoding-level `aggregate` and `bin`). Allowed transforms are `filter` and `fold`; `params` are allowed only in filter predicates, selections and conditional encodings (encoding `sort` is allowed). Every value the reader sees is then a raw datum that was checked.
- `nexus-diagram`: JSON shape check (`{type: flowchart|state, nodes, edges}` or `{type: sequence, participants, messages}`). Node count is the length of `nodes`, at most a proposed 60 nodes. Labels are plain text. No Mermaid parser is needed.
- `nexus-graph`: JSON shape check; at most a proposed 80 nodes and 160 edges; labels plain text.

Each valid block becomes an entry in a new response key `visuals`: `[{kind, spec, checks}]`. Invalid blocks are dropped and reported in `visuals_dropped: [{kind, reason}]`, never shown as raw code.

Both keys are generation keys (added to `_NARRATION_KEYS`, `None` under `evidence_only`). Every response key except `prompt_version`, `visuals` and `visuals_dropped` is byte-identical to today for an answer with no fence. The stream sends them in `done`; the `answer_delta` text the client already received may contain the fence, and the client replaces it when `done` arrives (§4.4). `prompt_version` changes.

### 4.3 Grounding: values and labels are checked

- Numbers: every numeric value in a visual is checked whatever its size. Every numeric value in a chart's `data.values`, and every number inside diagram or graph labels, is passed through `validate_numbers` with the same evidence text, query and context as the answer text, using a flag that checks every number. `validate_numbers` keeps its significance rule for answer text; visuals call it with this flag so a chart of small invented integers reports them as unverified.
- Chart data grounding: for chart data a value match alone is weaker than for text. A chart datum is marked `grounded` only if its value and its category label occur in the same evidence snippet; a value found elsewhere is `found_elsewhere`, counted and shown as not verified. Occurring in the same snippet does not guarantee occurring in the same row; this remains a known limit.
- Citations: every `cite` is passed through `validate_citations` against the same packet.
- Provenance: each checked value in `checks` carries `found_in` and, when it is `evidence`, the matched snippet's `doc_type` and `provenance_tier`, so a value from a code constant or from machine-read text is shown with the same marker the text answer uses and is not presented as document text.
- Labels: chart category labels and node labels that are not numbers are not judged true or false by this SPEC (no verifier for that exists); they are counted as unchecked, not as verified.
- `checks` per visual: `{numbers: [...], unverified_numbers, citations: [...], unverified_citations, unchecked_labels}`.
- A visual is shown even when some values are unverified, with those values marked, the same way the text answer shows unverified numbers and citations today instead of hiding them. A visual is collapsed behind a warning when it has at least one checkable item (number or `cite`) and none of them is grounded or verified. A visual with no checkable item is shown with the footer "nothing in this visual could be checked".
- When the answer abstains, `visuals` is an empty list.

### 4.4 Rendering and interaction in the web UI

New vendored libraries, as local files with their versions recorded like the existing ones (no CDN): `vega`, `vega-lite`, `vega-embed`, `vega-interpreter` (the CSP-safe expression interpreter), and `mermaid`. The Vega-Lite runtime and its JSON schema are vendored from the same 5.x release, the exact version recorded beside the files.

The first implementation step is a feasibility check that names the files: a browser-global build for each library, or loading it from `app.js`, which is already a module. If neither works without a build step for a library, the SPEC goes back to review rather than adding a build step.

`components/visual.js` renders a `visuals` entry by kind:
- chart: `vega-embed` with `ast: true` and the interpreter (no `eval`), actions menu off except "export PNG/SVG"; `params` bindings give sliders and dropdowns; tooltips on hover; legend click toggles series.
- chart controls added by the UI, not the model: bar and line switch only when x is nominal, ordinal or temporal and y is quantitative, with at most a `color` series; table is always available; otherwise the switch is hidden. Sort; show the data as a table. These change only the local copy of the spec.
- diagram: `mermaid` with `securityLevel: 'strict'`. The client builds Mermaid text from the JSON `nexus-diagram` spec, escaping every label, so `click`, `href`, `call`, links, init directives, markdown-string and HTML labels cannot be written at all. Click a node to highlight it and its edges (done by the UI on the rendered SVG).
- graph: `vis-network` with the same options as `views/graph.js`; drag, zoom, click to highlight neighbours.

Every visual shows its checks: values with `grounded = false` or marked `found_elsewhere` get the same ⚠ mark the citation chips use. The footer says "found in the evidence", not "verified": a footer line says "N values not found in the evidence, M labels not checked". A visual with no checkable item is shown with the footer "nothing in this visual could be checked". Hovering a cited datum shows its citation, with provenance tier and doc type markers matching the text answer.

While streaming, the client matches a fence start on the accumulated text at a line start, not per chunk. The fence text is shown as a placeholder ("drawing a visual…"), not as raw JSON; on `done` it is replaced by the rendered visual or by the drop reason. A fence still open at `done` is dropped as "incomplete visual"; an `error` event before `done` removes the placeholder.

The model-supplied spec is never inserted as HTML; text inside it is set as text.

### 4.5 Other surfaces

- `/search/answer` JSON: `visuals` and `visuals_dropped` as above, so any client can render.
- Slack: no visual; one line "This answer has a visual; open it in the web UI" plus, for charts, the data as a short mrkdwn table (proposed: up to 10 rows).
- MCP `nexus_answer`: the answer text plus each visual's kind and its data as a short text table; no spec.

### 4.6 Prompt

The answer system prompt gains a section describing the three fence kinds (including the JSON shape for `nexus-diagram`), the caps, the `cite` field, and when to use a visual: only when the evidence contains the values or structure, and never to fill a gap. If evidence lacks the values, the model writes no visual.

The model is told that values in a visual are checked like numbers in text.

## 5. Security

The model output is untrusted, because corpus text reaches the prompt and can steer it. The design keeps it data:
- No model-written code.
- Vega-Lite without `url` data, without an `href` channel, without the `image` mark, without `datasets` and `usermeta`, with transforms restricted to `filter` and `fold`, and with the interpreter instead of `eval`.
- Diagram input is JSON; the client builds Mermaid text from it, escaping every label, so `click`, `href`, `call`, links, init directives, markdown-string and HTML labels cannot be written at all.
- `vis-network` labels as text.

The web UI gets a Content-Security-Policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; font-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'`. It is set only on `/` and `/static` by one helper shared with SPEC-nexus-answer-images, which states the same string; whichever lands first adds the helper. The header is set only on `/` and `/static`, so `/docs` and `/redoc` are untouched. This policy requires `index.html` to have no inline script; this change checks that.

Size caps (rows, nodes, edges, blocks) bound rendering cost.

## 6. Error handling

Invalid JSON, schema failure, disallowed key or type, cap exceeded, or a fence still open at `done` ("incomplete visual") → dropped with reason in `visuals_dropped`. An `error` event before `done` removes the placeholder. Renderer exception in the browser → the visual's box shows the reason and the data table. The answer text is always shown.

## 7. Testing

No paid calls; the answer backend is a test double that returns fixed text.

- An answer with no fence produces `visuals = []` and every response key except `prompt_version`, `visuals` and `visuals_dropped` is byte-identical to today.
- Order: fences are removed first; existing text checks run on the answer without fences (the text citation extractor never sees `cite` fields), and visual checks run on fence contents separately.
- Each kind: a valid block is extracted, removed from `answer`, validated and returned; the stream's `done` carries the same `visuals`.
- Refusals: `data.url`, an `href` channel, the `image` mark, `datasets`, `usermeta`, disallowed transforms and encodings (`calculate`, `aggregate`, `joinaggregate`, `window`, `bin`, `density`, `regression`, `loess`, and encoding-level `aggregate` and `bin`), `params` outside allowed contexts, invalid JSON diagram shape, over-cap rows or nodes, a third block → dropped with a reason. Recursive checks apply at any depth across `layer`, `concat`/`hconcat`/`vconcat`, `facet`, `repeat` and `spec`.
- Grounding: every numeric value in a visual is checked whatever its size, so small invented integers report as unverified; a chart datum is `grounded` only if its value and category label occur in the same evidence snippet, otherwise `found_elsewhere` and unverified; checked values carry `found_in`, `doc_type` and `provenance_tier`; a `cite` to a real snippet is verified, a made-up one is not; abstention gives `[]`.
- Warning and collapse: a visual with checkable items where none is grounded or verified collapses behind a warning; a visual with no checkable item shows the footer "nothing in this visual could be checked".
- Vendored library parity: a test asserts that the vendored Vega-Lite schema file and the runtime report the same version.
- Streaming: a fence still open at `done` is dropped as an incomplete visual; an `error` event before `done` removes the placeholder.
- Parity test and `_NARRATION_KEYS` test updated for the two keys; `evidence_only` gives `None` for both.
- Web (vitest): the renderer refuses a spec the server would refuse (defence in depth), sets labels as text, builds escaped Mermaid text from JSON `nexus-diagram`, shows ⚠ on unverified values, and the chart-form switch changes only the local copy. Bar and line switch only when x is nominal, ordinal or temporal and y is quantitative, with at most a `color` series; table is always available; otherwise the switch is hidden.
- CSP tests: one test asserts the exact full Content-Security-Policy header string. Tests assert the header is set on `/` and `/static`, that `/docs` and `/redoc` are untouched, that `index.html` has no inline script, and that the existing graph view and inline chat graph render under the policy.

## 8. Acceptance

Tests above pass. A hand run on the restored 2026-11-10 dump (local, keyless bridge) uses three fixed questions written into the run record before the run, each run three times. Pass:
- The comparison question yields a chart with every value grounded in at least two of three runs.
- The process question yields a diagram in at least two of three runs.
- The question whose evidence lacks values yields no visual in three of three runs.

## 9. First use

The owner's manual run of the improvement loop, where Nexus is used during real work. The question there is whether visuals are asked for and whether their checks hold. The run records, in the improvement-loop hand run's record, the number of answers with a visual and how many of them had any value not found in the evidence. If none are produced or used, that is recorded.

## 10. Open questions

- The caps (2 blocks, 200 rows, 60 diagram nodes, 80 graph nodes, 160 edges, 10 Slack rows) are proposals.
- Whether a visual whose values are all unverified should be hidden instead of collapsed.
- Whether label checking (matching labels to evidence text) is worth a verifier later.
- Bundle size: Mermaid and Vega add several megabytes to the web UI; whether to load them lazily on the first visual.
