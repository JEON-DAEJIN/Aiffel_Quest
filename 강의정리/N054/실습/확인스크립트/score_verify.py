"""점수가 Langfuse 에서 읽히는지 사람 대신 확인한다: 별로예요(false)·신고(true)+코멘트가 그 트레이스에 붙고, 별로예요가 붙은 트레이스만 걸러지는지.
로컬 메모리 저장소(AUTH 없음)로 한 턴을 돌린다. 원문은 출력하지 않는다."""
import json
import os
import sys
import time

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local"})

from fastapi.testclient import TestClient  # noqa: E402

from app import observe  # noqa: E402
from app.main import app, store  # noqa: E402

client = TestClient(app)


def turn(message):
    events = [json.loads(line) for line in client.post("/api/chat", json={"message": message}).text.splitlines()]
    mid = next(e for e in events if e["type"] == "done")["message_id"]
    return mid, store.get_message("local-user", mid)["meta"]["trace_id"]


bad_mid, bad_trace = turn("오늘 좀 지쳤어")
good_mid, good_trace = turn("점심 뭐 먹을까?")
print("트레이스 A(별로예요+신고 예정):", bad_trace[:8], "| 트레이스 B(좋아요 예정):", good_trace[:8])
print(client.post("/api/feedback", json={"message_id": bad_mid, "value": "dislike"}).json())
print(client.post("/api/report", json={"message_id": bad_mid, "reason": "엉뚱한 답이에요 010-9999-8888 로 연락 주세요"}).json())
print(client.post("/api/feedback", json={"message_id": good_mid, "value": "like"}).json())
lf = observe.get_client()
time.sleep(30)

print("\n[1] 점수 종류별 조회")
res = lf.api.scores.get_many(from_timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc) - __import__("datetime").timedelta(minutes=5), limit=50)
for s in sorted(res.data, key=lambda s: s.name):
    d = s.model_dump() if hasattr(s, "model_dump") else s.__dict__
    print(f" - {s.name} | 값 {d.get('value')} | 종류 {d.get('data_type') or d.get('dataType')} | 환경 {d.get('environment')} | 트레이스 {(d.get('trace_id') or d.get('traceId') or '')[:8]} | 코멘트 {d.get('comment')!r}")
print("   (점수 객체 필드 이름:", sorted(k for k in d.keys())[:20], ")")

print("\n[2] 별로예요(user-feedback=false)가 붙은 트레이스만 걸러지는가 — 점수 이름·값으로 조회")
res2 = lf.api.scores.get_many(name="user-feedback", data_type="BOOLEAN", limit=50)
rows = [(s, (s.model_dump() if hasattr(s, 'model_dump') else s.__dict__)) for s in res2.data]
false_traces = {(d.get('trace_id') or d.get('traceId')) for s, d in rows if d.get('value') in (0, 0.0, False, "False", "false")}
true_traces = {(d.get('trace_id') or d.get('traceId')) for s, d in rows if d.get('value') in (1, 1.0, True, "True", "true")}
print(" false 트레이스 안에 A 있음:", bad_trace in false_traces, "| false 트레이스 안에 B 있음:", good_trace in false_traces)
print(" true 트레이스 안에 B 있음:", good_trace in true_traces)

print("\n[3] 그 트레이스가 실제로 있고 속성이 붙어 있는가")
obs = lf.api.observations.get_many(trace_id=bad_trace, limit=20, fields="core,basic")
print(" 관찰 단위", len(obs.data), "개, 환경", {o.environment for o in obs.data}, "| 사용자 있음:", all(bool(o.user_id) for o in obs.data))
