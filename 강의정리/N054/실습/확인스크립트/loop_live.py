"""화면에서 '기억을 지웠는데도 똑같다'던 조건을 재현한다: 틀린 약속(11/7)이 남아 있고 앞선 대화에 틀린 답이 있는 상태에서
`나 다음주 토요일에 이사 가`를 보낸다. 실제 LLM, 트레이스는 끈다."""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local", "LANGFUSE_TRACING_ENABLED": "false"})

from app import agent  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402
from app.store.memory_store import MemoryStore  # noqa: E402

llm = make_llm(load_settings())
N = int(sys.argv[1]) if len(sys.argv) > 1 else 6
msg = sys.argv[2] if len(sys.argv) > 2 else "나 다음주 토요일에 이사 가"
kst = ZoneInfo("Asia/Seoul")
bad = list_used = 0
for i in range(N):
    store = MemoryStore()
    store.add_reminder("m", "이사 가기", datetime(2026, 11, 7, 9, 0, tzinfo=kst))
    store.add_message("m", "user", "나 다음 주 토요일에 이사 가")
    store.add_message("m", "assistant", "오, 그거 좋겠다! 이사 준비 잘하고 있구나?")
    store.add_message("m", "user", "내가 다음 주에 뭐 한다고 했지?")
    store.add_message("m", "assistant", "다음 주 토요일, 11월 7일에 이사 간다고 했어! 이사 준비 잘 하고 있지? 😊")
    events = list(agent.run_turn(msg, "m", llm, store, True))
    turn = next(e for e in events if e["type"] == "turn")
    tools = [t["name"] for t in turn["tools"]]
    reply = "".join(e["text"] for e in events if e["type"] == "delta")
    mems = [m["text"] for m in store.list_memories("m")]
    wrong = any("11월 7일" in m or "11월 12일" in m for m in mems) or "11월 7일" in reply
    bad += wrong
    list_used += "list_reminders" in tools
    print(f"[{i + 1}] 도구={tools} 가드={turn['guards']}\n    기억={mems}\n    답={reply[:80]} → {'틀림' if wrong else '맞음'}")
print(f"=> 틀린 값(11/7·11/12)이 기억이나 답에 나온 횟수 {bad}/{N}, list_reminders가 쓰인 횟수 {list_used}/{N}")
