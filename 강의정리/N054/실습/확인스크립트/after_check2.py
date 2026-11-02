"""수정 뒤 같은 질문을 실제 LLM 으로 여러 번 보내 도구 선택(범위)과 답을 확인한다."""
import json
import os
import sys

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local"})

from app import agent, observe  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402
from app.store.memory_store import MemoryStore  # noqa: E402

settings = load_settings()
llm = make_llm(settings)
questions = sys.argv[2:] or ["다음 공휴일이 언제고 어떤 날인지 알려줘", "다음 공휴일이 언제야?"]
runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
for q in questions:
    print("=" * 60)
    print("질문:", q)
    for i in range(runs):
        store = MemoryStore()
        events = list(agent.run_turn(q, f"u{i}", llm, store, True))
        turn = next(e for e in events if e["type"] == "turn")
        tools = [(t["name"], t["args"]) for t in turn["tools"]]
        results = [e["summary"] for e in events if e["type"] == "tool"]
        reply = "".join(e["text"] for e in events if e["type"] == "delta")
        print(f"[{i + 1}] 도구:", json.dumps(tools, ensure_ascii=False), "| 확신도:", turn["confidence"], "| 행동:", turn["action"], "| 결정:", turn["decided_by"])
        print("    이유:", turn["reason"], "| 가드:", turn["guards"])
        print("    결과:", results)
        print("    답:", reply)
client = observe.get_client()
if client:
    client.flush()
