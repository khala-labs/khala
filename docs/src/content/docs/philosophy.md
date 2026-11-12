---
title: Philosophy
description: The calibration architectural thesis behind Khala.
---

*Khala does not promise absolute correctness. It guarantees **calibration**: aligning system confidence strictly with observable, verifiable evidence and blocking ungrounded assertions.*

## The Architecture Backbone (Khala Link)

Khala is the shared knowledge and governance backbone that unifies independent engineering tools (Nexus, Archon, Arbiter) under standardized calibration contracts. Khala is not an independent runnable CLI; it is the protocol and interoperability layer connecting these tools. It enforces that all components operate against a single substrate of grounded knowledge and explicitly state the provenance and uncertainty bounds of their outputs.

Large language models (LLMs) exhibit high fluency regardless of factual grounding, generating confident outputs in the absence of verified premises. In engineering pipelines, this leads to two critical failure modes that single-purpose tools fail to address concurrently. Khala is architected to deterministically defend against both.

## Four Information Domains on a Governed Substrate

Khala ensures that software engineers and autonomous coding agents operate from the **same single source of truth**. Engineering knowledge is structured into four distinct domains with different lifecycles and mutation dynamics:

1. **Domain & Organizational Knowledge** — Specifications, design documents, operational policies, runbooks. Persisted in a unified corpus and accessed identically by humans (Web UI) and agents (MCP/A2A contracts). (**Nexus**)
2. **Architectural & Design Decisions** — Architecture Decision Records (ADR/SDD). Automatically records micro-decisions made by agents while requiring human sign-off for accountable approval gates. (**Arbiter**)
3. **Runtime Telemetry & State** — Distributed traces, metrics, logs. Combines live telemetry with approved knowledge into structured evidence packets for PR review and incident root-cause analysis. (**Nexus**, OTel aggregation)
4. **System Comprehension & Cognitive Debt** — Structural debt metrics. Measures the divergence between codebase complexity and human verification coverage. No tool measures this today, and ADR-0011 keeps it open.

## Failure Mode 1 — Model Hallucination & Ungrounded Assertion

The first failure mode occurs when generative models assert obsolete or fabricated domain logic with maximum confidence. When queried regarding domain invariants, business rules, or status codes, models often synthesize plausible yet erroneous answers.

- **Archon** establishes an authority window directly over codebase constants and domain invariants, resolving truth deterministically from static code declarations.
- **Nexus** implements multi-path retrieval and deterministically abstains with a fixed message when no evidence snippets are retrieved. Citation source-matching and the groundedness of the numbers in an answer are both verified deterministically after generation and returned as response values rather than gating abstention; only the citation side is aggregated, as an unverified-citation rate.

## Failure Mode 2 — Human Rubber-Stamping

The second failure mode arises when human reviewers, overwhelmed by high-volume agent-generated diffs and specifications, approve changes without critical verification, collapsing the quality gate.

- **Arbiter** elevates architecture decisions and specifications into formal pre-implementation gates. By cryptographically stamping content hashes, timestamps, and named human approvers into decision ledgers, it enforces full accountability and auditability across all code changes.

## Latent Quality Defect — Superficial Test Coverage

Automatically generated test suites can report high line coverage while asserting trivial conditions, skipping execution checks, or over-mocking critical subsystems.

- No tool covers this today, and ADR-0011 keeps the experiment open, run directly with an off-the-shelf engine.

## The Calibration Thesis

All tools across the Khala ecosystem enforce **calibration** as an architectural invariant:

- **Archon** binds domain claims to verified static code constants.
- **Nexus** binds generative answers to verified evidence packets.
- **Arbiter** binds architectural approval to attributable decision ledgers.

## Calibration Role Matrix

| Tool Identifier | Architectural Role | Calibrated Domain | Target Consumers | Khala Topology | Execution Trigger |
|---|---|---|---|---|---|
| **Nexus** | Grounded Knowledge Base | Domain Knowledge & Telemetry (No source → Abstain) | All Engineers & Agents | Central Substrate | On-demand queries |
| **Archon** | Domain Invariants Authority | System Constants & Business Rules | Planners, Architects, Agents | Invariant Provider | On-demand queries |
| **Arbiter** | Decision & Spec Ledger | Architectural Design & Approval Integrity | Decision Makers | Spec Provider | Pre-implementation gate |

## Inter-Tool Topology

<img
  src="/khala/diagrams/ecosystem.svg"
  alt="Khala ecosystem topology: Fragmented sources (docs, specs, traces, configs) flow into one governed link; humans and agents query the same shared view."
  style="max-width: 100%; height: auto; display: block; margin: 1.5rem auto;"
/>

Khala enforces a decoupled hub-and-spoke topology: producer tools never invoke each other directly. All interactions flow through the **Khala substrate**:
- **Archon** and **Arbiter** publish verified constants and approved specifications into the substrate.
- [**Archon**](/tools/archon/) provides a deterministic API for invariant lookup.
