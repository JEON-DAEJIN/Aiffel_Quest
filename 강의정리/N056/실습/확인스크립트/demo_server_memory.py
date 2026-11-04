"""N056 4장 화면 확인용 임시 서버. 실제 LLM·Supabase를 쓰지 않는다(비용 0, 외부 DB 변경 없음).
가짜 LLM + 메모리 저장소 + 로그인 없음 + 가입 무료 크레딧 3개로 띄워, 크레딧 표시·차감·402 거절 화면을 본다.
.env 는 읽기 전에 아래 값을 먼저 정해 두므로(앱의 load_dotenv 는 이미 있는 값을 덮지 않는다) 키가 쓰이지 않는다."""
import os
import sys

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
os.environ.update({"LLM_PROVIDER": "fake", "LLM_API_KEY": "", "STORAGE": "memory", "AUTH": "none",
                   "ENV": "local", "FREE_CREDITS": "3", "LANGFUSE_TRACING_ENABLED": "false"})
os.chdir(REPO)
sys.path.insert(0, REPO)

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=8790)
