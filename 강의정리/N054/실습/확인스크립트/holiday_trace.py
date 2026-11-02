"""도쿄·서울 트레이스를 읽기 전용으로 거슬러 읽는다. 기억 메모 등 개인 내용은 출력하지 않고
choose-tools 출력, 도구 span, reply 입력의 [도구 결과] 블록, reply 출력만 보여 준다."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none"})

from app import observe  # noqa: E402
from app.config import load_settings  # noqa: E402

load_settings()
client = observe.get_client()
since = datetime.now(timezone.utc) - timedelta(minutes=int(sys.argv[1]) if len(sys.argv) > 1 else 30)
res = client.api.observations.get_many(from_start_time=since, limit=200, fields="core,basic,time,io,usage")
rows = sorted(res.data, key=lambda o: str(o.start_time))
by_trace = {}
for o in rows:
    by_trace.setdefault(o.trace_id, []).append(o)


def text(x):
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)


def tool_block(inp):
    s = text(inp)
    try:
        msgs = json.loads(s)
        s = next(m["content"] for m in msgs if m["role"] == "system")
    except Exception:
        pass
    if "[도구 결과]" in s:
        return s.split("[도구 결과]", 1)[1].split("\\n\\n", 1)[0].split("\n\n", 1)[0].strip()
    return "(입력에 [도구 결과] 없음)"


for tid, obs in by_trace.items():
    root = next((o for o in obs if o.name == "chat-turn"), None)
    if root is None or "공휴일" not in text(root.input):
        continue
    print("=" * 60)
    print("chat-turn", str(root.start_time)[11:19], "| 사용자 메시지:", text(root.input)[:60])
    for o in obs:
        if o.name == "choose-tools":
            print("choose-tools 출력:", text(o.output)[:300])
            print("choose-tools 메타:", getattr(o, "metadata", None), "| 토큰:", getattr(o, "usage_details", None))
        if o.name.startswith("tool:"):
            print(o.name, "입력:", text(o.input)[:120], "| 출력:", text(o.output)[:200], "| 메타:", getattr(o, "metadata", None), "| level:", o.level)
    reply = next((o for o in obs if o.name == "reply"), None)
    if reply:
        print("reply 입력의 [도구 결과]:", tool_block(reply.input)[:400])
        print("reply 출력:", text(reply.output)[:300])
        print("reply 토큰:", getattr(reply, "usage_details", None), "| 첫 글자:", getattr(reply, "time_to_first_token", None))
