"""N056 4장 확인 1번: 0002_credits.sql 이 시험용 Supabase 에 적용됐는지, 권한이 의도대로인지 본다.
- 서버 열쇠(secret key)로 credit_balance RPC 와 credit_ledger 조회가 되는가
- 브라우저 열쇠(publishable key)로는 spend_credit RPC 가 막히고, credit_ledger 조회는 RLS 때문에 빈 목록인가
키 값·사용자 ID 원문은 출력하지 않는다. 데이터는 바꾸지 않는다(없는 사용자 ID로 잔액만 조회)."""
import os
import sys

import httpx

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO); os.chdir(REPO)
from app.config import load_settings  # noqa: E402

s = load_settings()
base = f"{s.supabase_url}/rest/v1"
nobody = "00000000-0000-0000-0000-000000000000"   # 없는 사용자. 잔액 0이 나와야 한다

server = httpx.Client(base_url=base, timeout=10, headers={"apikey": s.supabase_secret_key})
browser = httpx.Client(base_url=base, timeout=10, headers={"apikey": s.supabase_publishable_key})

r = server.post("/rpc/credit_balance", json={"p_user": nobody})
print("① 서버 열쇠 credit_balance:", r.status_code, r.text[:60])
r = server.get("/credit_ledger", params={"select": "id", "limit": 1})
print("② 서버 열쇠 credit_ledger 조회:", r.status_code, "(행", len(r.json()) if r.status_code == 200 else "-", ")")
r = browser.post("/rpc/spend_credit", json={"p_user": nobody, "p_amount": 1, "p_reason": "chat", "p_ref": "chat:probe", "p_free": 0})
print("③ 브라우저 열쇠 spend_credit:", r.status_code, r.json().get("code") if r.headers.get("content-type", "").startswith("application/json") else r.text[:60])
r = browser.post("/rpc/credit_balance", json={"p_user": nobody})
print("④ 브라우저 열쇠 credit_balance:", r.status_code, r.json().get("code") if r.headers.get("content-type", "").startswith("application/json") and isinstance(r.json(), dict) else r.text[:60])
r = browser.get("/credit_ledger", params={"select": "id", "limit": 1})
print("⑤ 브라우저 열쇠 credit_ledger 조회:", r.status_code, r.text[:60])
