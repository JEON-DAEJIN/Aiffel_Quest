"""N056 4장 확인 3~5번용 로컬 서버. 저장소의 .env 설정 그대로(시험용 Supabase·익명 로그인·실제 LLM)로 띄운다.
.env 는 앱이 읽는다(이 스크립트는 값을 보지 않는다). 포트 8791."""
import os
import sys

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
os.chdir(REPO)
sys.path.insert(0, REPO)

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=8791)
