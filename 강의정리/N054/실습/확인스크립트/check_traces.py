"""최근 트레이스를 읽기 전용으로 조회해 이름·개수·토큰만 출력한다(원문은 출력하지 않는다)."""
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none"})

from app import observe  # noqa: E402
from app.config import load_settings  # noqa: E402

load_settings()
client = observe.get_client()
minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 60
since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
res = client.api.observations.get_many(from_start_time=since, limit=200, fields="core,basic,time,usage")
rows = sorted(res.data, key=lambda o: str(o.start_time))
print("관찰 단위:", len(rows), "/ 이름별:", dict(Counter(o.name for o in rows)))
roots = [o for o in rows if not getattr(o, "parent_observation_id", None)]
print("트레이스(루트):", [(o.name, str(o.start_time)[11:19]) for o in roots])
by_trace = {}
for o in rows:
    by_trace.setdefault(o.trace_id, []).append(o)
for tid, obs in by_trace.items():
    root = next((o for o in obs if not getattr(o, "parent_observation_id", None)), None)
    gens = [(o.name, (getattr(o, "usage_details", None) or {}).get("input"), (getattr(o, "usage_details", None) or {}).get("output")) for o in obs if o.type == "GENERATION"]
    print(" -", root.name if root else "?", str(root.start_time)[11:19] if root else "", "|", "단계:", [o.name for o in obs if o is not root], "|", "generation 토큰:", gens)
