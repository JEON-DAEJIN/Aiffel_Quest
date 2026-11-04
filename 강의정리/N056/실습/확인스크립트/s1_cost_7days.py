"""N056 2장 '직접 확인할 곳: Langfuse에서 원가 표 채우기'(1~3번)를 API로 한다.
최근 7일의 GENERATION을 모아 chat-turn 트레이스(메시지 한 건)별 비용을 더하고,
평균·중앙값·상위 10%·최댓값과 단계(generation 이름)별 비용을 환경별로 보인다. 읽기만 한다(LLM 호출 없음).
키·입력·출력 원문·프로젝트 ID는 출력하지 않는다. 결과 원자료는 s1_cost_7days.json에 남긴다."""
import json, os, statistics, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO); os.chdir(REPO)
from app import observe  # noqa: E402
from app.config import load_settings  # noqa: E402

load_settings()
c = observe.get_client()
since = datetime.now(timezone.utc) - timedelta(days=7)

# 1) 최근 7일 chat-turn 트레이스 id (서비스의 대화 턴만. 평가·심사 트레이스는 제외)
#    (이 SDK에는 트레이스 목록 API가 없어, 이름이 chat-turn인 루트 관찰 단위로 찾는다)
turns = {}
cursor = None
while True:
    kw = dict(from_start_time=since, name="chat-turn", is_root_observation=True, limit=1000, fields="core,basic")
    if cursor:
        kw["cursor"] = cursor
    r = c.api.observations.get_many(**kw)
    for t in r.data:
        turns[t.trace_id] = {"env": t.environment, "user": t.user_id, "session": t.session_id, "time": str(t.start_time)}
    cursor = getattr(r.meta, "cursor", None) if getattr(r, "meta", None) else None
    if not cursor or not r.data:
        break
print("chat-turn 트레이스(최근 7일):", len(turns))

# 2) 같은 기간 GENERATION 전부 → 트레이스별로 묶기
gens = []
cursor = None
while True:
    kw = dict(from_start_time=since, type="GENERATION", limit=1000, fields="core,basic,model,usage")
    if cursor:
        kw["cursor"] = cursor
    r = c.api.observations.get_many(**kw)
    gens += r.data
    cursor = getattr(r.meta, "cursor", None) if getattr(r, "meta", None) else None
    if not cursor or not r.data:
        break
by_trace = defaultdict(list)
for g in gens:
    if g.trace_id in turns:
        by_trace[g.trace_id].append(g)
print("GENERATION 전체:", len(gens), "| chat-turn에 속한 것:", sum(len(v) for v in by_trace.values()))

rows = []
for tid, gs in by_trace.items():
    cost = sum(float(g.total_cost or 0) for g in gs)
    rows.append({
        "trace": tid, **turns[tid], "cost_usd": cost, "calls": len(gs),
        "models": sorted({g.model or "?" for g in gs}),
        "steps": {g.name: {"cost": float(g.total_cost or 0), "in": int((g.usage_details or {}).get("input", 0)),
                           "out": int((g.usage_details or {}).get("output", 0))} for g in gs},
    })


def summary(rs, title):
    costs = sorted(x["cost_usd"] for x in rs)
    if not costs:
        print(f"\n[{title}] 없음"); return
    p90 = costs[max(0, int(len(costs) * 0.9) - 1)] if len(costs) >= 10 else None
    print(f"\n[{title}] 메시지 {len(costs)}건 | 모델 {sorted({m for x in rs for m in x['models']})}")
    print(f"  평균 ${statistics.mean(costs):.6f} · 중앙값 ${statistics.median(costs):.6f} · "
          f"상위10%(p90) {'$%.6f' % p90 if p90 is not None else '표본<10'} · 최댓값 ${costs[-1]:.6f}")
    print(f"  호출 수/메시지: {sorted({x['calls'] for x in rs})}")
    step = defaultdict(list)
    for x in rs:
        for name, s in x["steps"].items():
            step[name].append(s)
    for name, ss in sorted(step.items(), key=lambda kv: -statistics.mean(s["cost"] for s in kv[1])):
        print(f"  단계 {name:<16} 평균 ${statistics.mean(s['cost'] for s in ss):.6f} · "
              f"입력 {statistics.mean(s['in'] for s in ss):.0f}토큰 · 출력 {statistics.mean(s['out'] for s in ss):.0f}토큰 · {len(ss)}회")


summary(rows, "전체")
for env in sorted({x["env"] for x in rows}):
    summary([x for x in rows if x["env"] == env], f"environment={env}")

# 공개 저장소에 올라가므로 트레이스 ID·사용자 UUID는 앞 8자만 남긴다
_uuid = __import__("re").compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
for x in rows:
    x["trace"] = x["trace"][:8] + "…"
    for k in ("user", "session"):
        if isinstance(x.get(k), str):
            x[k] = _uuid.sub(lambda mm: mm.group(0)[:8] + "…", x[k])
json.dump(rows, open(os.path.join(HERE, "s1_cost_7days.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n원자료:", os.path.join(HERE, "s1_cost_7days.json"))
