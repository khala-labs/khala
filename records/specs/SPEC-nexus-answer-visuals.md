---
id: SPEC-nexus-answer-visuals
type: spec
title: Answers can carry interactive visuals as declarative specs, and every value
  in a visual is checked against the evidence like the text is
status: draft
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
- No visuals on Slack, MCP or A2A beyond the fallbacks in §4.5.
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
- A sibling SPEC drafted at the same time, SPEC-nexus-answer-images, adds a Content-Security-Policy for `img-src`; whichever lands second extends the same header.

## 4. Design

### 4.1 Three kinds, one fence syntax

The model may end its answer with up to two fenced blocks (proposed cap), each tagged with one of three kinds:
- ` ```nexus-chart ` — a Vega-Lite v5 spec (JSON) with inline `data.values` only. For comparisons, trends, distributions.
- ` ```nexus-diagram ` — Mermaid source restricted to `flowchart`, `sequenceDiagram` and `stateDiagram-v2`. For processes and states.
- ` ```nexus-graph ` — JSON `{nodes: [{id, label, group?}], edges: [{from, to, label?}]}` rendered with the already-vendored `vis-network`. For relations.

Every chart datum, diagram node and graph node or edge may carry a `cite` field (or, for Mermaid, a `%% cite: [출처: ...]` comment line directly after the node's line, since Mermaid comments take a whole line) using the existing citation syntax.

A fence is used because both backends return plain text and stream it; a fence survives streaming and needs no API mode. The answer text stays readable without the visual.

### 4.2 Server-side parsing and validation

After generation (both paths), a new module `llm/visuals.py` extracts the fenced blocks from the answer text, removes them from `answer`, and validates each:
- `nexus-chart`: JSON parse; Vega-Lite schema check against a vendored v5 JSON schema with `jsonschema` (already pinned in `nexus/constraints.txt`); allowlist of top-level keys; `data` must be `{values: [...]}` (no `url`, no `name`), at most a proposed 200 rows; transforms limited to `filter`, `calculate`, `aggregate`, `fold` (encoding `sort` is allowed); no `href` encoding channel; `params` allowed (this is what gives sliders, dropdowns and selections).
- `nexus-diagram`: allowed diagram types only; no `click` directives; no HTML labels; at most a proposed 60 nodes.
- `nexus-graph`: JSON shape check; at most a proposed 80 nodes and 160 edges; labels plain text.

Each valid block becomes an entry in a new response key `visuals`: `[{kind, spec, checks}]`. Invalid blocks are dropped and reported in `visuals_dropped: [{kind, reason}]`, never shown as raw code.

Both keys are generation keys (added to `_NARRATION_KEYS`, `None` under `evidence_only`). The stream sends them in `done`; the `answer_delta` text the client already received may contain the fence, and the client replaces it when `done` arrives (§4.4). `prompt_version` changes.

### 4.3 Grounding: values and labels are checked

- Numbers: every numeric value in a chart's `data.values`, and every number inside diagram or graph labels, is passed through `validate_numbers` with the same evidence text, query and context as the answer text. Each value gets `grounded` and `found_in`.
- Citations: every `cite` is passed through `validate_citations` against the same packet.
- Labels: chart category labels and node labels that are not numbers are not judged true or false by this SPEC (no verifier for that exists); they are counted as unchecked, not as verified.
- `checks` per visual: `{numbers: [...], unverified_numbers, citations: [...], unverified_citations, unchecked_labels}`.
- A visual is shown even when some values are unverified, with those values marked, the same way the text answer shows unverified numbers and citations today instead of hiding them. A visual whose numbers are all unverified is shown collapsed behind a warning line.
- When the answer abstains, `visuals` is an empty list.

### 4.4 Rendering and interaction in the web UI

New vendored libraries, as local files with their versions recorded like the existing ones (no CDN): `vega`, `vega-lite`, `vega-embed`, `vega-interpreter` (the CSP-safe expression interpreter), and `mermaid`.

`components/visual.js` renders a `visuals` entry by kind:
- chart: `vega-embed` with `ast: true` and the interpreter (no `eval`), actions menu off except "export PNG/SVG"; `params` bindings give sliders and dropdowns; tooltips on hover; legend click toggles series.
- chart controls added by the UI, not the model: switch between bar, line and table where the encoding allows; sort; show the data as a table. These change only the local copy of the spec.
- diagram: `mermaid` with `securityLevel: 'strict'`; click a node to highlight it and its edges (done by the UI on the rendered SVG).
- graph: `vis-network` with the same options as `views/graph.js`; drag, zoom, click to highlight neighbours.

Every visual shows its checks: values with `grounded = false` get the same ⚠ mark the citation chips use; a footer line says "N values not found in the evidence, M labels not checked". Hovering a cited datum shows its citation.

While streaming, the fence text is shown as a placeholder ("drawing a visual…"), not as raw JSON; on `done` it is replaced by the rendered visual or by the drop reason.

The model-supplied spec is never inserted as HTML; text inside it is set as text.

### 4.5 Other surfaces

- `/search/answer` JSON: `visuals` and `visuals_dropped` as above, so any client can render.
- Slack: no visual; one line "This answer has a visual; open it in the web UI" plus, for charts, the data as a short mrkdwn table (proposed: up to 10 rows).
- MCP `nexus_answer`: the answer text plus each visual's kind and its data as a short text table; no spec.
- A2A: `visuals` added to the existing data part.

### 4.6 Prompt

The answer system prompt gains a section describing the three fence kinds, the caps, the `cite` field, and when to use a visual: only when the evidence contains the values or structure, and never to fill a gap. If evidence lacks the values, the model writes no visual.

The model is told that values in a visual are checked like numbers in text.

## 5. Security

The model output is untrusted, because corpus text reaches the prompt and can steer it. The design keeps it data:
- No model-written code.
- Vega-Lite without `url` data, without `href`, with the interpreter instead of `eval`.
- Mermaid in strict mode with `click` and HTML labels refused server-side.
- `vis-network` labels as text.

The web UI gets a Content-Security-Policy: `script-src 'self'` (no `unsafe-eval`, no inline script), `connect-src 'self'`, `img-src 'self' blob: data:`, `style-src 'self' 'unsafe-inline'` (Mermaid and vega-embed set inline styles), `frame-src 'none'`, `object-src 'none'`. This needs `index.html` to have no inline script; this change checks that. The sibling SPEC-nexus-answer-images adds CSP for `img-src`; whichever lands second extends the same header.

Size caps (rows, nodes, edges, blocks) bound rendering cost.

## 6. Error handling

Invalid JSON, schema failure, disallowed key or type, cap exceeded → dropped with reason in `visuals_dropped`. Renderer exception in the browser → the visual's box shows the reason and the data table. The answer text is always shown.

## 7. Testing

No paid calls; the answer backend is a test double that returns fixed text.

- An answer with no fence produces `visuals = []` and the same `answer` and prompt-independent keys as today.
- Each kind: a valid block is extracted, removed from `answer`, validated and returned; the stream's `done` carries the same `visuals`.
- Refusals: `data.url`, `href`, an unknown transform, Mermaid `click`, HTML labels, over-cap rows or nodes, a third block → dropped with a reason.
- Grounding: a chart value present in the evidence is `grounded`; an invented one is not and is counted; a `cite` to a real snippet is verified, a made-up one is not; abstention gives `[]`.
- Parity test and `_NARRATION_KEYS` test updated for the two keys; `evidence_only` gives `None` for both.
- Web (vitest): the renderer refuses a spec the server would refuse (defence in depth), sets labels as text, shows ⚠ on unverified values, and the chart-form switch changes only the local copy.
- A test asserts the CSP header on `/` and that `index.html` has no inline script.

## 8. Acceptance

Tests above pass. A hand run on the restored 2026-11-10 dump (local, keyless bridge):
- One comparison question that yields a chart with all values grounded.
- One process question that yields a diagram.
- One question whose evidence lacks values, which yields no visual.

## 9. First use

The owner's manual run of the improvement loop, where Nexus is used during real work. The question there is whether visuals are asked for and whether their checks hold. If none are produced or used, that is recorded.

## 10. Open questions

- The caps (2 blocks, 200 rows, 60 diagram nodes, 80 graph nodes, 160 edges, 10 Slack rows) are proposals.
- Whether a visual whose values are all unverified should be hidden instead of collapsed.
- Whether label checking (matching labels to evidence text) is worth a verifier later.
- Bundle size: Mermaid and Vega add several megabytes to the web UI; whether to load them lazily on the first visual.
