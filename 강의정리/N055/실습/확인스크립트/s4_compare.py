"""N055 4단계: choose() 전체 경로 실험(전/후)의 틀린 항목과 안전장치 기록을 읽는다(읽기 전용). 사용: python s4_compare.py 파일.json [파일2.json ...]"""
import json, sys
for path in sys.argv[1:]:
    d = json.load(open(path, encoding="utf-8"))
    print("=====", path)
    for run in sorted(d):
        rows = d[run]
        bad = {i: v for i, v in rows.items() if v["exact"] != 1}
        print(f"{run}: 모두 정답 {sum(1 for v in rows.values() if v['exact']==1)}/{len(rows)} | 틀린 항목:", ", ".join(sorted(bad, key=lambda x: int(x[1:]))))
    for run in sorted(d):
        for i in sorted(d[run], key=lambda x: int(x[1:])):
            v = d[run][i]
            if i in ("T30","T31","T32","T33","T34","T35","T40") or v["guards"]:
                out = v["output"]["tools"]
                due = [t["args"].get("due_at") for t in out if t["name"] == "create_reminder"]
                if v["guards"] or i == "T34":
                    print(f"  {run} {i}: due_at {due} | 안전장치 {[g[:60] for g in v['guards']]}")
