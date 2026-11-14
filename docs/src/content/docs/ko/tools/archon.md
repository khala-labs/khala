---
title: Archon
description: 도메인 불변식 및 비즈니스 상수에 대한 권위 창(Authority Window) 인터페이스.
---

:::note[아키텍처 구성]
Archon은 독립 실행형 서비스가 아니며, Nexus 코어 저장소 내 `nexus/claims/` 패키지로 탑재되어 있습니다. Nexus CLI(`nexus claim-seed`, `nexus claim-value`, `nexus grade-authority`), HTTP REST API(`GET /claims/value`, `GET /claims/grade-authority`), 그리고 2개의 MCP 도구 인터페이스를 통해 접근할 수 있습니다.
:::

Archon은 Domain Truth에 대한 **단일 권위 창(Authority Window)** 인터페이스를 제공합니다. 소프트웨어 엔지니어 및 자율 에이전트가 시스템의 핵심 제약 조건, 한도, 비즈니스 불변식을 질의할 때, 정적 코드베이스 상수를 런타임에 직접 역참조하여 검증된 정본 값을 산출합니다.

문서화된 사양과 실제 소스코드 간의 괴리를 방지하기 위해, Archon은 사전에 정의된 도메인 클레임(Claim)을 소스코드 심볼에 바인딩하고, 질의 시점에 소스 파일의 AST/상수 값을 실시간 평가합니다. 근거가 부재하거나 정합성이 검증되지 않은 항목에 대해서는 응답을 기각함으로써 환각 생성을 억제합니다.

<svg class="kh-fig" viewBox="0 0 560 210" role="img" aria-label="Archon 상수 조회 및 검증 다이어그램: 질의 시점에 소스코드 상수 config/limits.py:12 (MAX_RETRIES = 5)를 읽고, content_hash가 사전 승인 해시와 일치함을 검증한 후 보정된 인용 답변(MAX_RETRIES = 5)을 반환함.">
<defs><marker id="ar-a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path class="kh-fig-ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
<text class="kh-fig-q" x="24" y="22">› max retry limit?</text>
<rect class="kh-fig-panel" x="24" y="36" width="250" height="150" rx="8"/>
<text class="kh-fig-h" x="42" y="60">READ CONSTANT</text>
<line class="kh-fig-rule" x1="42" y1="72" x2="256" y2="72"/>
<text class="kh-fig-d" x="42" y="94">config/limits.py:12</text>
<text class="kh-fig-ans" x="42" y="120">MAX_RETRIES = 5</text>
<text class="kh-fig-s" x="42" y="146">content-hash 3f9a2c</text>
<text class="kh-fig-verified" x="42" y="168">✓ matches approved</text>
<path class="kh-fig-line-acc" d="M274 111 L300 111" marker-end="url(#ar-a)"/>
<rect class="kh-fig-panel" x="300" y="36" width="236" height="150" rx="8"/>
<text class="kh-fig-h" x="318" y="60">GROUNDED ANSWER</text>
<line class="kh-fig-rule" x1="318" y1="72" x2="518" y2="72"/>
<text class="kh-fig-ans" x="318" y="98">MAX_RETRIES = 5</text>
<text class="kh-fig-d" x="318" y="124">→ config/limits.py:12</text>
<text class="kh-fig-s" x="318" y="148">read at query time · calibrated</text>
<text class="kh-fig-verified" x="318" y="170">✓ VERIFIED · no drift</text>
</svg>

## 핵심 개념

- **엔티티 레지스트리 기반 클레임 모델** — 용어, 액터, 시스템 불변식을 표준 도메인 엔티티로 등록하고, 세부 수치와 제약 조건을 해당 엔티티를 참조하는 클레임(Claim) 객체로 구조화합니다.
- **포인터 기반 실시간 평가 (Dynamic Dereferencing)** — 수치 데이터를 정적 데이터베이스에 단순 복제하지 않고 소스코드 심볼 경로를 참조(포인터)로 유지하여, 질의 시점의 최신 코드 값을 동적으로 평가합니다.
- **코드 드리프트 감지 (Claim-to-Code Drift)** — 대상 코드 심볼의 파일 경로 및 구문 해시가 마지막 검증 커밋 대비 변경된 경우 해당 클레임에 드리프트 상태를 마킹합니다.
- **결정론적 판정 및 LLM 생성 분리 (System Decides, LLM Narrates)** — 분류, 불변식 판정, 권한 검증은 결정론적 코드로 강제하며, 언어 모델은 검증 완료된 결과에 대한 요약 및 표현만을 담당합니다.

## 빠른 시작

Archon은 Nexus 저장소 내부 `master` 브랜치에 있는 `nexus/claims/` 패키지입니다. Nexus 스택(PostgreSQL)을 재사용합니다. 코드 값 리졸버는 `config.yaml` → `code_source.repo_path`를 통해 설정된 대상 저장소에서 상수를 읽습니다.

### 1. Nexus 실행

```bash
git clone https://github.com/khala-labs/khala.git
cd khala
task up          # starts containers, runs DB migrations, pulls the model (see the Nexus quickstart for the no-Task path)
```

그런 다음 `nexus/config.yaml`의 `code_source.repo_path`를 Archon이 상수를 읽어올 코드베이스로 설정합니다. 비워 두면 값 조회가 비활성화된 상태로 유지됩니다.

### 2. 도메인 클레임 시딩

`claims.yaml`은 각각 `value_source`(코드 상수)를 가리키는 불변 조건/값을 정의합니다. 시딩은 각 소스의 현재 코드 해시를 스냅샷으로 생성합니다.

```bash
nexus claim-seed claims.yaml
```

(참고: 저장소에 포함된 `nexus/claims.yaml`은 시드 예시이며, 패키지 자체가 아닙니다.)

### 3. 현재 값 질의

```bash
nexus claim-value Basic
```

Archon은 질의 시점에 코드 상수에서 값을 읽어와 신뢰도 및 최신성과 함께 답변합니다. 확실한 것은 단언하고 알 수 없는 것은 답변을 거부합니다.

## 사용 방법

### 도메인 값 조회

```bash
nexus claim-value Basic        # e.g. "basic tier max projects?"
nexus claim-value Task         # task limit, etc.
```

보정된 레이블과 함께 현재 값을 반환합니다. 코드 상수에서 명확하게 읽어온 경우 높은 신뢰도(high-confidence), 그렇지 않은 경우 솔직한 "couldn't verify", 마지막 검증 이후 소스가 변경된 경우 드리프트 경고가 표시됩니다.

### 등급 / 역할 권한 도출 (emergent 질문)

```bash
nexus grade-authority --enum GradeType
nexus grade-authority --enum GradeType --subpath some/scope
```

코드에서 권한 게이트를 추출하고(CodeQL 없이 무료 tree-sitter AST 사용), 여집합을 통해 각 등급이 어떤 작업에서 차단되는지 도출합니다. 고정 게이트 여집합은 확실(high)로 보고되며, "action-guard vs filter" 시맨틱은 확인 필요(medium)로 플래그가 지정되어 정직하게 구분됩니다.

### AI 에이전트에서 질의 (MCP)

Archon은 에이전트가 추측하는 대신 거버넌스 소스로부터 도메인 질문에 답변할 수 있도록 MCP 도구를 노출합니다:

- `archon_claim_value(concept, tenant, classification_max)` — 개념의 불변 조건/값의 현재 값입니다.
- `archon_grade_authority(grade, enum_name, subpath)` — emergent/여집합 권한 질문("what can MEMBER do?")입니다.

## 참조

- 저장소: [github.com/khala-labs/khala](https://github.com/khala-labs/khala), `master` 브랜치.
- 패키지: `nexus/claims/` (`seed.py`, `value_query.py`, `grade_authority.py`, `answer.py`, `matching.py`, `repository.py`). CLI는 `nexus/cli.py`, HTTP는 `nexus/api.py`, MCP 도구는 `nexus/mcp/server.py`에 있습니다.

:::note[마지막 검증]
2026-11-14 — 명령어, HTTP 라우트 및 MCP 도구 시그니처를 `master` 브랜치의 `nexus/cli.py`, `nexus/api.py`, `nexus/mcp/server.py`와 대조하여 확인했습니다.
:::
