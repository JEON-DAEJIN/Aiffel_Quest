"""수정 뒤 이사 이야기 시나리오를 실제 LLM 으로 여러 번 보내 약속 저장과 기억을 확인한다(트레이스는 켜지 않는다)."""
import os
import sys

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local", "LANGFUSE_TRACING_ENABLED": "false"})

from app import agent, memory, when  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402
from app.store.memory_store import MemoryStore  # noqa: E402

settings = load_settings()
llm = make_llm(settings)
runs = int(sys.argv[1]) if len(sys.argv) > 1 else 6
now = when.now_in("Asia/Seoul")
for q in sys.argv[2:] or ["나 다음 주 토요일에 이사 가"]:
    print("=" * 60)
    print("질문:", q)
    saved = bad_weekday = 0
    for i in range(runs):
        store = MemoryStore()
        events = list(agent.run_turn(q, "m", llm, store, True))
        turn = next(e for e in events if e["type"] == "turn")
        tools = [t["name"] for t in turn["tools"]]
        reminders = store.list_reminders("m", status="pending")
        mems = [m["text"] for m in store.list_memories("m")]
        bad = [m for m in mems if memory.weekday_mismatch(m, now)]
        saved += bool(reminders)
        bad_weekday += bool(bad)
        due = [str(r["due_at"])[:16] for r in reminders]
        print(f"[{i + 1}] 도구={tools} 가드={turn['guards']} 약속={due} 기억={mems}")
    print(f"=> 약속이 저장된 횟수 {saved}/{runs}, 요일이 안 맞는 기억이 남은 횟수 {bad_weekday}/{runs}")
