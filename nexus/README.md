<p align="center">
  <img src="logo.png" alt="Nexus" width="180" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Korean_NLP-mecab--ko-FF6F00?style=for-the-badge" />
</p>

<h1 align="center">Nexus</h1>

<p align="center">
  <strong>Grounded Enterprise RAG for Knowledge Retrieval</strong><br/>
  문서 기반 설계와 OTel 기반 관측을 결합하여, 답변 근거 있는 답변만 제공하는 지식 검색 시스템
</p>

<p align="center">
  <img src="docs/img/nexus-demo.gif" alt="Nexus — 답변 근거(evidence)와 함께 스트리밍되는 grounded 답변" width="820" />
</p>

<p align="center">
  <img src="docs/img/nexus-graph.png" alt="설계-관측 관계 그래프" width="405" />
  <img src="docs/img/nexus-diff.png" alt="설계-관측 Diff 대시보드" width="405" />
</p>

---

## What is Nexus?

Nexus는 조직 내부 지식(문서, 정책, 설정)과 운영 사실(OTel trace, metric)을 결합하여 **답변 근거 기반(grounded)으로 검색하고 추론하는 시스템**입니다.

AI Agent 가 CLI · MCP · A2A 로 질의하는 **context provider**로서, 추측이 아닌 실제 문서와 관측 데이터에 기반한 답변을 제공합니다.

```
"결제 서비스가 발행하는 토픽이 뭐야?"

→ 검색: Hybrid(BM25 형태소 + Vector 768d 또는 1024d, RRF) + Graph 2-hop context
→ 답변 근거: API_CONTRACT.md §5.2, 최근 OTel trace 47건
→ 답변: "payment-service는 payment.completed 토픽을 발행합니다. (confidence: 0.85)"
         + 출처 링크 + trace 포인터
```

### Why Nexus?

| 기존 RAG | Nexus |
|:--------:|:-----:|
| 문서만 검색 | 문서 + 실시간 trace 결합 |
| 추측 기반 답변 | 답변 근거(evidence) 필수 |
| 영어 최적화 | 한국어 형태소 분석 (mecab-ko) |
| Flat retrieval | Graph 관계 + Hybrid search |
| LLM이 판단 | System decides, LLM narrates |

---

## Architecture

```
                              ┌──────────────────────┐
                              │     Client / Agent   │
                              │ API, CLI, Web UI,   │
                              │ Slack Bot, MCP 2.0  │
                              └──────────┬───────────┘
                                         │
                              ┌──────────▼───────────┐
                              │    FastAPI (8000)     │
                              │  ┌────────────────┐   │
                              │  │ Hybrid Search  │   │
                              │  │ BM25+Vec+Graph │   │
                              │  └───┬────┬───┬───┘   │
                              │      │    │   │       │
                    ┌─────────┼──────┘    │   └──┐    │
                    │         │           │      │    │
              ┌─────▼─────┐   │   ┌───────▼──┐   │    │
              │ PostgreSQL │   │   │  Ollama  │   │    │
              │    16      │   │   │ nomic-   │   │    │
              │ ┌────────┐ │   │   │ embed    │   │    │
              │ │pgvector│ │   │   │ (768d)   │   │    │
              │ │tsvector│ │   │   │ (11434)  │   │    │
              │ │pg_trgm │ │   │   └──────────┘   │    │
              │ └────────┘ │   │                  │    │
              │  (5432)    │   │   ┌──────────────▼┐   │
              └────────────┘   │   │ OTel Collector│   │
                               │   │    (4318)     │   │
                ┌──────────┐   │   └──────┬────────┘   │
                │  Claude  │   │          │            │
                │ Sonnet   ◄───┘   ┌──────▼────────┐   │
                │  (LLM)   │       │ Grafana Tempo │   │
                └──────────┘       │  (3200)       │   │
                                   └───────────────┘   │
                                                       │
```

> 그림은 기본 세대만 그린다. 임베딩 세대는 둘이다 — `nomic-embed-text`(768d, Ollama, 기본) ·
> `KURE-v1`(1024d, `nexus-embed` 사이드카, `--profile embed`). 마지막 배포의 세대는 KURE-v1 이다
> (ADR-0009). LLM 백엔드는 `NEXUS_LLM_PROVIDER` 로 고른다 — `anthropic`(기본 모델
> `claude-sonnet-4-6`, `NEXUS_LLM_MODEL` 로 바꾼다) · `claude-code`(키리스 브리지, 소유자 신원만 —
> `providers/backend_choice.py`).

### Data Flow

```
┌─────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐     ┌───────────┐
│ Git Repo│────▶│ Classify │────▶│ Quarantine│────▶│  Chunk   │────▶│   Index   │
│  (*.md) │     │ + PII    │     │   Gate    │     │  (H1/H2) │     │BM25+Vec+G │
└─────────┘     └──────────┘     └───────────┘     └──────────┘     └───────────┘

┌──────────┐     ┌──────────┐     ┌───────────┐     ┌──────────────────┐
│OTel Trace│────▶│  Tempo   │────▶│ Aggregate │────▶│ CALLS_OBSERVED   │
│ (spans)  │     │ (store)  │     │ (5min win)│     │ + Evidence       │
└──────────┘     └──────────┘     └───────────┘     └──────────────────┘
```

---

## Key Features

### Hybrid Retrieval: BM25 + Vector (RRF Fusion) & Graph Context

BM25와 벡터 검색 경로를 병렬 실행하고 RRF(Reciprocal Rank Fusion, `k=60`)로 융합한 후, 융합 상위 결과에 대해 Entity 2-hop 지식 그래프 맥락을 독립적으로 결합합니다.

```python
# 1. BM25 경로: mecab-ko 형태소 분석을 통해 한국어 조사 및 어미를 정밀 분리
"서비스가" → ["서비스"]  # 조사 '가' 분리
"발행한다" → ["발행"]    # 어미 '한다' 분리

# 2. Vector 경로: nomic-embed-text (768d) 또는 KURE-v1 (1024d) 밀집 벡터 임베딩 (pgvector 연계)

# 3. RRF 융합: score = Σ 1/(k + rank + 1), k=60

# 4. Graph 맥락 확장: 융합 완료 후 엔티티 2-hop 인접 관계 엣지 추가 (랭킹 점수 비관여)
```

### Dual Knowledge Layer: Designed + Observed

```
┌─────────────────────────────────────────────────┐
│              Knowledge Graph                     │
│                                                  │
│  [payment-service] ──CALLS──▶ [order-service]   │  ← 설계 문서에서 추출
│         │                          │             │
│    PUBLISHES                  SUBSCRIBES         │
│         │                          │             │
│         ▼                          ▼             │
│  [payment.completed]    [order.created]          │
│                                                  │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│                                                  │
│  [payment-service] ═CALLS_OBSERVED═▶ [order-svc]│  ← OTel trace에서 관측
│         calls: 1,247                             │
│         error_rate: 2.3%                         │
│         p95: 142ms                               │
└─────────────────────────────────────────────────┘
```

### Design-Observation Diff

문서에만 있고 실제로 관측되지 않는 관계(Dead Doc), 관측되지만 문서화되지 않은 관계(Shadow Dependency)를 자동 탐지합니다.

| Diff Type | 의미 | 예시 |
|-----------|------|------|
| `doc_only` | 문서에는 있지만 관측 안 됨 | 사용 중단된 API |
| `observed_only` | 관측되지만 문서에 없음 | 미문서화 의존성 |
| `conflict` | 둘 다 있지만 불일치 | 프로토콜 변경 |

### Default-Deny Security

```
PII 감지 (주민번호, 카드번호, AWS Key, JWT)
    → 즉시 quarantine
    → 인덱싱 중단
    → 검색 결과에 절대 포함 금지

Classification: PUBLIC < INTERNAL < RESTRICTED
    → 모든 쿼리에 clearance 필터 적용
    → base_filter: tenant + classification + quarantine + status
```

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- (Optional) [Anthropic API Key](https://console.anthropic.com/) — LLM 답변 생성용

### 1. Clone & Configure

```bash
git clone https://github.com/khala-labs/khala.git
cd khala/nexus

cp .env.example .env
# .env에서 ANTHROPIC_API_KEY 설정 (LLM 답변 기능 사용 시 — 없어도 검색·답변 근거는 동작)
```

### 2. Start Everything

[Task](https://taskfile.dev)가 있으면 한 줄입니다:

```bash
task up
```

이 한 줄이 컨테이너를 띄우고(`--wait`로 health까지 대기), **DB 마이그레이션을 적용하고**,
임베딩 모델(`nomic-embed-text`)을 자동으로 받습니다. 최초 실행은 모델 다운로드로 몇 분 걸립니다.

Task가 없다면 그 세 가지를 직접:

```bash
docker compose up -d --wait                                  # 컨테이너 + 모델 자동 pull
docker compose exec -T nexus-app python -m scripts.migrate   # ← 빠뜨리면 소스 콘솔·문서 관리가 깨진다
```

> ⚠️ `docker compose up -d` **만** 하고 마이그레이션을 빠뜨리면, 검색·채팅은 되지만 소스
> 콘솔·문서 숨김/되돌리기·`supersede`가 `UndefinedTable`로 죽습니다. `task up`이나 위 두 줄을
> 함께 쓰세요.

뜨는 컨테이너:

| Container | Role | Port |
|-----------|------|------|
| nexus-db | PostgreSQL 16 + pgvector | 5432 |
| nexus-ollama | Embedding model | 11434 |
| nexus-app | FastAPI server | **8000** |

`docker-compose.yml` 의 서비스는 아홉이고, 나머지 여섯은 프로필로 옵트인한다:

| Container | Profile | Role |
|-----------|---------|------|
| nexus-embed | `embed` | KURE-v1(1024d) 임베딩 사이드카 |
| nexus-otel · nexus-tempo | `observability` | OTel 관측 파이프라인 (검색·채팅에 불필요) |
| nexus-grafana | `grafana` | trace 시각화 (tempo 를 함께 띄운다) |
| nexus-reingest | `reingest` | 주기 재적재 잡 |
| nexus-slack | `slack` | Slack Bot (Socket Mode) |

OTel 집계를 쓸 때만: `docker compose --profile observability up -d`.

### 3. Index Documents

리포에 함께 오는 설계 문서로 바로 시작해 볼 수 있습니다:

```bash
docker exec nexus-app nexus ingest ./docs
```

Notion 문서를 쓴다면 터미널 대신 웹 **소스** 탭에서 페이지 URL을 붙여넣으면 됩니다
(연결 상태·도달 여부까지 그 화면이 알려줍니다).

### 4. Search

브라우저에서 **`http://localhost:8000/`** 을 열고 질문하세요 — 답에는 답변 근거가 함께 붙습니다.

터미널이 편하면:

```bash
docker exec nexus-app nexus query "하이브리드 검색은 어떻게 결합하나"
```

---

## API Reference

요청·응답 규격의 정본은 [docs/API_CONTRACT.md](docs/API_CONTRACT.md) 와 코드(`nexus/api.py` ·
`nexus/documents/api.py` · `nexus/sources/api.py`)다. 아래는 주요 경로만 추린 것이다.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/search` | Hybrid search (BM25 + Vector + RRF) |
| `POST` | `/search/answer` | Search + LLM grounded answer |
| `POST` | `/search/answer/stream` | SSE 스트리밍 답변 (Web UI 채팅) |
| `POST` | `/search/explain` | 기대한 문서가 경로별로 몇 위였나 (패킷에 못 든 문서까지) |
| `POST` | `/ingest` | Index Markdown documents |
| `POST` | `/upload` | Upload & index a single file |
| `GET` | `/graph/{entity}` | Entity relationships (이름 또는 rid로 조회) |
| `GET` | `/entities/suggest` | 엔티티 자동완성 (pg_trgm) |
| `GET` | `/claims/value` · `/claims/grade-authority` | Archon — 코드 상수 값 · 등급 권한 |
| `POST` | `/feedback/offer` · `/feedback/vote` · `/feedback/reason` | 답변 피드백 (👍/👎 + 사유) |
| `GET` | `/documents` · `/documents/{rid}` | 인덱싱된 문서 목록 (페이지네이션) · 한 건 |
| `POST` | `/documents/{rid}/hide` · `/restore` · `/unsupersede` · `/supersede` | 문서 생명주기 |
| `GET`·`POST`·`DELETE` | `/sources/notion/...` | Notion root 관리 · 미리보기 · 동기화 (`roots` · `health` · `corpus` · `preview` · `sync`) |
| `GET` | `/diff` | Design vs. observation mismatch report |
| `POST` | `/otel/aggregate` | Trigger OTel trace aggregation |
| `GET` | `/visibility` | 이 principal 이 볼 수 있는 문서 수 (0건의 원인 가르기) |
| `GET` | `/auth/dev-token` | 로컬 dev 토큰 (`NEXUS_DEV_TOKEN` 이 없으면 `null`) |
| `GET` | `/status` | System health check |

### Example: Search with Graph

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "payment-service 의존성",
    "route": "hybrid_then_graph",
    "top_k": 5
  }'
```

### Example: Grounded Answer

```bash
curl -X POST http://localhost:8000/search/answer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "결제 서비스가 어떤 서비스를 호출하나요?",
    "clearance": "INTERNAL"
  }'
```

Response includes evidence snippets with source URIs and provenance.

---

## CLI Commands

컨테이너 안에서 돈다: `docker compose exec nexus-app nexus <command>`.

> **쓰는 명령은 반드시 그렇게 돌린다.** 임베딩 세대(모델·컬럼)는 env 로 오고 그 env 는 컨테이너
> 안에만 있다. 호스트 셸에서 그냥 `nexus ingest` 를 치면 `config.yaml` 기본값으로 해석돼
> **배포가 검색하지 않는 컬럼**에 적재된다 — 2026-08-10 에 실제로 그렇게 됐다
> (`SPEC-nexus-generation-of-record`). 컨테이너 없이 운영한다면 같은 변수를 export 한 셸에서
> 돌린다. 세대를 DB 에 명시적 선언(`nexus generation declare`)해 두면 어긋난 실행은 **거부**된다.

```bash
# ── 적재 ──
nexus ingest ./docs                         # 문서 인덱싱
nexus ingest ./docs --force                 # 전체 재인덱싱 (hash 무시)
nexus ingest-notion --roots "id1,id2"       # Notion 트리 적재 (NOTION_TOKEN 필요)
nexus ingest-notion --roots "..." --dry-run             # 계획만 — 적재도 재조정도 쓰지 않는다
nexus ingest-notion --roots "..." --reconcile --dry-run   # 위 + 삭제 반영 계획까지
nexus ingest-notion --roots "..." --reconcile             # soft_delete + revive 적용
# ↑ root 를 웹 소스 콘솔에 등록해 두었다면 CLI 대신 그 화면에서 동기화하는 편이 낫다.
#   미리보기 → 확인 → 적용 흐름이 붙어 있다.

# ── 소스 진단 ──
nexus sources health                        # 토큰이 유효한가, 등록된 root 에 닿는가 (문제 시 exit 1)

# ── 조회 ──
nexus query "검색어"                         # 검색 (+ --answer 로 LLM 답변)
nexus graph payment-service                 # 그래프 조회
nexus graph payment-service -h 2            # 2-hop 그래프
nexus diff                                  # 설계-관측 diff
nexus status                                # 시스템 상태
nexus entropy-signals                      # 공존 잔차 신호 — 테넌트별 5개
nexus entropy-signals --tenant default     # 라이브 코퍼스만 (전역은 평가 테넌트가 삼킨다)

# ── 도메인 값 (Archon) ──
nexus claim-seed claims.yaml                # 도메인 claim 적재 (소유자 판정 포함 — ruled_* 필드, migration 044)
nexus claim-value Basic                     # 개념의 현재 값을 코드에서 조회
nexus grade-authority                       # 등급 계층 권한 도출

# ── 운영 ──
nexus otel-aggregate                        # OTel trace 집계 (--profile observability 필요)
nexus auth gen-token                        # bearer 토큰 발급
nexus auth hash-token                       # 토큰 → sha256 (config.yaml auth.principals 용)

# ── 문서 생명주기 — 모든 파괴적 행위에는 역이 있다 ──
nexus doc hide <ref>                        # 검색에서 내린다. 지우지 않는다.
nexus doc restore <ref>                     # 되돌린다. Notion 동기화도 숨김 문서를 되살리지 않는다.
nexus supersede <old> --by <new>            # ⚠️ 파괴적: old 를 new 로 대체해 검색에서 배제
nexus unsupersede <ref> --reason "..."      # 그 역. 사유 필수. 체인은 역순으로만 풀린다.
```

`<ref>` 는 rid 든 경로든 받는다 (`README.md`, `doc_a1b2c3`). 숨김 문서도 경로로 부를 수 있다.

---

## Project Structure

파일 하나하나의 트리는 여기 두지 않는다 — 손으로 관리하던 트리는 실제 패키지보다 뒤처졌다(없는
`models/document.py` 를 가리키고, 패키지 열 개를 빠뜨렸다). 어디를 **반드시 거쳐야 하는지**는
[CLAUDE.md 의 이음매 지도](./CLAUDE.md#프로젝트-구조--이음매-지도)가 정본이고, 파일 목록은 `ls` 로 본다.
아래는 패키지 단위 지도다(2026-11-14 기준).

```
nexus/
├── nexus/
│   ├── api.py · cli.py      # FastAPI 앱 · Typer CLI (`nexus ...`)
│   ├── ingest/              # 수집 → PII 검사 → 분류 → 청킹. 모든 적재 경로는 pipeline.py(run_ingest)로 모인다
│   ├── index/               # BM25(mecab-ko) · 임베딩 · 벡터 컬럼 · 그래프 추출 · 앵커
│   ├── search/              # hybrid.py(BM25+Vector RRF) · answer_pipeline.py(답변 표면 공용 앞단) · reconcile.py(근거 묶음)
│   ├── llm/                 # 답변 생성 · 인용/숫자 검증 · prompt_version · 실패 사유
│   ├── providers/           # EmbeddingService · LLMService · 답변 백엔드 선택
│   ├── repositories/        # GraphRepository
│   ├── models/              # CRM 모델 (resource · chunk · claim)
│   ├── auth/                # bearer 토큰 → (tenant, clearance) · Cloudflare Access JWT
│   ├── claims/              # Archon — 코드 상수 값 · 소유자 판정
│   ├── documents/ · sources/  # 문서 생명주기 API · Notion 소스 콘솔 API
│   ├── feedback/ · health/  # 답변 피드백 · 배포 건강 신호
│   ├── otel/                # Tempo → CALLS_OBSERVED · 설계-관측 diff
│   ├── a2a/                 # A2A 서버 (플래그로 켠다)
│   ├── mcp/                 # MCP 서버 (도구 18개, mcp 2.x `MCPServer`)
│   ├── slack/               # Slack Bot (Socket Mode)
│   ├── tools/               # 개발용 도구 (키리스 LLM 브리지)
│   └── web/                 # Web UI (Vanilla JS, 빌드 불필요)
│
├── tests/                   # 시험 함수 약 3,000개 (2026-11-14 `git grep` 으로 2,994)
├── docs/                    # 설계 문서 · 가이드 · 사전 등록 기록 (docs/README.md)
├── migrations/              # SQL 마이그레이션 (001~052)
├── config.yaml              # Classification, PII, search params
├── entities.example.yaml    # Entity gazetteer 예시 (읽히지 않음 — 쓰려면 entities.yaml 로 복사)
├── init.sql                 # 기본 스키마 (이후 변경은 migrations/)
├── docker-compose.yml       # 서비스 9개 (기본 3개 + 프로필 6개, 위 Quick Start 표)
├── docker-compose.test.yml  # 통합 테스트용 (포트 충돌 방지)
└── Dockerfile               # Python 3.11 + mecab-ko
```

---

## Design Principles

### 1. Grounded Answers Only

모든 답변에는 source chunk 또는 trace 포인터가 답변 근거로 첨부됩니다. 추측은 제공하지 않습니다.

### 2. System Decides, LLM Narrates

접근 통제, 분류, 검색 경로 판정은 모두 **deterministic 코드**가 수행합니다. LLM은 검색된 evidence를 바탕으로 요약/설명만 담당합니다.

### 3. Nexus is an Index, Not Storage

원본 문서는 Git에, 원본 trace는 Tempo에 있습니다. Nexus DB에는 파생 데이터(chunks, embeddings, graph edges)만 저장됩니다.

### 4. Evidence-Driven Edges

근거(evidence) 없이는 어떤 관계(edge)도 생성되지 않습니다. 모든 edge는 반드시 source chunk 또는 trace query ref에 연결됩니다.

### 5. 2.0-Ready Abstractions

MVP 단계부터 교체 가능한 추상화를 적용하여, 2.0 전환 시 재설계를 방지합니다:

| Abstraction | Purpose |
|-------------|---------|
| `GraphRepository` Protocol | Neo4j 전환 대비 |
| `EmbeddingService` wrapper | 임베딩 모델 교체 대비 |
| `LLMService` wrapper | Multi-LLM 대비 |
| `get_search_text()` | Contextual Enrichment 대비 |
| `canonicalize_entity_name()` | 추출기 교체 시 rid 안정성 |

---

## Testing

```bash
# 전체 테스트 (시험 함수 약 3,000개 — DB 가 필요한 것은 NEXUS_TEST_DB_URL 이 있을 때만 돈다)
docker exec nexus-app pytest tests/ -v

# 카테고리별
docker exec nexus-app pytest tests/test_bm25_korean.py -v   # 한국어 BM25
docker exec nexus-app pytest tests/test_quarantine.py -v    # PII/보안
docker exec nexus-app pytest tests/test_hybrid.py -v        # 검색
docker exec nexus-app pytest tests/test_graph.py -v         # 그래프
docker exec nexus-app pytest tests/test_otel.py -v          # OTel
docker exec nexus-app pytest tests/test_api.py -v           # API 모델
docker exec nexus-app pytest tests/test_streaming.py -v     # SSE 스트리밍
docker exec nexus-app pytest tests/test_slack.py -v         # Slack Bot
docker exec nexus-app pytest tests/test_mcp.py -v           # MCP Server

# 통합 테스트 (실제 DB 필요)
docker compose -f docker-compose.test.yml up -d
NEXUS_TEST_DB_URL=postgresql://nexus:nexus@localhost:5433/nexus_test \
  pytest tests/test_e2e.py -v
docker compose -f docker-compose.test.yml down
```

---

## Configuration

`config.yaml`에서 주요 파라미터를 조정할 수 있습니다:

```yaml
# 한국어 청킹 파라미터
chunking:
  korean_tokens: 1100
  english_tokens: 700
  overlap_ratio: 0.15

# 검색 튜닝
search:
  bm25_top_k: 20
  vector_top_k: 20
  rrf_k: 60          # RRF fusion 파라미터

# PII 탐지 패턴 추가
pii_patterns:
  korean_ssn: '\b[0-9]{6}-[1-4][0-9]{6}\b'
  aws_key: 'AKIA[0-9A-Z]{16}'
```

Entity gazetteer 는 `entities.yaml` 에 둡니다. **리포에는 예시(`entities.example.yaml`)만 있고, 그 파일은
읽히지 않습니다.** 쓰려면 예시를 `entities.yaml` 로 복사해 배포의 엔티티로 바꾸세요(그 파일은 `.gitignore`
에 있습니다). `entities.yaml` 이 없으면 엔티티 검출 · 기동 시 등록 · 적재 시 관계 추출이 모두 꺼지고, 기동
로그에 `gazetteer_absent` 가 한 번 찍힙니다.

⚠ 검출은 이름과 별칭을 대소문자 무시 **부분 문자열**로 찾습니다. 짧은 영어 별칭(`order` 같은)은 다른 낱말
속에서도 걸립니다 — 예시 목록이 모든 테넌트에 쓰이던 때 로봇 사례 질의 32건이 전부 `order-service` 로
잡혔습니다(2026-10-01).

```yaml
entities:
  - name: payment-service
    type: Service
    aliases: ["결제 서비스", "결제서비스", "payment"]
  - name: payment.completed
    type: Topic
    aliases: ["결제 완료 이벤트", "payment completed event"]
```

---

## Web UI

`http://localhost:8000/` 접속 시 Web UI를 사용할 수 있습니다. 빌드 불필요 — FastAPI에서 직접 서빙합니다.

| 뷰 | 기능 |
|----|------|
| 채팅 | SSE 스트리밍 답변 + Evidence 패널 + 인라인 그래프 |
| 그래프 | vis-network 엔티티 관계 시각화 (노드 클릭 확장) |
| 문서 | 페이지네이션 문서 브라우저 |
| Diff | 설계-관측 불일치 대시보드 |
| 업로드 | 드래그앤드롭 Markdown 업로드 |

자세한 연동 규격: [docs/UI_INTEGRATION.md](docs/UI_INTEGRATION.md)

---

## Slack Bot

`@khala` 멘션이나 DM 으로 질의하면 grounded 답변을 Slack 메시지로 돌려준다. 진입점은
`nexus-slack`(`[project.scripts]`)이고 compose 의 `nexus-slack` 서비스(`--profile slack`)로 띄운다.
API 호출에는 `NEXUS_SLACK_TOKEN` bearer 를 붙인다 — 테넌트·clearance 는 그 principal 이 정한다.

설정 가이드: [docs/SLACK_BOT.md](docs/SLACK_BOT.md)

---

## MCP Server

AI Agent(Claude, Cursor 등)가 MCP 프로토콜로 Nexus에 질의할 수 있습니다.

```bash
pip install -e '.[mcp]'
python -m nexus.mcp                    # stdio (로컬)
python -m nexus.mcp --transport http   # streamable-http (원격)
```

도구 18개(2026-11-14, `nexus/mcp/server.py`): 검색·답변(`nexus_search` · `nexus_answer` ·
`nexus_graph` · `nexus_suggest` · `nexus_diff` · `nexus_status`), Archon(`archon_claim_value` ·
`archon_grade_authority`), 문서 생명주기(`nexus_documents_search` · `nexus_document_hide` ·
`nexus_document_restore` · `nexus_supersede` · `nexus_unsupersede`), Notion 소스(`nexus_sources_list` ·
`nexus_sources_add` · `nexus_sources_health` · `nexus_sources_sync` · `nexus_sync_status`).

⚠️ 런타임 이미지(`Dockerfile`)는 `mcp` 엑스트라를 설치하지 않는다 — 컨테이너 안에서는 `python -m nexus.mcp`
가 돌지 않는다. 지금 에이전트가 쓰는 문은 CLI 다(루트 `CLAUDE.md`).

⚠️ Nexus 기본 auth 모드가 `enforced` 라 `NEXUS_MCP_TOKEN` 없이는 모든 툴이 401 이다 ([docs/MCP_SERVER.md](./docs/MCP_SERVER.md) §6).

설정 및 사용법: [docs/MCP_SERVER.md](docs/MCP_SERVER.md)

---

## Roadmap

방향(RAG·LLMOps 실험과 다음 실험 순서)은 [ROADMAP.md](./ROADMAP.md) 가 정본이다. 2026-06 의 페이즈
계획(팀 맞춤형 → 검색 지능화 → 거버넌스)은 그 부록에 항목별 상태와 함께 있다 — 인증은 JWT 가 아니라
불투명 bearer 토큰으로 이미 출하됐다.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Language | Python 3.11+ | ML/NLP ecosystem |
| API | FastAPI | Async-first, OpenAPI |
| CLI | Typer | Developer productivity |
| Database | PostgreSQL 16 | pgvector + BM25 + Graph 통합 |
| Korean NLP | mecab-ko + mecab-ko-dic | 조사/어미 정확 분리 |
| Embedding | nomic-embed-text (Ollama) · KURE-v1 (sidecar) | 768d 기본 · 1024d 한국어 (ADR-0009), local |
| LLM | Claude Sonnet (Anthropic) · 키리스 브리지(dev) | Grounded answer generation. `NEXUS_LLM_PROVIDER` 로 고른다 |
| Tracing | OTel Collector + Tempo | Trace 수집 + 쿼리 |
| Container | Docker Compose | One-command infra |

---

## Environment Variables

전체 목록과 설명의 정본은 [`.env.example`](./.env.example) 이다. 자주 쓰는 것만:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://nexus:nexus@localhost:5432/nexus` | PostgreSQL 연결 |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API |
| `ANTHROPIC_API_KEY` | — | Claude API key (`anthropic` 백엔드) |
| `NEXUS_LLM_PROVIDER` | `anthropic` | 답변 백엔드 — `anthropic` · `claude-code`(키리스 브리지, owner principal 만) |
| `NEXUS_DEV_LLM_PROVIDER` | — | `local-dev` principal 하나만의 백엔드 (개발 상자는 `claude-code`) |
| `NEXUS_LLM_MODEL` | `claude-sonnet-4-6` | `anthropic` 백엔드의 모델 id |
| `NEXUS_EMBEDDING_MODEL` · `_COLUMN` · `_BACKEND` | config.yaml 값 | 임베딩 세대 (함께 움직인다) |
| `TEMPO_URL` | `http://localhost:3200` | Grafana Tempo |
| `OTEL_COLLECTOR_URL` | `http://localhost:4318` | OTel Collector |
| `DEFAULT_TENANT` | `default` | 기본 테넌트 |
| `SLACK_BOT_TOKEN` | — | Slack Bot OAuth Token (Slack Bot용) |
| `SLACK_APP_TOKEN` | — | Slack App-Level Token (Socket Mode) |
| `NEXUS_API_URL` | `http://localhost:8000` | Slack Bot → Nexus API 주소 |
| `NEXUS_SLACK_TOKEN` | — | Slack Bot 의 Nexus bearer (읽기 전용 principal) |

---

## License

MIT

---

<p align="center">
  <sub>Built with Claude Code</sub>
</p>
