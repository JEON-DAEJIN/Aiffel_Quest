"""N056 2장 '직접 확인할 곳' 4번: 한 대화 안에서 16턴 이어지는 대화를 실제 LLM으로 보내고,
턴마다 비용·호출 수·단계별 입력 토큰을 읽어 '첫 메시지 vs 열 번째 이후'를 비교한다.
로컬(ENV=local), 저장소는 메모리(한 대화를 같은 저장소로 이어 감), 인증 없음. 키·답 원문은 출력하지 않는다.
결과 원자료는 s2_long_conversation.json."""
import json, os, statistics, sys, time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO); os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local"})

from app import agent, observe  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402
from app.store.memory_store import MemoryStore  # noqa: E402

UID = "n056-long"
MESSAGES = [
    "안녕! 나 오늘 처음 왔어",                         # 1 인사
    "오늘 서울 날씨 어때?",                           # 2 날씨
    "그럼 우산 챙겨야 할까?",                         # 3 앞 말 이어받기
    "요즘 회사 일이 많아서 좀 지쳐",                    # 4 고민
    "팀장님이 일을 자꾸 나한테만 몰아줘",                # 5 고민 이어서
    "어떻게 말하면 기분 안 상하게 얘기할 수 있을까?",     # 6 상담
    "다음 공휴일 언제야?",                            # 7 공휴일
    "그날 친구랑 영화 보기로 했어. 오후 3시에 알려 줘",   # 8 약속(알림)
    "아 그리고 나 고양이 키워. 이름은 보리야",            # 9 기억할 정보
    "보리가 요즘 밥을 잘 안 먹어서 걱정이야",             # 10 고민
    "아까 내가 회사 얘기한 거 기억나?",                 # 11 앞 대화 참조
    "주말에 뭐 하면 기분 전환이 될까?",                  # 12 추천
    "12월에 연휴 있어?",                             # 13 공휴일
    "그때 부모님 댁에 갈까 생각 중이야",                 # 14 이어받기
    "오늘 얘기한 것 중에 내가 제일 걱정하는 게 뭐 같아?",  # 15 요약 요청
    "고마워, 오늘 얘기 들어줘서",                       # 16 마무리
]

settings = load_settings()
llm = make_llm(settings)
print("provider:", settings.provider, "model:", settings.model, "| now:", datetime.now().strftime("%Y-%m-%d %a %H:%M"))
since = datetime.now(timezone.utc) - timedelta(seconds=3)
store = MemoryStore()
starts = []
for i, m in enumerate(MESSAGES, 1):
    starts.append(datetime.now(timezone.utc))
    events = list(agent.run_turn(m, UID, llm, store, False))
    print(f"turn {i:2d} 보냄 (events {len(events)})")

client = observe.get_client()
client.flush()
time.sleep(25)


def fetch(**kw):
    out, cursor = [], None
    while True:
        if cursor:
            kw["cursor"] = cursor
        r = client.api.observations.get_many(**kw)
        out += r.data
        cursor = getattr(r.meta, "cursor", None) if getattr(r, "meta", None) else None
        if not cursor or not r.data:
            return out


roots = sorted(fetch(from_start_time=since, name="chat-turn", is_root_observation=True, user_id=UID,
                     limit=1000, fields="core,basic"), key=lambda o: str(o.start_time))
gens = fetch(from_start_time=since, type="GENERATION", user_id=UID, limit=1000, fields="core,basic,model,usage")
print("트레이스:", len(roots), "/ 보낸 턴:", len(MESSAGES), "| generation:", len(gens))

rows = []
for i, root in enumerate(roots, 1):
    gs = [g for g in gens if g.trace_id == root.trace_id]
    steps = {g.name: {"cost": float(g.total_cost or 0), "in": int((g.usage_details or {}).get("input", 0)),
                      "out": int((g.usage_details or {}).get("output", 0))} for g in gs}
    rows.append({"turn": i, "message": MESSAGES[i - 1] if i <= len(MESSAGES) else "?",
                 "cost_usd": sum(s["cost"] for s in steps.values()), "calls": len(gs), "steps": steps})
    s = steps
    print(f"turn {i:2d} ${rows[-1]['cost_usd']:.6f} 호출 {len(gs)} | "
          + " · ".join(f"{k} 입력{v['in']}/출력{v['out']}" for k, v in s.items()))

first = rows[0]["cost_usd"] if rows else 0
late = [r["cost_usd"] for r in rows if r["turn"] >= 10]
if rows and late:
    print(f"\n첫 메시지 ${first:.6f} · 10번째 이후 평균 ${statistics.mean(late):.6f} (×{statistics.mean(late) / first:.2f})"
          f" · 대화 전체 평균 ${statistics.mean(r['cost_usd'] for r in rows):.6f} · 합계 ${sum(r['cost_usd'] for r in rows):.6f}")
json.dump(rows, open(os.path.join(HERE, "s2_long_conversation.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
