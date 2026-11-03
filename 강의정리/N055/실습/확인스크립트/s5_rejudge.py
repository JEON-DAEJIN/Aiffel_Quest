"""N055 4단계: 사람이 확정한 22개 답을 심사 지시문 v1·v2로 다시 심사해 사람 판정과 맞춘다(Langfuse 평가자를 바꾸기 전의 로컬 확인).
Langfuse 평가자와 같은 모델(gpt-4.1)·같은 System/User 문장·boolean 점수 + 판단 이유 구조지만, 변수 채움 방식(input 을 JSON 으로 넣음)은
Langfuse 와 글자 단위로 같다고 보증하지 않는다. 키는 출력하지 않는다.
사용: python s5_rejudge.py  (friend-agent 의 .venv 파이썬으로)"""
import json, os, re, sys
REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO); os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local", "LANGFUSE_TRACING_ENABLED": "false"})
from app.config import load_settings
settings = load_settings()   # 서비스가 쓰는 LLM_API_KEY(.env)를 환경에서 읽는다. 값은 출력하지 않는다
from openai import OpenAI
assert settings.provider == "openai", settings.provider
client = OpenAI(api_key=settings.api_key, base_url=settings.base_url or None, timeout=60)
H = r"C:\Users\ilove\Documents\Aiffel_Quest\강의정리\N055\실습"
key = json.load(open(H + r"\확인스크립트\s2_label_key.json", encoding="utf-8"))
dump = json.load(open(H + r"\확인스크립트\s2_runs_v1_dump.json", encoding="utf-8"))
human = json.load(open(H + r"\확인스크립트\s2_human_labels_confirmed.json", encoding="utf-8"))["labels"]

def blocks(path):
    t = open(path, encoding="utf-8").read()
    got = re.findall(r"```text\n(.*?)```", t, re.S)
    return got[0].strip(), got[1].strip()      # System, User

def judge(system, user_t, row):
    inp = json.dumps({"message": row["message"], "tool_result": row["tool_result"]}, ensure_ascii=False)
    user = user_t.replace("{{input}}", inp).replace("{{output}}", row["answer"]).replace("{{ground_truth}}", row["cond"])
    r = client.chat.completions.create(
        model="gpt-4.1", temperature=0,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": {"name": "verdict", "strict": True, "schema": {
            "type": "object", "properties": {"reason": {"type": "string"}, "passed": {"type": "boolean"}},
            "required": ["reason", "passed"], "additionalProperties": False}}})
    d = json.loads(r.choices[0].message.content)
    return d["passed"], d["reason"]

out = {}
for name, path in (("v1", H + r"\복붙용\holiday-reply-judge_심사지시문.md"), ("v2", H + r"\복붙용\holiday-reply-judge_심사지시문_v2.md")):
    system, user_t = blocks(path)
    res = {}
    for k in sorted(key):
        row = dump[key[k]["run"]][key[k]["item"]]
        res[k] = judge(system, user_t, row)
    out[name] = res
    agree = [k for k in res if res[k][0] == (human[k] == "O")]
    missed = [k for k in res if res[k][0] and human[k] == "X"]
    false_f = [k for k in res if (not res[k][0]) and human[k] == "O"]
    print(f"심사 {name}: 사람 판정과 일치 {len(agree)}/22, 놓친 실패 {missed}, 잘못된 실패 {false_f}")
    print("   다른 항목:", {k: ("심사 " + ("통과" if res[k][0] else "실패") + "/사람 " + human[k] + " | " + res[k][1][:90]) for k in res if k not in agree})
json.dump(out, open(H + r"\확인스크립트\s5_rejudge_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
