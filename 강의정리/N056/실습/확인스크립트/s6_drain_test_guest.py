"""N056 4장 확인 5번: 시험용 Supabase의 테스트 게스트 한 명의 잔액을 0으로 만든다.
교안은 Table Editor에서 −줄을 직접 넣으라고 한다. 같은 일을 서버 열쇠로 한다 — 원장을 고치지 않고 adjust 줄을 하나 더 쌓는다.
사용: python s6_drain_test_guest.py <테스트 게스트 user_id>. 키 값은 출력하지 않고, user_id는 앞 8자만 출력한다."""
import os
import sys

REPO = r"C:\Users\ilove\Documents\friend-agent-practice\friend-agent"
sys.path.insert(0, REPO); os.chdir(REPO)
from app.config import load_settings  # noqa: E402
from app.store.supabase_store import SupabaseStore  # noqa: E402

uid = sys.argv[1]
s = load_settings()
assert s.storage == "supabase"
store = SupabaseStore(s.supabase_url, s.supabase_secret_key)
before = store.credit_balance(uid)
if before > 0:
    store.add_credit(uid, -before, "adjust", f"adjust:n056-drain:{uid}")
print("게스트", uid[:8], "| 잔액", before, "→", store.credit_balance(uid))
print("최근 원장:", [(e["reason"], e["delta"]) for e in store.credit_history(uid, 5)])
