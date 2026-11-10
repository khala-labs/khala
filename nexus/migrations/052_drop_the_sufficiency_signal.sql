-- 052: 충분성 신호의 네 칸을 내린다 — 마이그레이션 012 의 되돌림 (SPEC-nexus-sufficiency-signal §2.2h).
--
-- 왜 (2026-11-10, 소유자 결정). 그 SPEC 은 검토일 2026-11-10 까지 소비자 게이트를 선언하지
-- 못하면 012 를 되돌린다고 적어 뒀다. 그날까지 라이브에서 판정값(sufficient · insufficient)이
-- 적힌 행은 0 이었다 — 판정자는 한 번도 켜지지 않았고(모든 행이 disabled · not_applicable · NULL),
-- 이 칸을 읽는 코드도 없었다. 아무도 소비하지 않는 관찰은 ADR-0002 의 "taste = subtraction" 이
-- 막으려는 유지보수 면적이다.
--
-- 되돌리는 것은 칸과 제약뿐이다. 012 파일은 적용 이력(schema_migrations)의 일부라 그대로 두고,
-- 이 파일이 그 뒤에 와서 지운다. 사전에 의존 뷰가 없음을 라이브에서 확인했다(pg_depend 0건).
--
-- 멱등.

ALTER TABLE search_log DROP CONSTRAINT IF EXISTS search_log_sufficiency_check;
ALTER TABLE search_log DROP COLUMN IF EXISTS sufficiency;
ALTER TABLE search_log DROP COLUMN IF EXISTS sufficiency_at;
ALTER TABLE search_log DROP COLUMN IF EXISTS sufficiency_judge;
ALTER TABLE search_log DROP COLUMN IF EXISTS evidence_fingerprint;
