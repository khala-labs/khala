"""답변을 내는 API 표면은 **전부** 같은 검색 앞부분을 지나는가 — 그리고 그 안에서 `packet_for_answer` 를.

⛔ **왜 생겼나 (외부 평가 F2, 2026-09-02).** `reconcile.py` 의 `packet_for_answer` docstring 이
이렇게 적어 두었다 — *"답변용 근거 패킷은 이 함수 하나로만 만든다. 답변 경로가 셋이다 …
각자 `assemble_packet` 을 부르면 보강을 한 곳에만 붙이는 배선이 가능해지고 **그 조합은 검사가
초록인 채로 프로덕션에서 조용히 틀린다**."* `/search/answer/stream` 이 `assemble_packet` 을 직접
불렀고, 그래서 정정 확인 패스·페어 확장·코드 값이 웹 채팅이 타는 그 경로에서만 빠졌다.

**2026-11-13 부터 모양이 바뀌었다** (SPEC-nexus-shared-answer-pipeline). 네 API 표면이 검색
앞부분을 각자 복사해 갖고 있었고 사본이 갈렸다. 이제 앞부분은 `search/answer_pipeline.py` 의
`retrieve_for_answer` 하나이고, 패킷은 그 안의 **한 호출**에서 만든다. 그래서 이 검사는 세 가지를
본다:

1. 모든 API 표면(과 `POST /search`)이 `retrieve_for_answer` 를 부른다.
2. 어느 API 표면도 `hybrid_search` · `packet_for_answer` 를 **직접 부르지 않는다** — 부르면 사본이다.
3. `retrieve_for_answer` 안에서 패킷 호출은 **정확히 한 곳**이고, 그 한 곳을 지우면 이 검사가 붉어진다.

⚠ `packet_for_answer` 는 의존성으로 **주입된다** — 두 테스트 파일이 `nexus.api` 에서 그것을 바꿔
끼우기 때문이다. 그래서 이음매는 타입이 아니라 **한 호출 자리 + 이 검사**가 지킨다. 넷째 검사가
A2A·CLI 가 진짜 `reconcile.packet_for_answer` 를 묶는지 본다.

⚠ **이 검사는 "호출이 존재하는가" 까지만 본다.** 그 호출이 실제로 돌아 보강이 붙는지는
`test_read_scope_reaches_every_enrichment.py` 가 진짜 DB 로 확인한다. 둘이 짝이다.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

import pytest

PIPELINE = Path(__file__).resolve().parents[1] / "nexus" / "search" / "answer_pipeline.py"


def _names(func) -> set[str]:
    """이 함수와 **그 안에 중첩된 함수들**이 부르는 이름 전부.

    ⛔ 중첩까지 걸어야 한다. 스트리밍 핸들러의 본체는 `event_stream()` 안에 있어서,
    바깥 함수의 `co_names` 만 보면 **결함이 있는 판에서도 초록**이다.
    """
    seen, out = set(), set()

    def walk(code) -> None:
        if id(code) in seen:
            return
        seen.add(id(code))
        out.update(code.co_names)
        for const in code.co_consts:
            if hasattr(const, "co_names"):
                walk(const)

    walk(func.__code__)
    return out


def _tree(func) -> ast.AST:
    return ast.parse(textwrap.dedent(inspect.getsource(func)))


def _called(tree: ast.AST) -> set[str]:
    """이 소스가 **호출하는** 이름(`f(...)` · `x.f(...)`) — 키워드 인자로 넘기기만 한 것은 빼고."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            out.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    return out


def _surfaces():
    from nexus import api, cli
    from nexus.a2a import server

    return {
        "HTTP /search/answer": api.search_answer,
        "HTTP /search/answer/stream": api.search_answer_stream,
        "A2A": server._default_answer_fn,
        "CLI": cli.query,
    }


def _callers():
    from nexus import api

    return {**_surfaces(), "HTTP /search": api.search}


@pytest.mark.parametrize("label", list(_callers()))
def test_every_caller_goes_through_the_shared_retrieval(label):
    """⛔ API 표면 하나가 빠지면 그 API 표면의 사용자만 다른 검색을 받는다 — 화면에 안 보인다."""
    assert "retrieve_for_answer" in _names(_callers()[label]), (
        f"{label} 이 `retrieve_for_answer` 를 안 지난다 — 검색 앞부분의 사본이 돌아왔다")


@pytest.mark.parametrize("label", list(_callers()))
def test_no_caller_searches_or_builds_the_packet_itself(label):
    """대조군 — 직접 부르면 그것이 사본이다. 의존성으로 **넘기는** 것(`hybrid_search=hybrid_search`)은 괜찮다."""
    called = _called(_tree(_callers()[label]))
    assert not called & {"hybrid_search", "packet_for_answer"}, (
        f"{label} 이 {sorted(called & {'hybrid_search', 'packet_for_answer'})} 를 직접 부른다")


@pytest.mark.parametrize("label", list(_surfaces()))
def test_no_answer_surface_assembles_the_packet_itself(label):
    """지나가면서 **직접 조립도** 하면 두 패킷이 생기고 어느 쪽이 답에 갔는지 모른다."""
    assert "assemble_packet" not in _names(_surfaces()[label]), (
        f"{label} 이 `assemble_packet` 을 직접 부른다 — 이음매를 지나는 의미가 없어진다")


def _packet_sites(tree: ast.AST) -> int:
    """`retrieve_for_answer` 안의 `deps.packet_for_answer(...)` 호출 수."""
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.AsyncFunctionDef) and n.name == "retrieve_for_answer")
    return sum(1 for n in ast.walk(fn)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "packet_for_answer"
               and isinstance(n.func.value, ast.Name) and n.func.value.id == "deps")


def test_the_pipeline_builds_the_packet_at_exactly_one_site():
    assert _packet_sites(ast.parse(PIPELINE.read_text(encoding="utf-8"))) == 1


def test_the_check_goes_red_when_the_packet_call_is_removed():
    """⛔ **일부러 깨뜨려 본다.** 이 리포는 '찾아내고 종료코드 0' 인 검사기를 만든 적이 있다.

    파이프라인 소스를 파싱해 패킷 호출 노드를 `None` 으로 바꾸고, 같은 셈을 다시 한다.
    """
    class _DropPacketCall(ast.NodeTransformer):
        def visit_Await(self, node):
            call = node.value
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "packet_for_answer"):
                return ast.copy_location(ast.Constant(value=None), node)
            return self.generic_visit(node)

    tree = ast.parse(PIPELINE.read_text(encoding="utf-8"))
    mutated = ast.fix_missing_locations(_DropPacketCall().visit(tree))
    assert _packet_sites(mutated) == 0, "패킷 호출을 지웠는데도 셈이 그대로다 — 검사에 이빨이 없다"


@pytest.mark.parametrize("label", ["A2A", "CLI"])
def test_a2a_and_the_cli_bind_the_real_packet_function(label):
    """주입되는 자리다 — A2A·CLI 는 언제나 `reconcile.packet_for_answer` 를 묶는다."""
    tree = _tree(_surfaces()[label])
    deps = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and getattr(n.func, "id", None) == "RetrievalDeps"]
    assert len(deps) == 1, f"{label} 이 의존성을 한 번 만들지 않는다"
    bound = {k.arg: ast.unparse(k.value) for k in deps[0].keywords}
    assert bound["packet_for_answer"] == "reconcile.packet_for_answer"


def test_the_http_deps_bind_the_real_packet_function_when_nothing_is_patched():
    from nexus import api
    from nexus.search import reconcile

    deps = api._retrieval_deps({}, None, None)
    assert deps.packet_for_answer is reconcile.packet_for_answer


def test_it_sees_calls_made_inside_a_nested_function():
    """중첩을 안 걸으면 스트리밍 핸들러가 결함이 있는 판에서도 통과한다."""
    def outer():
        async def inner():
            return retrieve_for_answer  # noqa: F821 — 이름 존재만 본다
        return inner

    assert "retrieve_for_answer" in _names(outer)
