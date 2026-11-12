"""인용 문법 — `[출처: …]` 의 여는 표기와, 답변 근거 본문 안에서 그 문법을 벗기는 함수.

⛔ **왜 따로 있나 (2026-11-12 구조 점검).** `as_quoted_content` 는 `llm/citations.py` 에 있었고,
근거 묶음을 글로 바꾸는 `search/evidence_packet.py` 가 그것을 가져갔다. 그런데 `llm/answer.py` 는
`search` 의 여러 모듈을 가져오므로 `llm` 과 `search` 가 서로를 import 하는 순환이 생겼다. 문법
자체는 어느 쪽 것도 아니라 여기 둔다: `search` 가 쓰고, 인용 검증기(`llm/citations.py`)는 같은
여는 표기를 여기서 가져간다.
"""

from __future__ import annotations

#: 인용 문법의 여는 표기. 검증기와 벗기기가 같은 값을 쓴다.
CITATION_OPEN = "[출처:"


#: 답변 근거 본문 안의 인용 표기를 **내용으로** 바꾼 모양. 인용 문법이 아니어야 한다.
QUOTED_PREFIX = "(그 문서가 댄 근거: "


def as_quoted_content(text: str) -> str:
    """답변 근거 본문 안의 `[출처: …]` 를 **인용이 아닌 내용**으로 바꾼다.

    ⛔ **왜 필요한가 (실측 2026-09-23).** 설명 레이어의 LLM 설명이 코퍼스에 들어오면서, 그
    본문에 `[출처: 인터페이스 계약 명세서 …]` 가 **글자로** 들어 있게 됐다. 답이 그것을
    **제 인용으로 옮겨 적었다** — 그 문서는 근거 묶음에 없었다. 지난 답의 인용이 새 답의
    인용으로 승격되는 것이고, **한 세대에 한 번씩 근거 없이 신뢰가 오른다.**

    등급 주석에 *"이 문서 안에 적힌 인용은 이 문서의 내용이지 네 근거가 아니다"* 를 넣어
    막았는데, **넷 중 하나에서 다시 났다.** 프롬프트만이 지키는 약속은 확률이다.

    ⭐ **그리고 이 자리는 애초에 우리가 만든 것이다.** 우리가 **인용 문법 그대로인 문자열**을
    모델에게 먹이고, 같은 문법으로 인용을 쓰라고 시킨다. 베끼는 것이 이상한 일이 아니다.
    ⇒ 주석이 *"이것은 내용이다"* 라고 **말하는** 대신, 근거 묶음이 그것을 **내용으로 보여 준다.**

    ⚠ **지우지 않는다.** 그 설명이 무엇을 근거로 댔는지는 **그 문서의 내용**이고, 지우면
    읽는 쪽이 그 사실을 잃는다. 문법만 벗긴다.

    ⚠ 제목에 대괄호가 들어갈 수 있으므로 `llm/citations.py::_inner_citations` 와 **같은 깊이 세기**를 쓴다 —
    정규식으로 첫 `]` 에서 끊으면 `[파티룸] 디제잉 정책` 같은 제목이 잘린다(2026-08-08).
    """
    out, i = [], 0
    while (start := text.find(CITATION_OPEN, i)) != -1:
        depth, j = 1, start + len(CITATION_OPEN)
        while j < len(text) and depth:
            if text[j] == "[":
                depth += 1
            elif text[j] == "]":
                depth -= 1
            j += 1
        if depth:                      # 안 닫혔다 — 남은 것은 그대로 둔다
            break
        out.append(text[i:start])
        out.append(QUOTED_PREFIX + text[start + len(CITATION_OPEN):j - 1].strip() + ")")
        i = j
    out.append(text[i:])
    return "".join(out)
