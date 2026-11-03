"""N055 1단계 보충: '다음 공휴일' 실패가 재현되는지 같은 질문을 여러 번 더 보내 세고(기간 인자·답에 12월 25일이 있는지),
1단계에서 읽은 실패 트레이스에 '처음 틀린 단계' 한 줄 댓글을 단다(교안 2장 직접 확인 4번).
키·원문 전체는 출력하지 않는다. 사용: python s1b_repeat_and_comment.py [다음 공휴일 반복 횟수] [--no-comment]"""
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

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8
COMMENT = "--no-comment" not in sys.argv
settings = load_settings()
llm = make_llm(settings)
client = observe.get_client()
t_run = datetime.now(timezone.utc) - timedelta(seconds=3)

for i in range(N):
    list(agent.run_turn("다음 공휴일 언제야?", "n055-step1b", llm, MemoryStore(), False))
client.flush()
time.sleep(20)


def text(x):
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)


since = datetime.now(timezone.utc) - timedelta(minutes=60)
res = client.api.observations.get_many(from_start_time=since, limit=800, fields="core,basic,time,io")
by = {}
for o in sorted(res.data, key=lambda o: str(o.start_time)):
    by.setdefault(o.trace_id, []).append(o)


def summarize(obs):
    root = next((o for o in obs if o.name == "chat-turn"), None)
    choose = next((o for o in obs if o.name == "choose-tools"), None)
    reply = next((o for o in obs if o.name == "reply"), None)
    inp = root.input if root is not None else None
    msg = inp.get("message") if isinstance(inp, dict) and "message" in inp else text(inp)
    args = None
    try:
        args = json.loads(text(choose.output))["tools"][0]["args"] if choose else None
    except Exception:
        pass
    return msg, args, text(reply.output) if reply else ""


rows = [(tid,) + summarize(obs) for tid, obs in by.items() if any(o.name == "chat-turn" for o in obs)]

# 1) 다음 공휴일 반복 결과
a = [r for r in rows if r[1] == "다음 공휴일 언제야?" and r[0] and any(o.start_time and o.start_time >= t_run for o in by[r[0]])]
empty = sum(1 for r in a if not r[2])
ok = sum(1 for r in a if "12월 25일" in r[3] or "크리스마스" in r[3])
print(f"[다음 공휴일 {len(a)}번] 인자를 비움 {empty}/{len(a)} · 답에 크리스마스가 있음 {ok}/{len(a)}")
for r in a:
    print("  인자:", r[2], "| 답:", r[3][:70].replace("\n", " "))

# 2) 댓글: 이번 세션에서 읽은 실패 트레이스(연휴·시험 전날·올해 남은 빨간 날)
notes = {
    "12월에 연휴 있어?": "[N055] 답 만들기: 12/25(금)은 토·일과 이어 사흘 연휴인데 연휴라고 말하지 않음(도구 결과는 '12월 25일(금) 크리스마스'뿐)",
    "금요일 시험 전날 밤에 일찍 자라고 알려 줘": "[N055] 도구 선택: due_at이 시험 전날(목)이 아니라 금요일 21:00으로 들어감",
    "올해 남은 빨간 날 알려 줘": "[N055] 답 만들기: '올해 남은' 질문에 내년 1월 1일(새해)을 덧붙임",
}
if COMMENT:
    pid = client.api.projects.get().data[0].id
    n = 0
    for tid, msg, args, reply in rows:
        if msg in notes and any(o.start_time and o.start_time >= datetime.now(timezone.utc) - timedelta(minutes=50) for o in by[tid]):
            client.api.comments.create(project_id=pid, object_type="TRACE", object_id=tid, content=notes[msg])
            n += 1
    print("댓글 단 트레이스:", n)
