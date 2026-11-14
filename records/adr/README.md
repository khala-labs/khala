# Architecture Decision Records

Ecosystem-level ADRs for Khala—decisions that span more than one tool (Nexus and Arbiter; Observer, Probe, and Adept were tools until ADR-0011). Single-tool decisions live in that tool's own `docs/`.

These ADRs follow the [Arbiter](https://github.com/khala-labs/arbiter) house format
(`ADR-NNNN-<slug>.md`, frontmatter `id/type/title/status/date`) so they can be run
through Arbiter's accountable-review gate (`record` → `critique` →
human disposition → `approve`).

## Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| [ADR-0001](ADR-0001-adopt-a2a-inter-agent-interop.md) | Adopt A2A (Agent2Agent) as Khala's agent-to-agent interoperability layer | Accepted | 2026-06-18 |
| [ADR-0002](ADR-0002-reframe-system-command-debt.md) | Reframe Khala around staying in command of your own system in the AI era | Accepted | 2026-06-23 |
| [ADR-0003](ADR-0003-ai-era-artifact-lifecycle-and-debt-repayment-loop.md) | The AI-era artifact lifecycle and the debt-repayment loop | Accepted | 2026-06-26 |
| [ADR-0004](ADR-0004-component-architecture-grounding-division.md) | Component architecture — grounding division, dual-mode, and dual deployment | Accepted | 2026-06-26 |
| [ADR-0005](ADR-0005-component-naming-rename-and-forward-mapping.md) | Component naming — Protoss-unit rename and forward-mapping layer | Accepted | 2026-06-30 |
| [ADR-0006](ADR-0006-nexus-entropy-spine.md) | Nexus entropy spine | Accepted | 2026-07-01 |
| [ADR-0007](ADR-0007-component-rename-migration-landed.md) | Component rename migration landed — ADR-0005's deferred code/directory rename is complete | Accepted | 2026-07-11 |
| [ADR-0008](ADR-0008-keep-nexus-substrate-defer-onyx-adoption.md) | Keep Nexus's own substrate; defer the Onyx adoption question with named resume conditions | Accepted | 2026-08-01 |
| [ADR-0009](ADR-0009-the-embedding-model-block-of-adr-0008-is-lifted-what-the.md) | The embedding-model block of ADR-0008 is lifted - what the director declared, and what stays open | Accepted | 2026-08-05 |
| [ADR-0010](ADR-0010-machine-read-text-is-evidence-of-a-lower-tier.md) | Machine-read text from images is evidence, of a lower tier — and the tier must travel with it | Accepted | 2026-08-09 |
| [ADR-0011](ADR-0011-the-technical-debt-legs-two-tools-are-retired-and-the-co.md) | The technical-debt leg's two tools are retired, and the cognitive-debt leg stays open without its tool | Accepted | 2026-11-08 |
| [ADR-0012](ADR-0012-the-sufficiency-signal-is-reversed-on-its-review-date-mi.md) | The sufficiency signal is reversed on its review date: migration 012 undone, no consumer gate declared | Accepted | 2026-11-10 |

> **Note on ADR-0011:** ADR-0011 marks ADR-0004's rows for Observer, Probe, and Adept as historical. In ADR-0003, the clause "vouched via ken" reads as unimplemented from ADR-0011 onward (not retracted). The path mappings in ADR-0005 §3 and ADR-0007 describe directories that left this repository on 2026-11-08 for archived organization repositories. Those ADRs remain accepted and unedited; this index is the pointer to current state.

> **Note on ADR-0001:** A2A work was stopped before finding a real consumer. That stop is recorded in ADR-0002, and `OPEN.md` decision D4 keeps its 18 open questions out of the open-item count.

> **Note on ADR-0012:** ADR-0012 reverses `SPEC-nexus-sufficiency-signal` (migration 012 undone). The SPEC remains approved and unedited; read the SPEC together with ADR-0012.

> **Note on ADR-0005 §3:** ADR-0005's interim path/name disambiguation ("path `probe/` = Observer;
> new Probe is still `mutqa/`") is **stale** — the code rename has since landed. [ADR-0007](ADR-0007-component-rename-migration-landed.md)
> records the current state (`probe/` = the mutation tool `khala.probe`; `observer/` = the review
> analyzer `@khala/observer`). Read ADR-0005 §3 as history; ADR-0007 governs the current tree.

> **Note on ADR-0008 §6:** its block on **an embedding-model change** was lifted by the director on
> 2026-08-05 and the KURE-v1 swap shipped; [ADR-0009](ADR-0009-the-embedding-model-block-of-adr-0008-is-lifted-what-the.md)
> records the declaration, the evidence, and what stays open — resume condition (b), the mecab-ko
> third of the block, and two procedural defects in how the swap was gated. ADR-0008 is immutable and
> cannot forward-link, so this index is the pointer. Read ADR-0008 §6 and §2.6 together with ADR-0009.

> **Note on ADR-0009's open items** (director's rulings, 2026-08-05, after
> `SPEC-nexus-ko-eval-pool-sensitivity` and `SPEC-nexus-retrieval-backstop-detector` were approved).
> ADR-0009 is immutable and cannot forward-link, so this index carries the current state:
>
> - **A mechanism that detects backstop events — still OPEN.** Two designs were attempted and both
>   failed on the substrate, not on details (see `SPEC-nexus-retrieval-backstop-detector` §2): a CI
>   diff check cannot identify the governing SPEC because this repo approves before implementing, and
>   an Arbiter gate rule hangs from anchors that are all author-controlled. **A disposition of
>   impossibility does NOT discharge the item** — ADR-0009's other acceptable outcome, "a declaration
>   made after the fact", is cooperative by construction and remains available. The item's trigger
>   (`linked_adrs`) is spent; nothing guarantees another ADR-0008-linked SPEC.
> - **A usable predicate for "materially expand" — still OPEN, and deliberately not built.** ADR-0009
>   §4 makes the trigger a case-by-case director judgement; codifying it invites the boilerplate
>   equilibrium the detector SPEC identified. The practice that replaces it is a `## Backstop record`
>   in the body of any SPEC touching the retrieval stack.
> - **The rollback guard for the post-flip NULL gap — trigger did NOT fire** for
>   `SPEC-nexus-ko-eval-pool-sensitivity`. It touches `ko_eval_embeddings`, an evaluation store in a
>   disposable test database, not the production `embedding` / `embedding_1024` columns (verified
>   2026-08-05: 167/167 on both). The item itself stays open.
> - **Pack B's trigger is superseded.** ADR-0009's table carries "unchanged from ADR-0008 §5(b)";
>   `nexus/docs/KOREAN_SEARCH_QUALITY.md` §6.1 replaces the build trigger with a counted one —
>   **100 active documents** — because at today's 20, with a 10-document window, the random-ranker
>   `Recall@10` floor is 0.500 and any comparison returns "underpowered", which by ADR-0009's own
>   wording does not discharge the obligation. **ADR-0008 §5(b) itself is unchanged.**
> - **One implementation deviates from an approved SPEC.** `SPEC-nexus-ko-eval-pool-sensitivity` §5.3
>   specifies that `clean_db` truncate the eval store; the implementation preserves it by default and
>   makes destruction opt-in. Reasons in `KOREAN_SEARCH_QUALITY.md` §6.2. A successor record is owed.

## Statuses

- **proposed** — under discussion / awaiting review
- **in_review** — critique opened, dispositions pending
- **accepted** — approved and content-hash stamped (immutable)
- **superseded** — replaced by a later ADR
- **deprecated** — no longer relevant

> **Which status is authoritative.** The **ledger's frontmatter** is — this index reflects it. An
> ADR's *body* carries the status it was written with, and because accepted bodies are frozen the two
> cannot be reconciled by editing: most accepted ADRs still say "Proposed" (or "In review") in their
> body text. Arbiter enforces the immutability mechanically — editing an accepted artifact makes it
> report `tampered`, which is how an in-place amendment of ADR-0008 was caught on 2026-08-05.
> Amendments are carried by a successor record (ADR-0007 → ADR-0005, ADR-0009 → ADR-0008).
