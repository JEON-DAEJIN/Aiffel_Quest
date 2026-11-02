"""② 답 만들기 규칙만 따로 시험: 도구가 '없다'고 한 결과를 주고 같은 질문을 여러 번 보낸다(도구 선택은 건너뜀).
수정 전 규칙(git 의 HEAD 의 persona)과 수정 뒤 규칙을 같은 입력으로 비교한다."""
import os
import subprocess
import sys
import types

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local", "LANGFUSE_TRACING_ENABLED": "false"})

from app import agent, persona, when  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402

settings = load_settings()
llm = make_llm(settings)
now = when.now_in("Asia/Seoul")
tool_lines = ["2026-11-02부터 2026-11-30까지 공휴일이 없습니다(이 기간 밖은 조회하지 않았습니다)."]
question = "다음 공휴일이 언제고 어떤 날인지 알려줘"


def ask(label, n=5):
    bad = 0
    for i in range(n):
        system = agent.system_prompt(persona.DEFAULT_CHARACTER, now, "서울", [], None, tool_lines)
        reply = "".join(llm.chat_stream([{"role": "system", "content": system}, {"role": "user", "content": question}]))
        fabricated = any(k in reply for k in ("11월 9일", "한글날", "11월 1", "개천절")) and "없" not in reply
        bad += fabricated
        print(f"[{label} {i + 1}] {'지어냄' if fabricated else '정직'}: {reply[:120]}")
    print(f"=> {label}: 지어낸 것 {bad}/{n}")


ask("수정 뒤 규칙")
old = subprocess.run(["git", "show", "HEAD:app/persona.py"], capture_output=True, text=True, encoding="utf-8", cwd=REPO).stdout
module = types.ModuleType("persona_old")
exec(compile(old, "persona_old", "exec"), module.__dict__)
persona.FIXED_RULES = module.FIXED_RULES
persona.build_persona.__globals__["FIXED_RULES"] = module.FIXED_RULES
ask("수정 전 규칙")
