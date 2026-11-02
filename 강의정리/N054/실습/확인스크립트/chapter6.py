"""6장: 트레이스별 총 시간·단계별 시간·이름 없는 구간·토큰·비용을 읽기 전용으로 표로 낸다(원문은 출력하지 않음)."""
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
since = datetime.now(timezone.utc) - timedelta(minutes=int(sys.argv[1]) if len(sys.argv) > 1 else 60)
rows = []
cursor = None
while True:
    res = client.api.observations.get_many(from_start_time=since, limit=200, cursor=cursor, fields="core,basic,time,usage,cost,io")
    rows += res.data
    cursor = getattr(getattr(res, "meta", None), "cursor", None)
    if not cursor:
        break
by_trace = {}
for o in rows:
    by_trace.setdefault(o.trace_id, []).append(o)

print("필드 확인:", [k for k in ("calculated_total_cost", "total_cost", "cost_details", "usage_details", "time_to_first_token", "latency") if hasattr(rows[0], k)])


def cost(o):
    for k in ("calculated_total_cost", "total_cost"):
        v = getattr(o, k, None)
        if v is not None:
            return v
    d = getattr(o, "cost_details", None) or {}
    return d.get("total")


def sec(a, b):
    return (b - a).total_seconds()


table = []
for tid, obs in by_trace.items():
    root = next((o for o in obs if o.name in ("chat-turn", "greeting")), None)
    if not root or root.name != "chat-turn":
        continue
    # 가짜 LLM 테스트 트레이스는 건너뛴다(reply 토큰 0 + 모델 fake)
    gens = [o for o in obs if o.type == "GENERATION"]
    if not gens or sum(((g.usage_details or {}).get("input") or 0) for g in gens) == 0:
        continue
    t0 = root.start_time
    steps = {o.name: o for o in obs if o is not root}
    first = min(o.start_time for o in obs if o is not root)
    reply = steps.get("reply")
    row = {
        "start": str(t0)[11:19],
        "total": sec(t0, root.end_time),
        "pre": sec(t0, first),
        "choose": sec(steps["choose-tools"].start_time, steps["choose-tools"].end_time),
        "tool": sum(sec(o.start_time, o.end_time) for o in obs if o.name.startswith("tool:")),
        "reply": sec(reply.start_time, reply.end_time),
        "ttft": getattr(reply, "time_to_first_token", None),
        "mem": sec(steps["memory-update"].start_time, steps["memory-update"].end_time),
        "to_first_char": sec(t0, reply.start_time) + (getattr(reply, "time_to_first_token", 0) or 0),
        "tools": ",".join(sorted(n for n in steps if n.startswith("tool:"))) or "-",
        "tok_choose": (steps["choose-tools"].usage_details or {}),
        "tok_reply": (reply.usage_details or {}),
        "tok_mem": (steps["memory-update"].usage_details or {}),
        "cost": sum((cost(g) or 0) for g in gens),
        "tid": tid[:8],
    }
    table.append(row)
table.sort(key=lambda r: r["start"])
print()
print("시각     총시간  앞구간  choose  tool   reply  첫글자까지  memory | 도구                      | reply 입력/출력 | 비용$")
for r in table:
    print(f"{r['start']}  {r['total']:5.2f}  {r['pre']:5.2f}  {r['choose']:5.2f}  {r['tool']:5.2f}  {r['reply']:5.2f}  {r['to_first_char']:6.2f}   {r['mem']:5.2f} | {r['tools']:25s} | {r['tok_reply'].get('input')}/{r['tok_reply'].get('output')} | {r['cost']:.6f}")

print()
slow = max(table, key=lambda r: r["total"]); fast = min(table, key=lambda r: r["total"])
print("가장 느린:", slow["start"], round(slow["total"], 2), "초 / 가장 빠른:", fast["start"], round(fast["total"], 2), "초")
exp = max(table, key=lambda r: r["cost"]); chp = min(table, key=lambda r: r["cost"])
print("가장 비싼:", exp["start"], f"${exp['cost']:.6f}", "reply 입력", exp["tok_reply"].get("input"), "/ 가장 싼:", chp["start"], f"${chp['cost']:.6f}", "reply 입력", chp["tok_reply"].get("input"))
greet = [o for o in rows if o.name == "greeting" and any(g.trace_id == o.trace_id and (g.usage_details or {}).get("input") for g in rows if g.type == "GENERATION")]
print("메시지 수(진짜 LLM):", len(table), "| greeting 트레이스(진짜 LLM):", len(greet))
total_cost = sum(r["cost"] for r in table) + sum(cost(g) or 0 for g in rows if g.type == "GENERATION" and g.name == "greeting-reply" and (g.usage_details or {}).get("input"))
print(f"총비용(메시지+greeting): ${total_cost:.6f} / 메시지당 평균(chat-turn만): ${sum(r['cost'] for r in table) / len(table):.6f}")
