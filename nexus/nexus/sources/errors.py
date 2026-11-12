"""소스 콘솔의 도메인 예외 — API 계층이 HTTP 코드로 옮긴다."""

from __future__ import annotations


class SourceError(Exception):
    """모든 소스 콘솔 오류의 뿌리."""


class DuplicateRoot(SourceError):
    """이미 등록된 root (409)."""


class SyncInProgress(SourceError):
    """같은 tenant 에서 이미 동기화가 돌고 있다 (409). run_id 를 들고 있다."""

    def __init__(self, run_id: str):
        super().__init__(f"sync already running: {run_id}")
        self.run_id = run_id
