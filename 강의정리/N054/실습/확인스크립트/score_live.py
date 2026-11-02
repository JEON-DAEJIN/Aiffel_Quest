"""실제 LLM·실제 Langfuse 로 한 턴 → 좋아요/별로예요/신고 → 점수가 그 트레이스에 붙는지 확인한다. 로컬 메모리 저장소(AUTH 없음)."""
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
r = client.post("/api/chat", json={"message": "오늘 좀 지쳤어"})
events = [json.loads(line) for line in r.text.splitlines()]
mid = next(e for e in events if e["type"] == "done")["message_id"]
trace_id = store.get_message("local-user", mid)["meta"].get("trace_id")
print("답 메시지:", mid, "| 저장된 트레이스 ID 있음:", bool(trace_id))
print("별로예요:", client.post("/api/feedback", json={"message_id": mid, "value": "dislike"}).json())
print("신고(사유에 전화번호):", client.post("/api/report", json={"message_id": mid, "reason": "부적절해요 연락처 010-1234-5678"}).json())
other = store.add_message("someone-else", "assistant", "남의 답", {"trace_id": "x"})
print("남의 메시지에 반응:", client.post("/api/feedback", json={"message_id": other["id"], "value": "like"}).status_code)
lf = observe.get_client()
time.sleep(25)
res = lf.api.scores.get_many(trace_id=trace_id, limit=20)
for s in res.data:
    print(" 점수:", s.name, "| 값:", getattr(s, "value", None), "| 종류:", getattr(s, "data_type", None), "| 코멘트:", getattr(s, "comment", None))
print("점수 개수:", len(res.data))
