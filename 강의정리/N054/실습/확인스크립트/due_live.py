"""수정 뒤 부탁 표현별로 저장된 약속 날짜가 맞는지 실제 LLM 으로 확인한다. 기대 날짜는 오늘(2026-11-02 월요일) 달력으로 사람이 계산한 값이다."""
import os
import sys

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local", "LANGFUSE_TRACING_ENABLED": "false"})

from app import agent, when  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402
from app.store.memory_store import MemoryStore  # noqa: E402

settings = load_settings()
llm = make_llm(settings)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
cases = [
    ("다음 주 토요일 아침에 이사 준비하라고 알려 줘", "2026-11-14"),
    ("내일 아침 8시에 물 마시라고 알려 줘", "2026-11-03"),
    ("모레 저녁에 우산 챙기라고 알려 줘", "2026-11-04"),
    ("이번 주 금요일 오후 3시에 회의 있다고 알려 줘", "2026-11-06"),
    ("다음 주 수요일에 병원 가라고 알려 줘", "2026-11-11"),
]
total = good = 0
for q, expect in cases:
    ok = 0
    shown = []
    for i in range(N):
        store = MemoryStore()
        list(agent.run_turn(q, "d", llm, store, True))
        due = [r["due_at"].astimezone(when.now_in("Asia/Seoul").tzinfo).strftime("%Y-%m-%d %H:%M") for r in store.list_reminders("d", status="pending")]
        hit = bool(due) and due[0].startswith(expect)
        ok += hit
        shown.append(due[0] if due else "(없음)")
    total += N
    good += ok
    print(f"{q} → 기대 {expect} / 맞음 {ok}/{N} / 저장된 값: {shown}")
print(f"=> 전체 {good}/{total}")
