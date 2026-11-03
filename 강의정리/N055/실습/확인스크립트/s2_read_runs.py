"""N055 2단계: holiday-reply 실험의 항목별 답과 심사 판정·판단 이유를 읽는다(읽기 전용).
사용: python s2_read_runs.py <Experiments 화면의 실험 이름 앞부분 또는 전체> ...   예) reply-v1-1 reply-v1-2
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


def reason_for(answer):
    for o in judge:
        if answer and answer in str(o.input):
            try:
                return json.loads(o.output).get("scoreExplanation", "")
            except Exception:
                return str(o.output)[:200]
    return ""


ds = {i.id: i for i in c.get_dataset("holiday-reply").items}
results = {}
for e in exps:
    out = {}
    items = c.api.experiments.list_items(from_start_time=since, experiment_id=e.id, fields="core,io,scores", limit=100).data
    for it in items:
        d = ds.get(it.experiment_item_id)
        hid = d.metadata["id"] if d else it.experiment_item_id
        sc = [s for s in (it.scores or []) if s.name == "holiday-reply-judge"]
        answer = it.output if isinstance(it.output, str) else json.dumps(it.output, ensure_ascii=False)
        out[hid] = {"kind": d.metadata["kind"] if d else "?", "message": d.input["message"] if d else "",
                    "cond": d.expected_output if d else "", "tool_result": d.input["tool_result"] if d else "",
                    "answer": answer, "verdict": sc[0].value if sc else None, "reason": reason_for(answer)}
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
        print(f"  [{n}] {mark} | 답: {r['answer'][:150]}")
        print(f"      이유: {r['reason'][:240]}")
print("=" * 78)
for n in names:
    v = [results[n][h]["verdict"] for h in ids]
    print(n, "통과", sum(1 for x in v if x is True), "/ 실패", sum(1 for x in v if x is False), "/ 점수 없음", sum(1 for x in v if x is None))
if len(names) == 2:
    diff = [h for h in ids if results[names[0]][h]["verdict"] != results[names[1]][h]["verdict"]]
    print("두 실행에서 판정이 다른 항목:", diff or "없음")

if os.environ.get("DUMP"):
    with open(os.environ["DUMP"], "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print("saved:", os.environ["DUMP"])
