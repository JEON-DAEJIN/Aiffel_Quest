"""7장 설계 확인용 일회용 시험: propagate_attributes 안에서 루트만 만들고 자식은 밖에서 만들 때,
자식 관찰 단위에도 user_id·session_id·environment·version·tags 가 붙는가?  (A: 루트만 안에서, B: 자식도 안에서)"""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none"})
from langfuse import propagate_attributes  # noqa: E402

from app import observe  # noqa: E402
from app.config import load_settings  # noqa: E402

load_settings()
client = observe.get_client()
since = datetime.now(timezone.utc) - timedelta(seconds=3)
attrs = dict(user_id="spike-user", session_id="spike-user:2026-11-02", environment="spike", version="v-spike", tags=["spike-tag"],
             metadata={"commit": "abc123"})

with propagate_attributes(**attrs):
    rootA = client.start_observation(name="spikeA-root", as_type="span")
childA = rootA.start_observation(name="spikeA-child-outside", as_type="generation", model="fake")
childA.end()
rootA.end()

rootB = None
with propagate_attributes(**attrs):
    rootB = client.start_observation(name="spikeB-root", as_type="span")
    childB = rootB.start_observation(name="spikeB-child-inside", as_type="span")
    childB.end()
rootB.end()
client.flush()
time.sleep(12)
res = client.api.observations.get_many(from_start_time=since, limit=50, fields="core,basic,time,usage")
for o in sorted(res.data, key=lambda o: str(o.start_time)):
    if o.name.startswith("spike"):
        print(o.name, "| user:", getattr(o, "user_id", None), "| session:", getattr(o, "session_id", None), "| env:", getattr(o, "environment", None),
              "| version:", getattr(o, "version", None), "| tags:", getattr(o, "tags", None), "| trace:", o.trace_id[:6])
