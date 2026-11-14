---
title: 기여 가이드
description: Khala 오픈소스 생태계 기여 절차 및 컨벤션 안내.
---

문서와 도구는 공개적으로 개발됩니다. 기여는 이슈와 풀 리퀘스트를 열 수 있는 [Khala 저장소](https://github.com/khala-labs/khala)(`nexus/`, `docs/`, `records/`)에서 진행되며, Arbiter는 자체 [저장소](https://github.com/khala-labs/arbiter)에 있습니다.

용어, 명명 규칙, 도구별 버전 관리, 의존성을 다루는 저장소 규칙은 [CONVENTIONS.md](https://github.com/khala-labs/khala/blob/master/CONVENTIONS.md)에 있으며, 용어는 `GLOSSARY.md`와 `docs/glossary.md`에 정리되어 있습니다. 커밋 메시지와 풀 리퀘스트 설명은 조직 내 모든 저장소가 공유하는 단일 규칙인 [khala-labs/.github의 CONTRIBUTING.md](https://github.com/khala-labs/.github/blob/main/CONTRIBUTING.md)를 따릅니다.

풀 리퀘스트를 열기 전에 로컬에서 테스트 스위트와 저장소 가드를 실행해야 합니다. `check_readme_counts.py`, `check_terms.py`, `check_svg_fit.py`, `ledger_integrity.py`를 실행하고 `git add` 후 `fingerprint_scan.py`를 실행하시기 바랍니다. 문서 사이트를 위한 공식 기여 절차는 추후 이곳에 작성될 예정이며, 그전까지는 관련 저장소에서 토론을 열어 주십시오.
