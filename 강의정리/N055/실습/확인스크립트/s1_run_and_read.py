"""N055 1단계: 교안의 네 대화(와 정상 사례 두 개)를 실제 LLM·실제 Langfuse 로 여러 번 재현하고,
방금 남은 트레이스를 거슬러 읽어 '도구 선택 인자 → 도구 결과 → 답' 한 줄씩 보여 준다.
키·원문 전체는 출력하지 않는다. 사용: python s1_run_and_read.py [반복 횟수]"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local"})

from app import agent, observe  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402
from app.store.memory_store import MemoryStore  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
MESSAGES = [
    ("A 다음 공휴일", "다음 공휴일 언제야?", N),
    ("B 12월 연휴", "12월에 연휴 있어?", N),
    ("C 시험 전날", "금요일 시험 전날 밤에 일찍 자라고 알려 줘", N),
    ("정상1 남은 빨간 날", "올해 남은 빨간 날 알려 줘", 1),
    ("정상2 이번 주", "이번 주에 쉬는 날 있어?", 1),
]

settings = load_settings()
llm = make_llm(settings)
print("provider:", settings.provider, "model:", settings.model, "| now:", datetime.now().strftime("%Y-%m-%d %a %H:%M"))
since = datetime.now(timezone.utc) - timedelta(seconds=3)
sent = []
for label, message, times in MESSAGES:
    for i in range(times):
        store = MemoryStore()          # 매번 새 대화(앞선 말이 쌓이지 않게)
        events = list(agent.run_turn(message, "n055-step1", llm, store, False))
        sent.append((label, message))
        print(f"sent {label} #{i + 1}: events={len(events)}")

client = observe.get_client()
client.flush()
time.sleep(20)
res = client.api.observations.get_many(from_start_time=since, limit=500, fields="core,basic,time,io")
rows = sorted(res.data, key=lambda o: str(o.start_time))
by_trace = {}
for o in rows:
    by_trace.setdefault(o.trace_id, []).append(o)
print("traces:", len(by_trace), "observations:", len(rows), "| 보낸 메시지:", len(sent))


def text(x):
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)


def short(x, n=110):
    s = text(x).replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"


out = []
for tid, obs in by_trace.items():
    root = next((o for o in obs if o.name == "chat-turn"), None)
    choose = next((o for o in obs if o.name == "choose-tools"), None)
    tools = [o for o in obs if str(o.name).startswith("tool:")]
    reply = next((o for o in obs if o.name == "reply"), None)
    msg = ""
    if root is not None:
        inp = root.input
        msg = inp.get("message") if isinstance(inp, dict) and "message" in inp else short(inp, 60)
    out.append({"trace_id": tid, "message": msg, "choose": text(choose.output) if choose else None,
                "tools": [(t.name, text(t.input), text(t.output)) for t in tools],
                "reply": text(reply.output) if reply else None})
for r in sorted(out, key=lambda r: r["message"]):
    print("-" * 70)
    print("질문:", short(r["message"], 60), "| trace", r["trace_id"][:8])
    print(" 도구 선택:", short(r["choose"], 200))
    for name, i, o in r["tools"]:
        print(" 도구 실행:", name, "입력", short(i, 90), "→ 결과", short(o, 140))
    print(" 답:", short(r["reply"], 160))
