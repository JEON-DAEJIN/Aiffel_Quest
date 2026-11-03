"""N055 4단계: 심사 지시문 v2 의 기준 5·6번이 경계 사례에서 무엇을 바꾸는지 본다. 사람 판정 22개에 없는 새 답 6개(내가 만든 합성 답)를 v1·v2 로 심사한다.
기대값은 내가 통과 조건의 문자 그대로 읽어 정한 것이라 '사람이 확정한 값'이 아니다. 사용: friend-agent 의 .venv 파이썬으로 실행"""
import json, os, re, sys
REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO); os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local", "LANGFUSE_TRACING_ENABLED": "false"})
from app.config import load_settings
settings = load_settings()
from openai import OpenAI
client = OpenAI(api_key=settings.api_key, base_url=settings.base_url or None, timeout=60)
H = r"C:\Users\ilove\Documents\Aiffel_Quest\강의정리\N055\실습"
COND = "12월 25일(금)이 토요일, 일요일과 이어져 25일부터 27일까지 쉰다고 말한다"
TOOL = "2026-12-01~2026-12-31 공휴일: 12월 25일(금) 크리스마스."
CASES = [  # (답, 기대 통과 여부, 무엇을 보는가)
    ("12월 25일이 금요일이라 주말까지 이어서 쉴 수도 있을 것 같아!", False, "추측으로만"),
    ("크리스마스가 금요일이라 주말이랑 붙으면 길게 쉴지도 몰라.", False, "추측으로만"),
    ("12월 25일은 크리스마스야. 연휴 맞아!", False, "연휴 한 낱말만"),
    ("25일 금요일부터 27일 일요일까지 사흘 쉴 수 있어!", True, "확정(통과)"),
    ("크리스마스가 금요일이라 주말이랑 이어져서 사흘 연휴야!", True, "확정(통과)"),
    ("크리스마스는 있는데 연휴는 아니야.", False, "연휴 아님"),
]
def blocks(path):
    got = re.findall(r"```text\n(.*?)```", open(path, encoding="utf-8").read(), re.S)
    return got[0].strip(), got[1].strip()
def judge(system, user_t, answer):
    inp = json.dumps({"message": "12월에 연휴 있어?", "tool_result": TOOL}, ensure_ascii=False)
    user = user_t.replace("{{input}}", inp).replace("{{output}}", answer).replace("{{ground_truth}}", COND)
    r = client.chat.completions.create(model="gpt-4.1", temperature=0, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": {"name": "verdict", "strict": True, "schema": {"type": "object",
        "properties": {"reason": {"type": "string"}, "passed": {"type": "boolean"}}, "required": ["reason", "passed"], "additionalProperties": False}}})
    return json.loads(r.choices[0].message.content)
res = {}
for name, path in (("v1", H + r"\복붙용\holiday-reply-judge_심사지시문.md"), ("v2", H + r"\복붙용\holiday-reply-judge_심사지시문_v2.md")):
    s, u = blocks(path)
    res[name] = [judge(s, u, c[0]) for c in CASES]
for i, (ans, want, what) in enumerate(CASES):
    f = lambda n: ("통과" if res[n][i]["passed"] else "실패")
    print(f"[{what}] 기대 {'통과' if want else '실패'} | v1 {f('v1')} | v2 {f('v2')} | {ans}")
print("v1 기대와 일치", sum(1 for i, c in enumerate(CASES) if res["v1"][i]["passed"] == c[1]), "/ 6,  v2 기대와 일치", sum(1 for i, c in enumerate(CASES) if res["v2"][i]["passed"] == c[1]), "/ 6")
json.dump(res, open(H + r"\확인스크립트\s5_boundary_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
