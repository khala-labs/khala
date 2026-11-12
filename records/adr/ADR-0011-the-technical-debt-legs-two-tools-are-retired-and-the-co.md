---
id: ADR-0011
type: adr
title: The technical-debt leg's two tools are retired, and the cognitive-debt leg
  stays open without its tool
status: accepted
linked_adrs:
- ADR-0002
- ADR-0003
- ADR-0004
date: '2026-11-08T15:40:35Z'
approved_by: LivingLikeKrillin
reviewed_at: '2026-11-12T19:55:20Z'
content_hash: sha256:481f88432723e14bd4a673f1491e7347fbd07ee4dbd5240076512540e09c03d5
---
# ADR-0011: The technical-debt leg's two tools are retired, and the cognitive-debt leg stays open without its tool

## Status
Proposed.

Successor record to [[ADR-0002]] (three debts; servicing-window tools; a gated follow-on backlog), [[ADR-0003]] (artifact lifecycle: canonical governance tier "approved, content-hashed, vouched via ken", naming ken as "exactly that instrument" for cognitive debt—vouch bound to `content_hash`, a repetition schedule, org metrics = cognitive-debt coverage + orphan list), and [[ADR-0004]] (component architecture: each tool grounds in a different truth source). Tool renamings from [[ADR-0005]] and [[ADR-0007]] (mutqa = Probe, probe = Observer, ken = Adept, specledger = Arbiter) appear as new names with old in parentheses.

Accepted ADRs are immutable (`content_hash` stamped); no sentence in [[ADR-0002]], [[ADR-0003]], or [[ADR-0004]] is edited. This record is the successor a reader consults for tool assignments (`linked_adrs` carries lineage). Older text stands as written; where marked historical or unimplemented, this record is the ruling. If not accepted, extracted repositories remain archived and nothing is un-built; what would be missing is the ledger record that [[ADR-0002]]'s and [[ADR-0003]]'s tool assignments no longer hold.

## Date
2026-11-09

## Context
Verified 2026-11-08: Arbiter (intent debt) is in use; every SPEC and ADR in this ledger, including this record, went through its record → critique → disposition → approve path (`records/.reviews/` holds sidecars). Daily use is not claimed, as commit history does not record gate invocations.

Observer's last code change was 2026-07-11; Probe's last feature change 2026-07-11; Adept's 2026-07-02; Adept Web none since 2026-08-02. Adept ran once for real: the 2026-07-02 dogfood (one ADR registered, 5 questions, 3 right / 2 wrong, coverage 0 of 11 artifacts)—the "real puller" [[ADR-0004]] refers to; it never ran twice. Observer and Probe never ran against a real PR stream or real test suite. No reason for stopping is recorded in the ledger, engineering log, `OPEN.md`, or tools' READMEs (searched 2026-11-08; search scope stated so the claim is bounded).

On 2026-11-08, Observer, Probe, and Adept (with Adept Web and its three state files, in `khala-labs/adept`) were extracted to organization repositories and archived; Arbiter to `khala-labs/arbiter`, live, installed back into monorepo CI from git. The monorepo retains Nexus, the docs site, and `records/`.

The Observer retrospective (`records/audit/2026-11-08-observer-retrospective.md`) evaluated `observer check` v0.6.0 over the last 30 merged PRs (#552–#582). Observer ships profiles for Spring Boot, Next.js, and React SPA only; the evaluator wrote a Python monorepo profile, making measurement a property of that profile as much as the tool. With size thresholds on, 8/30 warned (all file-count). With cohesion rules only, 2/30 warned, both repository-wide terminology sweeps where splitting PRs is not useful. The pre-written rule required wiring CI only at 10–60%. One PR is 3.3% of the sample, so the figure alone is fragile; the decision does not rest on it alone. Observer v0.4–v0.5 review and troubleshooting functions grounded in Nexus (service graph, entity gaps, approved specs, guidelines) were unexercised, needing a running Nexus with a live graph.

Observer v0.1–v0.3 (PR size, OpenAPI diff, checklist) have common substitutes (CI size checks, dedicated OpenAPI diff tools, PR templates, LLM reviewers). Observer v0.4–v0.5 ground in Nexus data; whether a separate surface is warranted is left open—[[ADR-0004]]'s grounding division is not retracted, but the Observer implementation is retired. Probe wraps `cosmic-ray`; additions (changed-module selection, adjudicated survivor ledger, Critic prompt, `absorb` step) are believed reproducible with the engine, a small ledger file, and a skill text—a cost judgement, not a demonstrated reproduction (none attempted). For cognitive debt, no off-the-shelf substitute is known to the author.

Under [[ADR-0002]] gate ⓐ, the comprehension meter is a gated follow-on ("none is designed in this ADR"), fired when an observed, logged rate crosses a threshold; the comprehension log is ⓐ's own first sub-step. A gate is declared fired by the director and recorded in that direction's first SPEC ([[ADR-0002]] dispositions I-007, I-008). This record respects that: designing no meter, hook, schema, or kill criteria. Two independent design proposals (Fable agent and Codex, 2026-11-08) exist as future SPEC inputs; they agreed on observe-only until 20 trials, a record line per run even when silent, stand-ins before tools, and kill criterion first, differing on order and question timing (approval vs session start). They are inputs, not decisions.

## Decision
1. **Observer (old name "probe") is retired.** Cohesion checks were run here and not wired (grounds: 2/30 non-actionable hits under an evaluator-written profile, plus common substitutes); this is a repository maintenance decision, not refuting the hypothesis on platforms Observer targets. Its Nexus-grounded functions are dropped with it; no reassignment or backlog entry—if Nexus ever needs an impact or grounding surface, that is a Nexus SPEC on its own evidence.
2. **Probe (old name "mutqa") is retired as a tool, on cost:** an unrun tool with a commodity engine. The technical-debt experiment stays open, running engine-direct in two phases with distinct units:
   - Phase 1: `diff-cover` on changed lines for 20 PRs, each uncovered line labelled by a person as `gap`, `intended`, or `dontcare`.
   - Phase 2: mutation testing, survivors labelled by a person as `gap`, `equivalent`, or `dontcare`.
   The threshold for moving from phase 1 to 2 is not set here and must be set before phase 2 starts; no gate occurs before 20 trials. Probe's procedure (deterministic runner separate from judgement; survey → critic → absorb) is kept as a skill text.
3. **The cognitive-debt leg stays the centre of the mission and stays open.** Adept (old name "ken") is archived; [[ADR-0003]]'s tier clause "vouched via ken" is unimplemented from this record on (not retracted), and no artifact is currently vouched; cognitive-debt coverage and the orphan list are not produced. Per [[ADR-0002]] gate ⓐ, the only construction permitted before the gate fires is ⓐ's first sub-step, a comprehension log; its design, question source, grading, hash semantics (Arbiter's `content_hash` over governed content vs git blob hash over the whole file are different things and must not be conflated), single-person limits (author = subject = grader; "across people" is untestable by one person), and kill criteria belong to the direction's first SPEC after the director declares the gate.
4. **Register as read from this record:**
   - Technical debt: no tool (experiment open, engine-direct).
   - Intent debt: Arbiter (unchanged).
   - Cognitive debt: open, no tool, gate ⓐ not yet declared fired.
   [[ADR-0004]]'s rows for Observer ("Probe" row), Probe ("mutqa" row), and Adept ("ken" row) are historical.

## Consequences
- README Status in archived repositories (`khala-labs/observer`, `khala-labs/probe`, `khala-labs/adept`) must carry the conclusion: Observer was run here, not wired, retired; Probe is retired, procedure kept as skill; Adept is archived, hypothesis open under [[ADR-0002]] gate ⓐ. This needs the owner to un-archive briefly. Completion criterion: sentence present in each README; no date set.
- [[ADR-0003]]'s "vouched via ken" clause reads as unimplemented until a successor SPEC says otherwise.
- The lab rule recorded: a tool whose hypothesis was never run is a cost, not an asset; "built once, never run twice" is a failure of the insertion point, so the fix is where the instrument bites, not more instrument.

## Open items this record deliberately leaves
- Whether and when the director declares [[ADR-0002]] gate ⓐ fired.
- Whether the Probe experiment is ever run and at what phase-1 → phase-2 threshold.
- Whether the new partner project that replaced the previous one supplies a service graph that would make Nexus-grounded review worth a SPEC.
- The stale relative link in accepted [[ADR-0008]] to `../nexus/scripts/adr0008_nori_recall.py`, which no longer resolves from `records/adr/` and is not edited because the body is stamped.
