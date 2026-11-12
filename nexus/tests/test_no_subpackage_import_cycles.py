"""하위 패키지(`nexus.llm`, `nexus.search`, …) 사이에 모듈 최상위 import 순환이 없다.

⛔ **왜 (2026-11-12 구조 점검).** `llm` 과 `search` 가 서로를 import 했다: `llm/answer.py` 가 `search`
의 다섯 모듈을 가져오고, `search/evidence_packet.py` 가 `llm/citations.py` 의 인용 문법 벗기기를
가져갔다. 순환은 지금 당장 터지지 않아도 import 순서 하나에 깨지는 구조다. 그 함수는
`search/citation_syntax.py` 로 옮겼고, 이 검사가 하위 패키지 수준의 순환을 다시 막는다.

**모듈 최상위 import 만 센다.** 함수 안의 지연 import 는 순환을 피하려고 일부러 쓰는 자리이고,
import 시점에 돌지 않는다.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "nexus"


def _subpackage(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) >= 2 and (PACKAGE / parts[1]).is_dir():
        return parts[1]
    return None


def _edges(files: dict[str, str]) -> dict[str, set[tuple[str, str]]]:
    """{하위 패키지: {(가리키는 하위 패키지, "a -> b"), …}} — 모듈 최상위 import 만."""
    out: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for module, source in files.items():
        here = _subpackage(module)
        if here is None:
            continue
        for node in ast.parse(source).body:
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                targets = [node.module]
            elif isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            else:
                continue
            for target in targets:
                there = _subpackage(target) if target.startswith("nexus.") else None
                if there and there != here:
                    out[here].add((there, f"{module} -> {target}"))
    return out


def _cycles(edges: dict[str, set[tuple[str, str]]]) -> list[str]:
    """두 하위 패키지가 서로를 가리키는 쌍과 그 근거 import."""
    graph = {a: {b for b, _ in v} for a, v in edges.items()}
    found = []
    for a, targets in graph.items():
        for b in targets:
            if a < b and a in graph.get(b, set()):
                why = sorted(w for x, w in edges[a] | edges[b] if x in (a, b))
                found.append(f"{a} <-> {b}: " + "; ".join(why))
    return found


def _package_files() -> dict[str, str]:
    files = {}
    for f in PACKAGE.rglob("*.py"):
        parts = list(f.relative_to(PACKAGE.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        files[".".join(parts)] = f.read_text(encoding="utf-8")
    return files


def test_no_two_subpackages_import_each_other():
    assert _cycles(_edges(_package_files())) == []


def test_the_check_can_actually_fail():
    """대조군 — 옮기기 전의 모양(서로를 가리키는 두 모듈)을 넣으면 잡혀야 한다."""
    files = {
        "nexus.llm.answer": "from nexus.search.evidence_packet import x\n",
        "nexus.search.evidence_packet": "from nexus.llm.citations import as_quoted_content\n",
    }
    assert len(_cycles(_edges(files))) == 1


def test_a_deferred_import_is_not_counted():
    files = {
        "nexus.llm.answer": "from nexus.search.evidence_packet import x\n",
        "nexus.search.evidence_packet": "def f():\n    from nexus.llm.citations import y\n",
    }
    assert _cycles(_edges(files)) == []
