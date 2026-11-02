"""staging 환경 트레이스를 읽기 전용으로 요약한다: 리비전(Version)별 개수, 단계별 시간, 토큰, 비용. 원문은 출력하지 않는다."""
import os
import sys
from collections import Counter, defaultdict
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
rows = []
cursor = None
while True:
    res = client.api.observations.get_many(from_start_time=since, limit=200, cursor=cursor, environment="staging",
                                           fields="core,basic,time,usage,cost")
    rows += res.data
    cursor = getattr(getattr(res, "meta", None), "cursor", None)
    if not cursor:
        break
print("staging 관찰 단위:", len(rows))
by = defaultdict(list)
for o in rows:
    by[o.trace_id].append(o)
print("버전(리비전)별 트레이스 수:", dict(Counter(next(iter(o.version for o in obs if o.version), "(없음)") for obs in by.values())))
print("사용자 수:", len({o.user_id for o in rows if o.user_id}), "| 세션 수:", len({o.session_id for o in rows if o.session_id}))


def sec(a, b):
    return (b - a).total_seconds()


print()
print("시각     버전                              총시간  앞구간(load) choose  tool  reply  첫글자까지  save  memory | 도구 | reply 토큰 | 비용$")
for tid, obs in sorted(by.items(), key=lambda kv: min(o.start_time for o in kv[1])):
    root = next((o for o in obs if o.name == "chat-turn"), None)
    if not root:
        continue
    st = {o.name: o for o in obs if o is not root}
    gens = [o for o in obs if o.type == "GENERATION"]
    reply = st.get("reply")
    if not reply:
        continue
    ttft = getattr(reply, "time_to_first_token", 0) or 0
    tools = ",".join(sorted(n for n in st if n.startswith("tool:"))) or "-"
    cost = sum((getattr(g, "total_cost", None) or 0) for g in gens)
    f = lambda n: sec(st[n].start_time, st[n].end_time) if n in st and st[n].end_time else float("nan")
    print(f"{str(root.start_time)[11:19]}  {root.version or '(없음)':34s} {sec(root.start_time, root.end_time):5.2f}  {f('load-context'):5.2f}      {f('choose-tools'):5.2f} {sum(f(n) for n in st if n.startswith('tool:')):5.2f}  {f('reply'):5.2f}  {sec(root.start_time, reply.start_time) + ttft:6.2f}     {f('save-turn'):5.2f}  {f('memory-update'):5.2f} | {tools} | {(reply.usage_details or {}).get('input')}/{(reply.usage_details or {}).get('output')} | {cost:.6f}")
