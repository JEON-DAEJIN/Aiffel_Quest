"""N055 2단계: holiday-reply 데이터셋(data/eval/holiday_reply.jsonl)을 만든다.
'고정한 도구 결과'는 지어내지 않고 실제 get_holidays 도구(공개 API)에 기간을 넘겨 나온 문장을 그대로 쓴다.
평가 시각은 교안의 답 지시문과 같은 2026-11-02(월) 14:00 한국 시간이다. 사용: python s2_make_holiday_reply.py"""
import json
import os
import sys
from types import SimpleNamespace

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local", "LANGFUSE_TRACING_ENABLED": "false"})

from app import tools  # noqa: E402

CTX = SimpleNamespace(timezone="Asia/Seoul")


def tool(frm, to):
    r = tools.get_holidays({"from": frm, "to": to}, CTX)
    return r.summary


ONE_YEAR = tool("2026-11-02", "2027-11-02")      # 인자를 비웠을 때 도구가 보는 1년(서비스에서 실제로 나오는 모양)
NONE_NOV = tool("2026-11-02", "2026-11-30")
DEC = tool("2026-12-01", "2026-12-31")
REST_YEAR = tool("2026-11-02", "2026-12-31")
THIS_WEEK = tool("2026-11-02", "2026-11-08")
MAR_2027 = tool("2027-03-01", "2027-03-31")
TOMORROW = tool("2026-11-03", "2026-11-03")

# (id, 메시지, 도구 결과, 통과 조건, failure|normal, 어디서 왔나)
ITEMS = [
    ("HR01", "다음 공휴일 언제야?", NONE_NOV, "결과에 없는 날짜를 공휴일이라고 말하지 않는다", "failure", "교안 4개 중 1"),
    ("HR02", "12월에 연휴 있어?", DEC, "12월 25일(금)이 토요일, 일요일과 이어져 25일부터 27일까지 쉰다고 말한다", "failure", "교안 4개 중 2"),
    ("HR03", "올해 남은 빨간 날 알려 줘", REST_YEAR, "크리스마스 하나만 말한다", "normal", "교안 4개 중 3"),
    ("HR04", "이번 주에 쉬는 날 있어?", THIS_WEEK, "이번 주에는 공휴일이 없다고 말한다", "normal", "교안 4개 중 4"),
    ("HR05", "12월에 연휴 있어?", ONE_YEAR, "12월 25일(금)이 토요일, 일요일과 이어져 25일부터 27일까지 쉰다고 말한다", "failure", "1단계 관찰: 인자를 비워 1년 조회한 결과로 3번 중 2번 틀림"),
    ("HR06", "올해 남은 빨간 날 알려 줘", ONE_YEAR, "올해(2026년) 안의 공휴일인 크리스마스만 말하고, 내년 날짜(1월 1일 새해 등)는 말하지 않는다", "failure", "1단계 관찰: 새해를 덧붙임 1/1"),
    ("HR07", "다음 공휴일 언제야?", ONE_YEAR, "12월 25일(금) 크리스마스를 다음 공휴일로 말한다", "normal", "1단계 관찰: 11번 모두 통과"),
    ("HR08", "3월에 쉬는 날 있어?", MAR_2027, "3월 1일(월) 3·1절이 앞의 토요일, 일요일과 이어져 사흘(2월 27일~3월 1일)을 쉰다고 말한다", "failure", "월요일 공휴일 경계(교안 더 해보기 3)"),
    ("HR09", "이번 달에 남은 공휴일 있어?", NONE_NOV, "이번 달에는 남은 공휴일이 없다고 말하고, 도구 결과에 없는 날짜(12월 25일 등)를 말하지 않는다", "failure", "도구가 '없다'고 한 뒤 다음 날짜를 지어내는 경우(교안 심사 예시 3)"),
    ("HR10", "다음 달에 공휴일 있어?", DEC, "다음 달(12월)의 공휴일로 12월 25일(금) 크리스마스를 말한다", "normal", "정상 사례"),
    ("HR11", "내일 공휴일이야?", TOMORROW, "내일은 공휴일이 아니라고 말한다", "normal", "정상 사례"),
]

out = os.path.join(REPO, "data", "eval", "holiday_reply.jsonl")
with open(out, "w", encoding="utf-8", newline="\n") as f:
    for id_, msg, result, cond, kind, source in ITEMS:
        f.write(json.dumps({"id": id_, "message": msg, "tool_result": result, "pass_condition": cond,
                            "kind": kind, "source": source}, ensure_ascii=False) + "\n")
print("wrote", len(ITEMS), "items:", sum(1 for i in ITEMS if i[4] == "failure"), "failure /", sum(1 for i in ITEMS if i[4] == "normal"), "normal")
for id_, msg, result, *_ in ITEMS:
    print(id_, "|", msg, "|", result[:150])
