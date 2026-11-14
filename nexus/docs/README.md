# Nexus 문서

## 설계 · 규격

- `nexus-mvp-design.md` — MVP 설계 문서. 10일 시범 구축 때의 설계 기록이며, 이후 바뀐 것은 문서 머리 주석에 있다
- `API_CONTRACT.md` — API 계약서
- `PIPELINE_SPEC.md` — 파이프라인 상세
- `UI_INTEGRATION.md` — Web UI 연동 규격

## 가이드 · 런북

- `SLACK_BOT.md` — Slack Bot 설정 가이드
- `MCP_SERVER.md` — MCP Server 설정 가이드
- `TEAM_DOGFOOD_DEPLOY.md` — 로컬 + Cloudflare Tunnel 팀 배포 런북

## 품질 · 측정 기록

날짜가 박힌 기록이다. 본문은 그날의 사실로 두고, 뒤에 바뀐 것은 머리에 「이후 바뀜」 주석으로 단다.

- `KOREAN_SEARCH_QUALITY.md` — 한국어 검색 품질: 평가셋(코퍼스·라벨·판정 규칙)과 그 평가 하니스가 잡아낸 프로덕션 결함들, 각각의 적용 방법
- `BM25_POOL_PREREGISTRATION.md` — BM25 후보 풀 크기 사전 등록 (2026-09-02)
- `MULTIHOP_ASSEMBLY_PREREGISTRATION.md` — 멀티홉 조립 사전 등록 (2026-09-02)
- `PROCEDURE_RETRIEVAL_PREREGISTRATION.md` · `PROCEDURE_RETRIEVAL_T2_REGRESSION.md` — 사례 분류로 절차 문서 찾기: 사전 등록과 T2 회귀 측정 (2026-09-20)
- `FUSION_DOCUMENT_AGREEMENT_PREREGISTRATION.md` · `FUSION_DOCUMENT_AGREEMENT_REGRESSION.md` — 문서 합의 융합(F1): 사전 등록과 측정, 기각 (2026-10-01)
- `CODE_CARD_REPRODUCIBILITY.md` — 코드 카드 재현성 측정 (`SPEC-nexus-code-semantic-cards`)
- `EMPTY_OR_FAILED_READBACK_AUDIT.md` — 빈 것과 터진 것이 같은 값으로 나오는 자리 감사 (2026-09-22)
