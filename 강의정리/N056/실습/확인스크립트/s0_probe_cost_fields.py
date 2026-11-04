"""N056 2장 준비: 최근 Langfuse generation 하나의 비용·토큰 필드 이름과 값이 채워져 있는지만 본다.
키·입력·출력 원문은 출력하지 않는다."""
import os, sys
from datetime import datetime, timedelta, timezone
REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO); os.chdir(REPO)
from app import observe  # noqa: E402
from app.config import load_settings  # noqa: E402
load_settings()
c = observe.get_client()
since = datetime.now(timezone.utc) - timedelta(days=7)
res = c.api.observations.get_many(from_start_time=since, type="GENERATION", limit=5, fields="core,basic,model,usage,metrics")
print("generations(최대 5):", len(res.data))
for o in res.data[:2]:
    d = o.dict() if hasattr(o, "dict") else vars(o)
    keep = {k: v for k, v in d.items() if k not in ("input", "output", "metadata", "projectId") and v not in (None, {}, [])}
    print({k: (str(v)[:80]) for k, v in keep.items()})
