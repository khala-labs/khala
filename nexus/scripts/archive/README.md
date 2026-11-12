# `nexus/scripts/archive/`

이 디렉터리는 작업이 끝난 일회성 스크립트를 보관한다. 2026-11-13에 적용된 규칙에 따라, 기록이나 문서가 이동된 경로를 가리키지 않도록 저장소의 추적 파일(기록, 문서, 테스트, `Taskfile`, `CI`, 다른 스크립트)에서 참조하지 않는 스크립트만 이곳으로 이동한다.

| 스크립트 | 무엇이었나 | 끝난 이유 |
| --- | --- | --- |
| `backfill_doc_titles.py` | 2026-06-30에 추가되었으며, 제목이 파일명으로 대체된 문서의 첫 표제에서 사람이 읽을 수 있는 제목을 복원한 일회성 백필이다. | 수집 단계(`ingest/title.derive_title`)에서 이제 제목을 직접 도출한다. |
| `tokenizer_protected_probe.py` | 토크나이저에서 말뭉치 자체 용어를 보호하면 순위가 상승하는지 측정한 작업이며, 규칙은 `nexus/tests/eval/tokenizer-protected-terms/README.md`에 있다. | 2026-08-26에 기각되었다. |
| `tokenizer_surface_probe.py` | 표면형도 함께 색인하면 분절된 고유명사를 복원하는지 측정한 작업이며, 규칙은 `nexus/tests/eval/tokenizer-surface/README.md`에 있다. | 2026-08-26에 기각되었다. |

스크립트는 `docker exec nexus-app python -m scripts.archive.<name>` 명령으로 실행하며 각 스크립트의 자체 독스트링에 세부 옵션이 있다.
