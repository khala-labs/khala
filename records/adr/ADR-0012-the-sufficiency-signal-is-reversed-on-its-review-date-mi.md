---
id: ADR-0012
type: adr
title: 'The sufficiency signal is reversed on its review date: migration 012 undone,
  no consumer gate declared'
status: in_review
resolves: SPEC-nexus-sufficiency-signal
linked_adrs:
- ADR-0002
- ADR-0006
date: '2026-11-10T12:46:17Z'
---
# The sufficiency signal is reversed on its review date: migration 012 undone, no consumer gate declared

## Status
Proposed. Successor record to `SPEC-nexus-sufficiency-signal` (status approved, body frozen by `content_hash`; not edited). Reads against [[ADR-0002]] (three debts; "taste = subtraction"; a gated follow-on backlog) and [[ADR-0006]] (the SPEC's other linked ADR). None of the three is edited; this record is what a reader consults from now on for the sufficiency signal.

## Date
2026-11-10

## Context
The SPEC (approved 2026-08) added four columns to `search_log` by migration `012_sufficiency.sql`: `sufficiency`, `sufficiency_at`, `sufficiency_judge`, and `evidence_fingerprint`. A separate LLM judge, off by default and enabled per tenant through `NEXUS_SUFFICIENCY=on` plus allow-list `NEXUS_SUFFICIENCY_TENANTS`, recorded whether retrieved evidence sufficed to answer; no code could branch on the value (§2.2a). Clause §2.2h set a review date, 2026-11-10: declare a consumer gate against a pre-registered threshold, or reverse migration 012. Test 20 specified that the review date "has teeth": a check that fails on or after that date unless a record in `specs/` or `adr/` carries `resolves: SPEC-nexus-sufficiency-signal`. That check was never built: nothing in the repository reads a `resolves:` key. What actually fired on 2026-11-10, in CI, was the repository's dated-trigger check `scripts/check_dated_triggers.py`, which reads the explicit declarations in `OPEN.md` §5.

Measured on the review date in the live database:
- Total `search_log` rows: 2,730 (1,785 written since column creation); judged rows (`sufficient` or `insufficient`): 0.
- Distribution: `not_applicable` 895, `disabled` 890, NULL (older rows) 945.
- The judge was never enabled for any tenant; `sufficiency_judge` was `off` on every instrumented row.
- No code reads the column apart from the signal's own `pending` update.
- No database view depends on the four columns (checked with `pg_depend`).

Two `OPEN.md` items waited on signal enablement: A10 (instrument debts: daily cap `NEXUS_SUFFICIENCY_MAX_PER_DAY` existed only in the SPEC, never in code; `STRANDED_SECONDS = 300` was a module constant a deployment could not raise) and A64 (enable the signal, blocked on A10). Twelve deferred critique issues of the SPEC were counted in `OPEN.md` §4 as "conditional residue" for a follow-on SPEC.

On 2026-11-10, the owner decided in words "012 되돌리기" (reverse 012), choosing §2.2h's second arm without declaring a consumer gate. Ungated observation nobody consumes is the maintenance surface [[ADR-0002]]'s "taste = subtraction" exists to prevent, and the SPEC named this outcome as default when no consumer appears.

## Decision
1. Migration `052_drop_the_sufficiency_signal.sql` drops CHECK constraint `search_log_sufficiency_check` and the four columns idempotently (`DROP ... IF EXISTS`). Migration file 012 stays in the directory because it is part of the applied history in `schema_migrations`; 052 comes after it and undoes it.
2. In `nexus/search/signals.py`, judge plumbing is removed: `JudgeInput` dataclass, eligibility helper `_eligibility`, `_enabled_for`, `evidence_fingerprint()`, concurrency slot (`_try_take_slot`, `_release_slot`, `_inflight`), `_judge_with_timeout`, constants `STRANDED_SECONDS` and `_MAX_TIMEOUT_SECONDS`, four columns in `_insert`, and post-insert `UPDATE ... WHERE sufficiency = 'pending'`. `record_search` loses parameter `judge_input`. Four call sites (`api.py` answer and streaming paths, `cli.py`, `a2a/server.py`) stop building judge inputs. `judge_identity()` is removed from `nexus/llm/sufficiency.py`.
3. The four environment variables `NEXUS_SUFFICIENCY`, `NEXUS_SUFFICIENCY_TENANTS`, `NEXUS_SUFFICIENCY_CONCURRENCY`, and `NEXUS_SUFFICIENCY_TIMEOUT` are no longer read anywhere (the fifth, `NEXUS_SUFFICIENCY_MAX_PER_DAY`, never was).
4. Tests removed: `test_sufficiency_signal.py` (17) and `test_sufficiency_signal_db.py` (12), 29 in total; five tests that collected the judge input or called `_insert` with the old signature are trimmed. `test_sufficiency.py` (9 tests) stays. Added `test_the_sufficiency_signal_is_gone.py`, which asserts the post-state: no module under `nexus/` reads a `NEXUS_SUFFICIENCY*` variable, the insert names none of the four columns, and (against the disposable test database) migration 052 leaves no column and no CHECK and completes a second time without error.
5. What stays, deliberately: judge module `nexus/llm/sufficiency.py` (`judge`, `judge_raw`, `parse`, `build_prompt`) and offline Korean answer-quality harness use (`scripts/ko_eval_answer_run.py --sufficiency`), which grades evidence sufficiency per question and writes a sufficiency × outcome grid into run artifacts. It is an evaluation instrument, not the live signal, and §2.2h does not cover it.
6. `OPEN.md`: H10, A10, and A64 are closed with strikethrough rows naming this record; two fired lines in §5 are removed; twelve `sufficiency-signal` items leave §4 (30 → 18), with a declaration line in §4 pointing here. This record carries the frontmatter key `resolves: SPEC-nexus-sufficiency-signal` because the SPEC named that key as its successor's deliberate act; no check reads it, and the key is a convention, not a mechanism.

## Consequences
- `search_log` rows written after 052 lack sufficiency columns; 1,785 instrumented rows lose those four values upon applying 052 (none held judged values). A `pg_dump` of the live database (custom format, 88.5 MB) taken earlier on 2026-11-10, before this change, sits in the owner's Drive sync folder for this project. It is a copy of the values, not a rollback: re-applying 012 would restore the columns empty.
- Search-stack fingerprinting on answers is unaffected: `search/versions.py::search_fingerprint` (migration 047) was added because `evidence_fingerprint` was written only when the judge was active.
- The abstention question the SPEC was built to inform (`abstention-never-fires`: flag reads false when an answer is absent because BM25 returns results) is not answered here and stays as it was before the SPEC.
- Live deployment apply order, by the owner's agent session on the owner's machine: merge, fast-forward the main checkout (the app reloads with code that no longer references the columns), then `docker compose exec -T nexus-app python -m scripts.migrate`. This inverts the repository's usual migration-first order on purpose: dropping the columns while the old code still runs would make every `search_log` insert fail, and `_persist` swallows that failure (logged as `search.signal.persist_failed`), so the rows would be lost, not refused.
- In the window between the code reload and migration 052, rows are written with NULL in the four columns, which breaks 012's invariant that NULL means "older than the column". The columns are dropped at the end of that window, so no reader can be misled by it afterwards.

## Open items this record deliberately leaves
- Whether evidence sufficiency is ever measured again on the live path. If so, a new SPEC with a named consumer first and a column second is required.
- `OPEN.md` item H3 (feedback sample of two votes; §5.3 review date 2026-11-12) fires in two days under the dated-trigger check; it is a different SPEC and is unaddressed here. It is now the only declaration left in §5, and `check_dated_triggers.py` refuses to judge an empty list (exit 76), so whoever closes H3 must leave a declaration or change that rule in the same change.
- The offline harness's `--sufficiency` grid has no stated owner or cadence; it is retained because it is used, not because this record evaluated it.
