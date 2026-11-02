"""한 트레이스의 관찰 단위별 시작 시각·걸린 시간을 읽기 전용으로 출력한다(원문 출력 없음)."""
import os
import sys

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none"})

from app import observe  # noqa: E402
from app.config import load_settings  # noqa: E402

load_settings()
client = observe.get_client()
trace_id = sys.argv[1]
res = client.api.observations.get_many(trace_id=trace_id, limit=50, fields="core,basic,time,usage")
rows = sorted(res.data, key=lambda o: str(o.start_time))
t0 = rows[0].start_time
for o in rows:
    start = (o.start_time - t0).total_seconds()
    end = (o.end_time - t0).total_seconds() if o.end_time else None
    print(f"{o.name:18s} 시작 +{start:5.2f}s  끝 +{(end if end is not None else float('nan')):5.2f}s  걸린 {((end - start) if end is not None else float('nan')):5.2f}s  level={o.level}")
