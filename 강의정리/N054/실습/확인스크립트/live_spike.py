"""실제 LLM·실제 Langfuse 로 한 턴을 돌려 보는 일회용 확인. 값(키·원문)은 출력하지 않고 이름·개수·토큰만 출력한다."""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none", "ENV": "local"})

from app import agent, observe  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402
from app.store.memory_store import MemoryStore  # noqa: E402

settings = load_settings()
print("provider:", settings.provider, "model:", settings.model)
llm = make_llm(settings)
store = MemoryStore()
since = datetime.now(timezone.utc) - timedelta(seconds=5)
message = sys.argv[1] if len(sys.argv) > 1 else "오늘 좀 지쳤어. 이사 준비 때문에 정신이 없네."
events = list(agent.run_turn(message, "spike-user", llm, store, False))
print("events:", len(events), "last:", events[-1]["type"])

client = observe.get_client()
print("tracing client:", "on" if client else "off")
if client:
    client.flush()
    time.sleep(12)
    try:
        res = client.api.observations.get_many(from_start_time=since, limit=50, fields="core,basic,time,io,usage")
        rows = sorted(res.data, key=lambda o: str(o.start_time))
        print("observations since run:", len(rows))
        for o in rows:
            usage = getattr(o, "usage_details", None) or getattr(o, "usage", None)
            print(" -", getattr(o, "type", None), getattr(o, "name", None), "| model:", getattr(o, "provided_model_name", None) or getattr(o, "model", None),
                  "| usage:", usage, "| level:", getattr(o, "level", None), "| ttft:", getattr(o, "time_to_first_token", None),
                  "| parent:", "root" if not getattr(o, "parent_observation_id", None) else "child")
    except Exception as error:
        print("api read failed:", type(error).__name__, str(error)[:200])
