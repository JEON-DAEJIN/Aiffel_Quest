"""실제로 틀린 답을 낸 reply 의 입력(시스템 지시문 + 대화 21개 + 질문)을 트레이스에서 그대로 꺼내
같은 입력으로 N번 다시 보낸다. A = 기록된 그대로, B = 시스템 지시문에 '앞선 말과 달라도 도구 결과를 따른다' 줄을 더한 것.
판정은 객관적으로: 답에 '12월 25일'(정답)이 있으면 정답. 개인 내용은 출력하지 않는다."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local", "LANGFUSE_TRACING_ENABLED": "false"})

from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
settings = load_settings()
llm = make_llm(settings)

# 트레이스 조회는 Langfuse 를 켠 클라이언트가 필요해서 따로 만든다
os.environ["LANGFUSE_TRACING_ENABLED"] = "true"
from langfuse import Langfuse  # noqa: E402

client = Langfuse(base_url=os.environ.get("LANGFUSE_BASE_URL") or None)
since = datetime.now(timezone.utc) - timedelta(minutes=40)
res = client.api.observations.get_many(from_start_time=since, limit=200, fields="core,basic,time,io")
rows = sorted(res.data, key=lambda o: str(o.start_time))
by = {}
for o in rows:
    by.setdefault(o.trace_id, []).append(o)

NEW_LINE = ("- [도구 결과]가 있으면 앞선 대화에서 내가 한 말과 달라도 도구 결과를 따른다. "
            "앞선 내 답이 도구 결과와 다르면 같은 말을 되풀이하지 말고 '아까는 잘못 말했어'라고 바로잡는다.")
ANCHOR = "- 사용자 설정 칸에"

cases = []
for tid, obs in by.items():
    root = next((o for o in obs if o.name == "chat-turn"), None)
    reply = next((o for o in obs if o.name == "reply"), None)
    if not root or not reply:
        continue
    t = str(root.start_time)[11:19]
    if not ("01:26:00" <= t <= "01:28:00") or "공휴일" not in str(root.input):
        continue
    msgs = reply.input if isinstance(reply.input, list) else json.loads(reply.input)
    cases.append((t, msgs))
print("재생할 실제 입력:", [(t, len(m)) for t, m in cases])


def ask(msgs, rules_variant):
    msgs = [dict(m) for m in msgs]
    if rules_variant == "B":
        assert ANCHOR in msgs[0]["content"], "앵커 줄을 못 찾음"
        msgs[0]["content"] = msgs[0]["content"].replace(ANCHOR, NEW_LINE + "\n" + ANCHOR, 1)
    return "".join(llm.chat_stream(msgs))


for variant, label in (("A", "A 기록된 그대로"), ("B", "B 새 줄 추가")):
    good = total = 0
    for t, msgs in cases:
        for i in range(N):
            reply = ask(msgs, variant)
            ok = "12월 25일" in reply
            good += ok
            total += 1
            print(f"[{label} {t} #{i + 1}] {'정답' if ok else '오답'}: {reply[:90]}")
    print(f"=> {label}: 정답 {good}/{total}")
