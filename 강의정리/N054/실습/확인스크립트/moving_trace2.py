"""이사 이야기 트레이스를 읽기 전용으로 거슬러 읽는다: 속성, 도구 선택, 도구 결과, 기억 정리 출력, 마지막 질문의 기억 메모."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.update({"STORAGE": "memory", "AUTH": "none"})

from app import observe  # noqa: E402
from app.config import load_settings  # noqa: E402

load_settings()
client = observe.get_client()
since = datetime.now(timezone.utc) - timedelta(minutes=int(sys.argv[1]) if len(sys.argv) > 1 else 20)
res = client.api.observations.get_many(from_start_time=since, limit=300, fields="core,basic,time,io,usage,metadata")
rows = sorted(res.data, key=lambda o: str(o.start_time))
by = {}
for o in rows:
    by.setdefault(o.trace_id, []).append(o)


def text(x):
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)


for tid, obs in by.items():
    root = next((o for o in obs if o.name == "chat-turn"), None)
    if not root or "user" not in dir(root):
        pass
    if not root or not str(root.start_time) > str(since)[:19]:
        continue
    q = text(root.input)
    if not any(k in q for k in ("이사", "다음 주에 뭐", "점심", "돼지국밥", "라면", "토요일")):
        continue
    print("=" * 72)
    print("chat-turn", str(root.start_time)[11:19], "| 질문:", q[:40])
    print("  속성: user=", getattr(root, "user_id", None), "| session=", getattr(root, "session_id", None), "| env=", getattr(root, "environment", None), "| version=", getattr(root, "version", None))
    for o in obs:
        if o.name == "choose-tools":
            out = text(o.output)
            print("  choose-tools 출력:", out[:300])
        if o.name.startswith("tool:"):
            print("  ", o.name, "입력:", text(o.input)[:140], "| 출력:", text(o.output)[:140])
        if o.name == "memory-update":
            print("  memory-update 출력:", text(o.output)[:300])
        if o.name == "reply":
            s = text(o.input)
            try:
                msgs = json.loads(s)
                system = next(m["content"] for m in msgs if m["role"] == "system")
            except Exception:
                system = s
            for line in system.splitlines():
                if "이사" in line or "[기억" in line or "[도구 결과]" in line:
                    print("  reply 입력(시스템) 줄:", line.strip()[:150])
            try:
                hist = [m for m in msgs if m["role"] != "system"]
                print("  reply 입력: 대화 메시지", len(hist), "개 / 그중 '이사' 포함:", sum("이사" in m["content"] for m in hist), "/ '11월 7일' 포함:", sum("11월 7일" in m["content"] for m in hist))
                for m in hist:
                    if "11월 7일" in m["content"] and m["role"] == "assistant":
                        print("    앞선 내 답:", m["content"][:80])
            except Exception as e:
                print("   (대화 파싱 실패)", e)
            print("  reply 출력:", text(o.output)[:150])
