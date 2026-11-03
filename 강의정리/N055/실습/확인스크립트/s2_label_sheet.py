"""N055 2단계: 사람이 먼저 통과/실패를 붙일 '판정표'를 만든다. 심사 결과(판정·이유)는 넣지 않고,
항목과 실행 이름을 섞어 어느 실행인지·몇 번째 항목인지 모르게 한다(심사 결과를 먼저 보면 사람의 판단이 끌려간다).
사용: python s2_label_sheet.py <read_runs 덤프 json> <판정표 md 출력> <대응표 json 출력>"""
import json
import random
import sys

src, sheet, mapping = sys.argv[1:4]
data = json.load(open(src, encoding="utf-8"))
rows = [(run, hid, r) for run, items in data.items() for hid, r in items.items()]
random.Random(1103).shuffle(rows)
lines = ["# 사람 판정표 (N055 holiday-reply 답 22개)", "",
         "> 항목마다 **통과 조건**을 읽고 서비스의 답이 그 조건을 지켰으면 `O`, 어겼으면 `X`로 적어 주세요.",
         "> 말투·길이·이모지는 보지 않고 **통과 조건 하나만** 봅니다. 애매하면 `?`로 적고 이유를 한 줄 적어 주세요.",
         "> Langfuse의 Compare 화면이나 심사 결과(true/false)는 **보지 않은 상태**에서 판정해 주세요(결과를 먼저 보면 판단이 끌려갑니다).", ""]
key = {}
for n, (run, hid, r) in enumerate(rows, 1):
    key[f"{n:02d}"] = {"run": run, "item": hid, "judge": r["verdict"], "reason": r["reason"], "kind": r["kind"]}
    lines += [f"## {n:02d}. {r['message']}", "",
              f"- 도구 결과: {r['tool_result']}",
              f"- 서비스의 답: {r['answer']}",
              f"- **통과 조건**: {r['cond']}", "- 내 판정: `   `", ""]
open(sheet, "w", encoding="utf-8").write("\n".join(lines))
json.dump(key, open(mapping, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("판정표", len(rows), "개 →", sheet)
