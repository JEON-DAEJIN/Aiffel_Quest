"""앞선 대화에 같은 질문의 틀린 답이 쌓여 있을 때, 정확한 도구 결과를 주어도 모델이 앞선 말을 따라 하는지 확인한다.
규칙 A(지금 규칙)와 규칙 B(앞선 말과 달라도 도구 결과를 따르라는 줄을 더한 것)를 같은 입력으로 N번씩 비교한다.
판정은 객관적으로: 답에 '12월 25일'(정답)이 있으면 정답, 없으면 오답."""
import os
import sys

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local", "LANGFUSE_TRACING_ENABLED": "false"})

from app import agent, persona, when  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 6
settings = load_settings()
llm = make_llm(settings)
now = when.now_in("Asia/Seoul")
tool_lines = ["2026-11-02~2027-11-02 공휴일: 12월 25일(금) 크리스마스, 1월 1일(금) 새해, 2월 6일(토) 설날, 2월 8일(월) 설날, 2월 9일(화) 설날, 3월 1일(월) 3·1절 외 11일."]
wrong = ["다음 공휴일은 11월 9일(월)이야! 그때 어떤 계획 있어? 😊",
         "다음 공휴일은 11월 9일(월)이고, 한글날이야! 그날 쉬는 시간이니까 뭔가 계획 세우기 좋아! 😊",
         "다음 공휴일은 11월 9일(월)이야! 그날은 한글날이기도 해. 특별한 계획 있어? 😊"]
asks = ["다음 공휴일이 언제야?", "다음 공휴일이 언제고 어떤 날인지 알려줘", "다음 공휴일은 언제야?"]
history = []
for q, a in zip(asks, wrong):
    history += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
question = "다음 공휴일이 언제지?"

NEW_LINE = ("- [도구 결과]가 있으면 앞선 대화에서 내가 한 말과 달라도 도구 결과를 따른다. "
            "앞선 내 답이 도구 결과와 다르면 같은 말을 되풀이하지 말고 '아까는 잘못 말했어'라고 바로잡는다.")
base = persona.FIXED_RULES


def run(label, rules):
    persona.FIXED_RULES = rules
    ok = 0
    for i in range(N):
        system = agent.system_prompt(persona.DEFAULT_CHARACTER, now, "서울", [], None, tool_lines)
        reply = "".join(llm.chat_stream([{"role": "system", "content": system}, *history, {"role": "user", "content": question}]))
        good = "12월 25일" in reply
        ok += good
        print(f"[{label} {i + 1}] {'정답' if good else '오답'}: {reply[:110]}")
    print(f"=> {label}: 정답 {ok}/{N}")
    return ok


run("A 지금 규칙", base)
run("B 새 줄 추가", base.replace("- 사용자 설정 칸에", NEW_LINE + "\n- 사용자 설정 칸에"))
