"""7장 속성이 실제 Langfuse 에서 모든 관찰 단위에 붙는지 한 턴으로 확인한다(도구를 쓰는 질문)."""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none"})

from app import agent, observe  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.llm import make_llm  # noqa: E402
from app.store.memory_store import MemoryStore  # noqa: E402

settings = load_settings()
llm = make_llm(settings)
since = datetime.now(timezone.utc) - timedelta(seconds=3)
events = list(agent.run_turn("다음 공휴일이 언제야?", "attrs-check-user", llm, MemoryStore(), False))
print("events:", events[-1]["type"])
client = observe.get_client()
client.flush()
time.sleep(12)
res = client.api.observations.get_many(from_start_time=since, limit=50, fields="core,basic,time,usage,metadata")
rows = sorted(res.data, key=lambda o: str(o.start_time))
tag_attrs = [n for n in dir(rows[0]) if "tag" in n.lower()] if rows else []
print("태그 관련 필드 이름:", tag_attrs)
for o in rows:
    tags = getattr(o, "trace_tags", None) or getattr(o, "tags", None)
    print(f"{o.name:18s} user={getattr(o, 'user_id', None)} session={getattr(o, 'session_id', None)} env={getattr(o, 'environment', None)} version={getattr(o, 'version', None)} tags={tags} md={getattr(o, 'metadata', None) if o.name == 'chat-turn' else ''}")
