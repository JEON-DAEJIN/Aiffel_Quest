"""N056 6장 보충: 우리 서버의 승인 코드(app.payments.confirm_payment)가 토스 승인 API와 실제로 통신하는지 본다.
존재하지 않는 paymentKey 로 승인을 요청한다 — 돈·카드·개인정보는 쓰지 않는다. 결제가 없으니 승인될 수 없다.
- 인증(시크릿 키 + 콜론 Basic 헤더)이 맞으면: 토스가 '결제 없음' 류의 오류 코드를 돌려준다
- 인증이 틀리면: UNAUTHORIZED_KEY 류의 오류 코드를 돌려준다
비교용으로 일부러 콜론을 뺀 헤더도 한 번 보낸다(LLM Quick Reference '자주 틀리는 패턴' 1번). 키 값은 출력하지 않는다."""
import base64
import os
import sys

import httpx

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO); os.chdir(REPO)
from app import payments  # noqa: E402
from app.config import load_settings  # noqa: E402

s = load_settings()
fake = {"payment_key": "tviva_n056_probe_not_a_real_payment", "order_id": "ord_n056probe000000", "amount": 1000}

try:
    payments.confirm_payment(s.toss_secret_key, fake["payment_key"], fake["order_id"], fake["amount"])
    print("① 우리 코드(콜론 있음): 예상 밖으로 승인됨")
except payments.TossError as e:
    print(f"① 우리 코드(콜론 있음): HTTP {e.status} · {e.code} · {e.message}")

wrong = "Basic " + base64.b64encode(s.toss_secret_key.encode()).decode()   # 콜론 없음(틀린 방식)
r = httpx.post(payments.CONFIRM_URL, timeout=15, headers={"Authorization": wrong, "Content-Type": "application/json"},
               json={"paymentKey": fake["payment_key"], "orderId": fake["order_id"], "amount": fake["amount"]})
body = r.json()
print(f"② 비교 — 콜론을 뺀 헤더: HTTP {r.status_code} · {body.get('code')} · {body.get('message')}")
