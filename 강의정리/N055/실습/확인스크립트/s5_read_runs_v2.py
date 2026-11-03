"""N055 4단계: holiday-reply-v2 실험의 항목별 답과 두 심사(holiday-reply-judge = v1 문장, holiday-reply-judge-v2 = 보완판)의 판정·이유를 읽는다(읽기 전용).
사용: python s5_read_runs_v2.py <실험 이름> ...   예) reply2-v1-1 reply2-v1-2   (DUMP=경로 로 JSON 저장)
- 실험 항목(experiments API)에서 답과 점수(holiday-reply-judge)를 읽고,
- 판단 이유는 심사 호출 기록(환경 langfuse-llm-as-a-judge 의 'Execute evaluator' 관찰 단위 출력)에서 답 문장으로 찾아 붙인다.
키는 출력하지 않는다."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local"})

from app.config import load_settings  # noqa: E402

load_settings()
from langfuse import Langfuse  # noqa: E402

c = Langfuse()
since = datetime.now(timezone.utc) - timedelta(hours=int(os.environ.get("HOURS", "6")))
wanted = sys.argv[1:]
exps = [e for e in c.api.experiments.list(from_start_time=since).data if any(e.name.startswith(w) or e.name == w for w in wanted)]
exps.sort(key=lambda e: e.name)

judge = []
cursor = None
while True:
    r = c.api.observations.get_many(from_start_time=since, limit=200, fields="core,basic,io", cursor=cursor,
                                    environment=["langfuse-llm-as-a-judge"])
    judge += r.data
    cursor = getattr(getattr(r, "meta", None), "cursor", None)
    if not cursor or not r.data:
        break


def reason_for(answer, v2):
    for o in judge:
        if answer and answer in str(o.input) and (("추측으로만" in str(o.input)) == v2):
            try:
                return json.loads(o.output).get("scoreExplanation", "")
            except Exception:
                return str(o.output)[:200]
    return ""


ds = {i.id: i for i in c.get_dataset("holiday-reply-v2").items}
results = {}
for e in exps:
    out = {}
    items = c.api.experiments.list_items(from_start_time=since, experiment_id=e.id, fields="core,io,scores", limit=100).data
    for it in items:
        d = ds.get(it.experiment_item_id)
        hid = d.metadata["id"] if d else it.experiment_item_id
        sc1 = [s for s in (it.scores or []) if s.name == "holiday-reply-judge"]
        sc2 = [s for s in (it.scores or []) if s.name == "holiday-reply-judge-v2"]
        answer = it.output if isinstance(it.output, str) else json.dumps(it.output, ensure_ascii=False)
        out[hid] = {"kind": d.metadata["kind"] if d else "?", "message": d.input["message"] if d else "",
                    "cond": d.expected_output if d else "", "tool_result": d.input["tool_result"] if d else "",
                    "answer": answer, "verdict": sc1[0].value if sc1 else None, "reason": reason_for(answer, False),
                    "verdict2": sc2[0].value if sc2 else None, "reason2": reason_for(answer, True)}
    results[e.name.split(" - ")[0]] = out

names = sorted(results)
ids = sorted(next(iter(results.values())))
for hid in ids:
    print("=" * 78)
    f = results[names[0]][hid]
    print(f"{hid} [{f['kind']}] {f['message']}")
    print(f"  통과 조건: {f['cond']}")
    print(f"  도구 결과: {f['tool_result'][:110]}")
    for n in names:
        r = results[n][hid]
        mark = {True: "통과", False: "실패", None: "점수 없음"}.get(r["verdict"], r["verdict"])
        mark2 = {True: "통과", False: "실패", None: "점수 없음"}.get(r["verdict2"], r["verdict2"])
        print(f"  [{n}] 옛 심사 {mark} / 보완 심사 {mark2} | 답: {r['answer'][:150]}")
        print(f"      옛 이유: {r['reason'][:160]}")
        print(f"      새 이유: {r['reason2'][:160]}")
print("=" * 78)
for n in names:
    v = [results[n][h]["verdict"] for h in ids]
    v2 = [results[n][h]["verdict2"] for h in ids]
    print(n, "| 옛 심사 통과", sum(1 for x in v if x is True), "/ 실패", sum(1 for x in v if x is False), "/ 없음", sum(1 for x in v if x is None),
          "| 보완 심사 통과", sum(1 for x in v2 if x is True), "/ 실패", sum(1 for x in v2 if x is False), "/ 없음", sum(1 for x in v2 if x is None))
if len(names) == 2:
    diff = [h for h in ids if results[names[0]][h]["verdict"] != results[names[1]][h]["verdict"]]
    print("두 실행에서 판정이 다른 항목:", diff or "없음")

if os.environ.get("DUMP"):
    with open(os.environ["DUMP"], "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print("saved:", os.environ["DUMP"])
