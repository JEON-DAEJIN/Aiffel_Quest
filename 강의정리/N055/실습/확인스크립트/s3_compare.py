"""N055 3단계: s3_runs_dump.json(scripts/run_tool_experiment.py --dump)의 6회 실험을 항목별로 나란히 놓는다(읽기 전용).
O=도구와 인자 모두 정답, t=도구만 맞고 인자가 틀림, X=도구가 틀림. 버전마다 두 회차를 'v1:OO'처럼 붙여 쓴다."""
import json, sys
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "s3_runs_dump.json", encoding="utf-8"))
runs = sorted(d)
vers = sorted({r.split("-")[1] for r in runs})
ids = sorted(next(iter(d.values())), key=lambda x: int(x[1:]))
def mark(v):
    return "O" if v["exact"] == 1 else ("t" if v["tools_right"] == 1 else "X")
def cell(ver, i):
    return "".join(mark(d[r][i]) for r in runs if r.split("-")[1] == ver)
print("항목  " + "  ".join(f"{v:>6}" for v in vers))
rows = []
for i in ids:
    cs = [cell(v, i) for v in vers]
    if any(c != "OO" for c in cs):
        print(f"{i:<5} " + "  ".join(f"{c:>6}" for c in cs))
        rows.append(i)
print("\n(표시 안 된 항목은 6번 모두 O)", len(ids) - len(rows), "개")
print("\n버전별 합계(항목×회차)")
for v in vers:
    rs = [r for r in runs if r.split("-")[1] == v]
    for r in rs:
        print(f"  {r}: 도구 {sum(1 for i in ids if d[r][i]['tools_right']==1)}/41, 모두 {sum(1 for i in ids if d[r][i]['exact']==1)}/41")
print("\n틀린 이유(예시: 각 항목의 첫 틀린 실행)")
for i in rows:
    for r in runs:
        v = d[r][i]
        if v["exact"] != 1:
            picked = ",".join(t["name"] for t in v["output"]["tools"]) or "도구 없음"
            print(f"  {i} {r}: 고른 도구 {picked} | {'; '.join(c for c in v['comments'] if not c.startswith('고른 도구'))[:150]}")
            break
