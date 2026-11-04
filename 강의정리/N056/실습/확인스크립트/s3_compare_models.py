"""N056 3장 '직접 확인할 곳: 같은 메시지로 두 모델 비교하기'.
같은 메시지 10개를 같은 순서로 지금 모델(gpt-4o-mini)과 한 단계 큰 모델로 보내고,
모델마다 비용 합계·평균과 메시지별 답을 나란히 남긴다.
.env는 열거나 고치지 않는다 — 앱의 load_dotenv가 이미 있는 환경변수를 덮지 않으므로(setdefault)
이 프로세스에서만 LLM_MODEL을 정해 바꾼다(교안의 '.env 수정 → 서버 재시작 → 원래대로'와 같은 효과).
사용: python s3_compare_models.py [큰 모델 이름, 기본 gpt-4o]
결과: s3_compare_models.json, s3_answers_side_by_side.md(사람이 나란히 읽는 표)"""
import json, os, statistics, sys, time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
BIG = sys.argv[1] if len(sys.argv) > 1 else "gpt-4o"
sys.path.insert(0, REPO); os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local"})

from app import agent, observe  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402
from app.store.memory_store import MemoryStore  # noqa: E402

# 교안: 인사, 날씨나 공휴일 묻기, 고민 털어놓기, 약속 잡기를 섞고 앞 메시지를 이어 받는 메시지도 두세 개
MESSAGES = [
    ("인사", "안녕! 오늘 하루 어땠어?"),
    ("날씨", "내일 서울 날씨 어때?"),
    ("이어받기", "그럼 뭐 입고 나가면 좋을까?"),
    ("공휴일", "이번 달에 쉬는 날 있어?"),
    ("고민", "요즘 잠을 잘 못 자. 누우면 생각이 많아져"),
    ("이어받기", "그런 생각이 주로 일 걱정이야. 어떻게 하면 좀 내려놓을 수 있을까?"),
    ("약속", "토요일 오후 2시에 친구랑 점심 약속 있어. 전날 밤에 알려 줘"),
    ("고민", "친구가 요즘 연락을 잘 안 받아서 서운해"),
    ("이어받기", "내가 먼저 연락하는 게 맞을까, 기다리는 게 맞을까?"),
    ("맞장구", "고마워, 덕분에 좀 나아졌어"),
]


def run(model):
    os.environ["LLM_MODEL"] = model
    settings = load_settings()
    llm = make_llm(settings)
    uid = f"n056-cmp-{model}"
    store = MemoryStore()
    since = datetime.now(timezone.utc) - timedelta(seconds=3)
    answers = []
    for kind, m in MESSAGES:
        text, tools = "", []
        for e in agent.run_turn(m, uid, llm, store, False):
            if e.get("type") == "delta":
                text += e.get("text", "")
            elif e.get("type") == "turn":
                tools = [t["name"] for t in e.get("tools", [])]
        answers.append({"kind": kind, "message": m, "answer": text.strip(), "tools": tools})
        print(f"[{settings.model}] {kind} 보냄")
    return settings.model, uid, since, answers


results = {}
for model in ["gpt-4o-mini", BIG]:
    name, uid, since, answers = run(model)
    results[name] = {"uid": uid, "since": since, "answers": answers}

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


summary = {}
for name, r in results.items():
    roots = sorted(fetch(from_start_time=r["since"], name="chat-turn", is_root_observation=True, user_id=r["uid"],
                         limit=1000, fields="core,basic"), key=lambda o: str(o.start_time))
    gens = fetch(from_start_time=r["since"], type="GENERATION", user_id=r["uid"], limit=1000,
                 fields="core,basic,model,usage")
    per = []
    for root in roots:
        gs = [g for g in gens if g.trace_id == root.trace_id]
        per.append({"cost": sum(float(g.total_cost or 0) for g in gs),
                    "models": sorted({g.model or "?" for g in gs}),
                    "reply_out": sum(int((g.usage_details or {}).get("output", 0)) for g in gs if g.name == "reply"),
                    "priced": all(g.total_cost is not None for g in gs)})
    for a, p in zip(r["answers"], per):
        a.update(p)
    costs = [p["cost"] for p in per]
    summary[name] = {"traces": len(roots), "total_usd": sum(costs), "mean_usd": statistics.mean(costs) if costs else 0,
                     "models_seen": sorted({m for p in per for m in p["models"]}),
                     "all_priced": all(p["priced"] for p in per),
                     "reply_out_mean": statistics.mean(p["reply_out"] for p in per) if per else 0}
    s = summary[name]
    print(f"{name}: 트레이스 {s['traces']} · 합계 ${s['total_usd']:.6f} · 평균 ${s['mean_usd']:.6f} · "
          f"답 출력 평균 {s['reply_out_mean']:.0f}토큰 · 가격 모두 계산됨 {s['all_priced']} · 모델 {s['models_seen']}")

names = list(results)
if summary[names[0]]["total_usd"]:
    print(f"비용 배수: ×{summary[names[1]]['total_usd'] / summary[names[0]]['total_usd']:.1f}")

json.dump({"messages": MESSAGES, "summary": summary,
           "answers": {n: r["answers"] for n, r in results.items()}},
          open(os.path.join(HERE, "s3_compare_models.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)

lines = [f"# 같은 메시지 10개, 두 모델의 답 (N056 3장, {datetime.now():%Y-%m-%d})", "",
         f"| # | 종류 | 메시지 | {names[0]} | {names[1]} |", "|---|---|---|---|---|"]
cell = lambda s: s.replace("|", "\\|").replace("\n", " ")
for i, (kind, m) in enumerate(MESSAGES):
    a0, a1 = results[names[0]]["answers"][i], results[names[1]]["answers"][i]
    lines.append(f"| {i + 1} | {kind} | {cell(m)} | {cell(a0['answer'])} | {cell(a1['answer'])} |")
open(os.path.join(HERE, "s3_answers_side_by_side.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("나란히 읽기:", os.path.join(HERE, "s3_answers_side_by_side.md"))
