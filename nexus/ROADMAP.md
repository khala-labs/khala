# Khala — Roadmap

> 최종 갱신: 2026-11-11 (이전 판: 2026-06-19)

이 문서는 팀 채택을 목표로 했던 이전 판(2026-06-19 갱신) 이후의 리포 분리·도구 정리·목적 정정을 반영하여 실험 단위로 다시 쓴 Khala 의 2026-11-11 로드맵이다. 본문의 사실은 2026-11-11 기준 master 코드, `records/`(ADR·SPEC·감사), `OPEN.md` 에서 확인했으며, 열린 항목 수의 정본인 `OPEN.md` 의 수를 베끼지 않는다.

## 목적

Khala 는 소유자가 RAG 와 LLMOps 를 직접 구현하며 정말 운영 가능한 형태로 만들 수 있는지 실험하고 증명하는 실험실이다(2026-11-08 「khala 는 실험실이다」). 결정 기준은 채택 수나 소비자 수가 아니라 「실험이 더 잘 보이고, 더 잘 증명되는가」이며, 「소비자가 생기면 그때」 같은 채택 트리거로 결정을 미루지 않는다. 각 실험은 무엇을 만들었고, 무엇이 증명·반증됐고, 다음에 무엇을 시도하는지로 적으며, 끝난 실험은 결론을 적고 archive 한다. 반증도 결과다.

### 지금 검증하는 가설

| 가설 | 어디서 검증하나 |
|------|------|
| RAG 답변을 **근거에 묶어 둘 수 있다** — 근거 없는 답은 내지 않고, 인용·숫자는 코드가 확인한다 | Nexus 답변 경로 (코드에 있음) |
| 한국어 조직 문서에서 하이브리드 검색과 평가를 **결정론적으로** 운영할 수 있다 | Nexus 검색 · 한국어 평가 하니스 (코드에 있음) |
| 실패한 답변 하나가 라벨 → 수정 → 버전 비교까지 **한 바퀴 도는 개선 루프**를 만들 수 있다 | `SPEC-nexus-improvement-loop` (승인 대기) |
| 전체 조직이 하나의 RAG 를 공유하는 것보다 **팀별로 맞춘 RAG** 가 낫다 | 팀별 검색 프로파일 (미착수, 두 번째 테넌트 필요) |

---

## 실험대와 도구

2026-11-08 리포 분리를 거쳐 2026-11-10 소유자가 `khala-labs/khala`를 정본으로 정했다. 옛 리포 `LivingLikeKrillin/khala`는 PR 이력(#1~#584)을 보존하고 있다.

| 리포 | 역할 | 상태 |
|------|------|------|
| **khala-labs/khala** | Nexus(답변 근거 기반 지식 검색) + 문서 사이트 + `records/`(ADR·SPEC·감사·조사) | 정본(2026-11-10). Nexus 배포 없음(2026-11-11 기준, 마지막 데이터는 2026-11-10 DB 덤프) |
| **khala-labs/arbiter** | ADR·SPEC 사전 승인 게이트(record → critique → disposition → approve, 승인 시 SHA-256 잠금). khala CI 가 git 으로 설치한다 | 사용 중 |
| **khala-labs/observer** | 플랫폼 인식 PR 분석 + API 규격 diff | archived. ADR-0011 이 접는다 |
| **khala-labs/probe** | AST 변이 테스트 하니스 | archived. 도구는 접고 실험은 engine-direct 로 열어 둔다(ADR-0011) |
| **khala-labs/adept** | 인지 부채 측정(Vouch 커버리지) + 웹 콘솔 | archived. 인지 부채 칸은 도구 없이 열려 있다(ADR-0011) |

**Archon** 은 별도 도구가 아니라 Nexus 내장 모듈(`nexus/nexus/claims`)이다 — 질의 시점에 소스 코드 상수에서 값을 판독한다.

---

## RAG 실험 — 만든 것과 결과

RAG 에서 코드에 있는 것과 반증된 결과를 함께 적는다. 평가 라벨을 문서 저자가 직접 써서 점수가 천장에 붙는 한계가 있다.

| 실험 | 만든 것 | 결과 |
|------|------|------|
| 하이브리드 검색 | BM25(mecab-ko) + 벡터 **두 경로**를 RRF(`k=60`)로 융합. 그래프는 융합 밖에서 `result.graph` 로 붙는 보강 | 코드에 있음 |
| 한국어 임베딩 교체 | `nomic-embed-text`(768) → `KURE-v1`(1024). 세대를 DB 에 선언하면 어긋난 적재를 거부한다 | KURE-v1 이 마지막 배포의 세대(ADR-0009) |
| 근거 검증 | 인용·숫자를 evidence packet 과 코드로 대조, 해소 안 되면 `unverified_citations` | 코드에 있음 |
| 기권 | 근거 0건이면 LLM 을 부르지 않는다(`abstained`, `no_evidence`) | 코드에 있음 |
| 코드 값 대조 (Archon) | 문서 값 옆에 코드 상수 값과 소유자 판정(`ruled_*`)을 붙인다(#553) | 코드에 있음 |
| 문서 엔티티 GraphRAG | gazetteer 추출 그래프 | **내림.** 유지 대상은 OTel 설계-관측 이중 그래프 |
| 검색 품질 기법 7종 | 2홉 결합 · 모델 재구성 · 빈도 PRF · IDF 확장 · 답변 계약 · 메타데이터 리랭킹 · 코퍼스 합치기 | **7전 7패**(2026-08-25 ~ 09-19). 올린 것은 결함 제거뿐 |
| 문서 합의 융합 (F1) | fusion 이 문서 일치를 세는 요청 플래그(#570) | **기각** — 사전 등록 규칙으로(#571) |
| 평가 하니스 | 한국어 답변 채점기 · 라벨 저술 검사 · 사전 등록 판정식 · 지정 평가 코퍼스 검사 (CI) | 코드에 있음(CI). 라벨을 문서 저자가 직접 써서 점수가 천장에 붙는다 |

---

## LLMOps 실험 — 지금 있는 것과 빈 곳

버전 구분(`prompt_version`·코퍼스 버전·검색 스택 지문)과 개발 지출 차단(키리스 브리지)은 있으나 모델 id 미기록, 비용·토큰 칸 비어 있음, 라이브 LLM 심판 없음, 릴리스 파이프라인 없음, 드리프트 감시 없음으로 비어 있는 곳이 있다. 이 상태를 정리한 2026-11-02 LLMOps 재평가 보고서는 옛 리포 PR #584 에 머지되지 않은 채 있다. 그 보고서의 결론 중 하나는 질의가 주 몇 건이라 어떤 관측 도구도 보여 줄 것이 없다는 점이다.

| 축 | 지금 상태 |
|------|------|
| 버전 구분 | 답변마다 `prompt_version` · 코퍼스 버전 · 검색 스택 지문(`search_fingerprint`)이 붙는다(#558 · #562) |
| 질의 기록 | `search_log` 는 질의 원문 없이 `query_sha256` · `query_len` 만 남긴다. 원문은 옵트인한 테넌트만 `search_query_text` 에 보존(migration 017) |
| 단계 시간 | `search_span` 저장소 + `/search/explain`. 화면은 없다 |
| 비용·토큰 | `search_log` 에 칸(migration 006)은 있으나 **비어 있다** — 키리스 브리지가 usage 를 주지 않는다 |
| 모델 id | **기록하지 않는다** |
| LLM 심판 | 라이브 충분성 판정은 한 번도 켜지지 않아 되돌렸다(ADR-0012). 오프라인 하니스 `--sufficiency` 만 남았다 |
| 피드백 | 👍/👎 투표가 있다. 표본 2건(`OPEN.md` H3) |
| 임베딩 세대 | 선언 게이트가 어긋난 적재를 거부한다. 드리프트 감시(canary)는 없다 |
| 릴리스 | 릴리스 파이프라인이 없다. 마지막 배포(2026-11-10 까지)는 메인 체크아웃을 `--reload` 로 읽었다. 지금은 배포 없음(2026-11-11 기준, 마지막 데이터는 2026-11-10 DB 덤프) |
| 개발 지출 | 키리스 브리지(`NEXUS_LLM_PROVIDER=claude-code`)로 개발 실행에 돈을 쓰지 않는다 |

---

## 다음 실험

다음 실험 표의 순서는 이 문서가 제안하는 순서이고 소유자가 바꿀 수 있다. 1번 개선 폐루프는 SPEC 4판이 이미 있고 승인만 기다려 가장 앞서며, 2번 LLM 호출 기록(모델 id 등)은 개선 루프가 「전후를 버전으로 가른다」 할 때 어떤 모델이 답했는지가 기록에 없으면 비교가 비기 때문에 바로 뒤에 둔다. 개선 폐루프의 목표는 실제 질문 하나가 👎 또는 기권 → 라벨 → 변경이 `prompt_version` 을 바꿈 → 새 버전에서 그 라벨이 통과 → 전후가 버전으로 갈라 보이는 한 가닥을 실제 트래픽으로 한 번 관통시키는 것이다.

| 순서 | 실험 | 첫 단계 | 상태 |
|------|------|------|------|
| 1 | **개선 폐루프** (`SPEC-nexus-improvement-loop` 4판) | U1 유입: 에이전트 principal 의 질의 원문 보존 · `v_search_health` 테넌트 차원. U1 뒤 2주 판정(주 10건)에 못 미치면 U2 이하는 착수하지 않는다 | 승인 대기. 옛 리포 PR #583 에 있고 새 리포에 다시 열어야 한다 |
| 2 | **LLM 호출 기록** | `search_log` 에 모델 id · 가격표 불일치를 `/status` 에 표시 · `/version` 엔드포인트 · 브리지 usage(브리지가 낼 수 있는지 미검증) | 제안(LLMOps 재평가, 옛 리포 PR #584) |
| 3 | **결정론 canary** | 고정 질의의 검색 결과가 바뀌면 알린다 — 임베딩·코퍼스 드리프트 감시 | 제안(같은 보고서) |
| 4 | **팀별 검색 프로파일** | 두 번째 테넌트(새 프로젝트)에서 tenant별 BM25/벡터 가중치를 시험한다 | 미착수. 새 프로젝트 이름·경로 미확인 |
| — | 기술 부채 (Probe engine-direct) | `diff-cover` 20 PR → 변이 테스트 | 열려 있음, 착수 안 함 |

**하지 않기로 한 것 (LLMOps):** 트레이싱 플랫폼(Langfuse 등)은 들이지 않는다 — 질의가 주 몇 건이라 볼 것이 없고, 대신 신호 칸을 `gen_ai.*` 어휘에 맞춰 둔다. LLM 심판을 검증 없이 라이브에 두지 않는다. 한국어 충실도 분류기는 검증 없이 쓰지 않는다.

---

## 걸려 있는 일

| 항목 | 상태 | 누가 |
|------|------|------|
| `SPEC-nexus-improvement-loop` 승인 · 새 리포에 PR 다시 열기 | 위 「다음 실험」 1 | 소유자 |
| ADR-0011 (Observer·Probe 접음, Adept archive) | `in_review`, 비평 21건 처분 완료 | 소유자 승인 |
| ADR-0012 (충분성 신호 되돌림, migration 052) | `in_review`, 코드는 master 에 머지됨 | 소유자 승인 |
| `OPEN.md` H3 (피드백 표본 2건) | 달력 트리거 2026-11-12. §5 의 마지막 선언이라 닫을 때 선언을 남기거나 규칙을 같이 고친다 | 다음 회차 |
| `OPEN.md` H1 · H27 (자격증명 회전) | 대기. 리포 밖이라 리포에서 확인할 수 없다 | 소유자 |
| 인지 부채 (ADR-0002 게이트 ⓐ) | 선언 안 됨. 선언 전 허용되는 것은 이해도 로그 하나 | 소유자 선언 |

---

## 접은 도구 — ADR-0011 (in_review)

ADR-0011은 Observer를 접고, Probe 도구를 접되 기술 부채 실험은 engine-direct로 열어 두며, Adept를 archive 하고 인지 부채 칸은 도구 없이 열어 두었다. 이에 따라 기술 부채는 도구 없음(실험 열림), 의도 부채는 Arbiter, 인지 부채는 열림, 도구 없음으로 배정됐다. 가설을 한 번도 돌리지 않은 도구는 자산이 아니라 비용이며, 「한 번 만들고 두 번 안 돌린 것」은 끼워 넣은 자리의 실패이므로 고칠 것은 도구를 더 만드는 것이 아니라 도구가 실제로 작동할 자리라는 것이 ADR-0011이 기록한 실험실 규칙이다.

| 도구 | 완료된 것 | 결론 |
|------|------|------|
| **Observer** | v0.1 플랫폼 인식 PR 범위 분석 · v0.2 API 규격 린트/diff · v0.3 MCP 서버 · v0.4 Nexus 연동. 2026-06 로드맵의 v0.5(UI 확장팩)·v0.6(팀별 린트 프로파일)은 코드에 없다(패키지 버전 문자열만 0.6.0) | 2026-11-08 회고: 머지 PR 30건에 응집 규칙만 7%(2/30), 사전 기준 10~60% 미달 → CI 배선 안 함. 접는다. 가설 반증이 아니라 이 리포의 유지 결정 |
| **Probe** | AST 변이 하니스(`cosmic-ray` 래핑), 생존 변이체 판정 기록 | 도구는 비용으로 접는다. 실험은 engine-direct 로 열어 두고 절차는 스킬 문서로 남긴다 |
| **Adept** | Vouch 커버리지 측정 + 웹 콘솔. 실사용 1회(2026-07-02) | archive. ADR-0003 의 「vouched via ken」은 미구현으로 읽는다 |

---

## 부록 — 2026-06 페이즈 계획의 상태

이전 판의 Phase 1(팀 맞춤형)·Phase 2(검색 지능화)·Phase 3(거버넌스)은 2026-06 에 조직 채택을 전제로 짠 계획이었으나, 2026-11-11 코드 대조 결과 대부분 미착수였고 JWT 인증은 다른 설계(불투명 bearer 토큰)로 이미 출하됐다. 이번 판은 이 계획을 부록으로 내리고, 그중 팀별 검색 프로파일만 「다음 실험」 4번으로 옮겼다.

| 페이즈 | 항목 | 상태 | 근거 |
|------|------|------|------|
| 1 팀 맞춤형 | tenant별 검색 프로파일 | 미착수 → 「다음 실험」 4 | `config.yaml` 에 tenant별 가중치가 없다. 융합 가중치는 질의 채널 단위 |
| 1 | tenant별 문서 풀 격리 | 부분 | 테넌트 격리는 있다. 토큰의 `read_tenants` 로 여러 테넌트를 함께 읽는다. 「공유 문서 풀」 개념은 없다 |
| 1 | 역할별 결과 reranking | 미착수 | principal 에 roles 가 없다 |
| 1 | tenant 설정 관리 | 부분 | `config.yaml` 의 auth 블록이 토큰을 tenant 에 묶는다. 검색 프로파일은 없다 |
| 2 검색 지능화 | Adaptive 검색 깊이 | 미착수 | `search/router.py` 는 키워드·엔티티 수 규칙으로 route 셋(`hybrid_only` · `hybrid_then_graph` · `graph_then_hybrid`) 중 하나를 고른다. 깊이 단계가 아니다 |
| 2 | Cross-Encoder Reranking | 미착수 | 2026-09-19 실측에서 bge 리랭커 미도입 |
| 3 거버넌스 | JWT 인증/인가 | 다른 설계로 출하 | JWT 가 아니라 불투명 bearer 토큰. 토큰 하나 = 고정된 `(tenant, clearance)`, 요청은 범위를 좁히기만 한다 |
| 3 | 감사 추적 | 부분 | `search_log` 가 질의를 기록한다. A2A 는 `a2a/audit.py` |
| 3 | tenant 관리 UI | 미착수 | 소스 루트 관리 API(`/roots`)는 있다. 테넌트 프로파일 화면은 없다 |

보류였던 항목: **Context Engine 3계층**은 그대로 보류. **Neo4j 전환**은 하지 않는다(의존성 추가 금지, `GraphRepository` 뒤에 있음). **도메인 특화 임베딩**은 KURE-v1 교체로 출하됐다(ADR-0009).

---

## 동향 분석 — 흡수/제외 근거

2026년 RAG 동향을 조사하여, Nexus 방향성과 일치하되 꼭 필요한 컨셉만 흡수한다.

### 흡수

| 동향 | 반영 위치 | 근거 |
|------|----------|------|
| **Vertical/Domain-specific RAG** | 다음 실험 4 (미착수) | 범용 RAG보다 도메인 맞춤형이 성능 차이가 큼. tenant별 프로파일로 구현 |
| **역할별 검색 프로파일** | 2026-06 Phase 1 (미착수) | 같은 쿼리에 재무분석가와 법무팀이 다른 결과를 받는 패턴. reranking으로 구현 |
| **Adaptive RAG** | 2026-06 Phase 2 (미착수) | 쿼리 복잡도별 검색 깊이 동적 조정. 비용 30-40% 절감 벤치마크 |

### 제외

| 동향 | 근거 |
|------|------|
| **Agentic RAG** (LLM in search loop) | "System decides, LLM narrates" 원칙과 충돌. 검색 판정에 LLM을 넣으면 비결정적 + 비용 급증 |
| **PageIndex Tree Search** | 구조화된 장문 문서(금융 보고서, 법률 문서)에 최적화. Nexus는 팀 문서 100-500개 규모에 Hybrid로 이미 충분 |
| **Self-RAG** (자체 신뢰도 평가) | Nexus는 evidence 필수 + quarantine 원칙이 아키텍처 수준에서 할루시네이션을 방지. 별도 자기평가 계층 불필요. 라이브 충분성 판정 칸도 한 번도 켜지지 않아 되돌렸다(ADR-0012) |
| **GraphRAG Global/Community Search** (Leiden 커뮤니티 탐지 + community report) | 수백만 문서 코퍼스용 기능. 100-500개 규모에서는 커뮤니티가 너무 작아 무의미하다. 결정적으로 community report는 *LLM이 생성한 비그라운디드 파생 요약*이라 "Nexus는 인덱스지 저장소가 아니다" + "evidence 없는 것은 없는 것" 두 원칙과 정면 충돌. **의식적 배제** |
| **LLM 기반 그래프 추출** (gazetteer 대체) | 질의/색인 파이프라인에 LLM 추출을 넣는 것은 "System decides, LLM narrates" + 결정성 + air-gap 원칙 위반. 규칙 기반 gazetteer 추출을 유지한다 |

> **Neo4j 전환**도 동향(그래프 DB 기반 GraphRAG)에 해당하나 하지 않는다 — 의존성을 늘리지 않는 규칙(`nexus/CLAUDE.md`)이 있고, `GraphRepository` Protocol 이 추상화해 두었다.

### GraphRAG 정렬 평가 (2026)

Microsoft GraphRAG가 사실상 표준을 정의한 뒤(LLM 추출 → Leiden 커뮤니티 → 계층 요약 → Local/Global/DRIFT search),
Nexus의 그래프 계층을 그 베이스라인과 대조한 결과를 **의식적 결정으로** 기록한다.

| 차원 | 상태 | 비고 |
|----|------|------|
| Local search (엔티티 중심 k-hop) | 정렬 | `get_neighbors` 2-hop이 Microsoft local search 패턴과 동형. 감지된 엔티티 최대 5개에서 탐색한다 |
| Hybrid (BM25+Vector, RRF) | 정렬 | 한국어 형태소까지 포함. 그래프는 RRF 에 들어가지 않는 보강이다 |
| Evidence-bound edge / 추적성 | **앞섬** | 모든 edge가 source chunk에 바인딩 |
| 설계-관측 이중 그래프 (OTel) | **독자적 우위** | 메인스트림 GraphRAG에 등가물 없음. 런타임 관측을 그래프에 결합 |

> 이전 판의 「무조건 개선 — 멀티-엔티티 그래프 탐색」은 이미 되어 있다: `hybrid_search` 는 `entity_rids[:graph_max_entities]` 전부에서 탐색하고 `graph_hops` 는 설정이다. 이전 판의 「demand-pull 게이트 항목」(그래프 근접도 RRF 반영 · gazetteer 오프라인 제안 도구)은 소비자 신호를 기다리는 형식이라 실험으로 열지 닫을지 다시 정한다.

### 참고 자료

- [10 RAG Architectures in 2026](https://www.techment.com/blogs/rag-architectures-enterprise-use-cases-2026/)
- [From RAG to Context (RAGFlow)](https://ragflow.io/blog/rag-review-2025-from-rag-to-context)
- [Enterprise Knowledge Systems 2026-2030 (NStarX)](https://nstarxinc.com/blog/the-next-frontier-of-rag-how-enterprise-knowledge-systems-will-evolve-2026-2030/)
- [Hybrid Tree Search (PageIndex)](https://docs.pageindex.ai/tutorials/tree-search/hybrid)
- [Microsoft GraphRAG — Local/Global search & Leiden communities](https://microsoft.github.io/graphrag/)
- [Global Community Summary Retriever (graphrag.com)](https://graphrag.com/reference/graphrag/global-community-summary-retriever/)

---

## 핵심 원칙

1. **Grounded answers only** — 답변 근거 없는 답변은 제공하지 않는다
2. **System decides, LLM narrates** — 접근 통제/분류/검색 경로는 코드가 결정. LLM은 요약만
3. **팀 맞춤형 > 범용** — 전체 조직이 하나의 설정을 공유하는 것은 비효율적이다
4. **정상일 때는 조용히** — 노이즈는 신뢰를 죽인다
5. **돌리지 않은 도구는 비용이다** — 가설을 한 번도 돌리지 않은 도구는 비용이며, 끝난 실험은 결론을 적고 archive 한다(ADR-0011). (이전 판의 원칙 5 「없어도 동작, 있으면 풍부 — Observer 는 Nexus 없이도 100% 동작한다」는 Observer가 접혀 낡았다.)

---

## 소유자가 정할 것

이 문서가 정하지 않고 소유자가 정할 것은 다음 여섯 가지다.
1. 다음 실험의 순서.
2. `SPEC-nexus-improvement-loop` 승인과, 옛 리포의 열린 PR 셋(#583 · #584 · #556)을 새 리포에 다시 열지.
3. 개선 루프와 팀별 프로파일의 테스트 기반이 될 새 프로젝트의 이름과 경로.
4. ADR-0011 · ADR-0012 승인.
5. 부록의 2026-06 페이즈 항목 중 다시 실험으로 올릴 것이 있는지.
6. 이전 판의 demand-pull 게이트 항목 둘(그래프 근접도를 RRF 에 반영, gazetteer 후보 오프라인 제안 도구)을 실험으로 열지 닫을지.
