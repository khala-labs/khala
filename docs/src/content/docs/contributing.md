---
title: Contributing
description: For future collaborators and open-source contributors.
---

The docs and the tools are built in the open. Contribution happens in the [Khala repository](https://github.com/khala-labs/khala) (`nexus/`, `docs/`, `records/`), where you can open issues and pull requests; Arbiter lives in its own [repository](https://github.com/khala-labs/arbiter).

Repository conventions — terminology, naming, per-tool versioning, dependencies — are in [CONVENTIONS.md](https://github.com/khala-labs/khala/blob/master/CONVENTIONS.md); the terms are in `GLOSSARY.md` and `docs/glossary.md`. Commit messages and pull request descriptions follow one rule shared by every repository in the organization: [CONTRIBUTING.md in khala-labs/.github](https://github.com/khala-labs/.github/blob/main/CONTRIBUTING.md).

Before opening a pull request, run the test suite and the repository guards locally: `check_readme_counts.py`, `check_terms.py`, `check_svg_fit.py`, `ledger_integrity.py`, and `fingerprint_scan.py` after `git add`. A formal contribution flow for the docs site will be written here later; until then, open a discussion in the relevant repository.
