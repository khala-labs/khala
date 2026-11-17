# DB 마이그레이션 (경량 순차)

`init.sql` 은 **빈 DB 최초 1회** 베이스라인(`/docker-entrypoint-initdb.d`)이다. 이후
스키마 변경(델타)은 이 디렉터리에 순서 있는 `.sql` 파일로 누적한다.

## 규칙

확인 2026-11-17 — `nexus/migrations.py` · `scripts/migrate.py` 에 대 봤다.

- 파일명 = 버전 키, **정렬 순서로 적용**: `001_<설명>.sql`, `002_<설명>.sql`, …
- 적용된 버전은 `schema_migrations` 테이블에 기록되고 재실행 시 건너뛴다(**멱등**).
- 각 파일은 자체 트랜잭션으로 적용된다.
- 버전 키는 **파일명 전체**다(`migration_version`). 러너는 `schema_migrations` 에 없는 파일을 이름
  정렬 순으로 적용한다.
- ⚠ 그래서 번호를 끼워 넣거나 같은 번호를 다시 써도 거절되지 않는다. 대신 이미 적용된 DB 에서는
  그 파일이 **맨 뒤에** 돌고, 빈 DB 에서는 번호 자리에서 돈다 — 두 DB 의 적용 순서가 달라진다.
  **권장**: 새 파일은 가장 큰 번호 다음을 쓴다.
- **멱등 DDL 권장**: `ADD COLUMN IF NOT EXISTS`, `CREATE TABLE/INDEX IF NOT EXISTS` —
  빈 DB(init.sql 직후)와 기존 DB 양쪽에서 안전하도록. 권장이고, 검사하는 곳은 없다.

## 적용

```bash
# 업데이트 한 줄 (이미지 재빌드·재기동 + 마이그레이션):
task update

# 마이그레이션만:
docker compose exec -T nexus-app python -m scripts.migrate
docker compose exec -T nexus-app python -m scripts.migrate --status   # 현황만
```
