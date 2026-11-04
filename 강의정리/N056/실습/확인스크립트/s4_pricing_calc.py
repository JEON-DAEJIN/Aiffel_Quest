"""N056 3장 손익 계산기(학습서의 웹 계산기는 PDF에 없어 같은 식을 코드로 둔다).
강의노트 3-8의 [보충 검산] 식과 같다:
  크레딧 1개 마진 = 가격 − 원가 − 가격 × 수수료
  유료 사용자 몫 = (하루 메시지 − 하루 무료) × 30 × 유료 사용자 수 × 마진 − 유료 사용자의 무료분 원가
  무료 사용자 원가 = 무료 사용자 수 × 하루 무료 × 30 × 원가   (무료 사용자는 한도까지 다 쓴다고 가정)
  한 달 손익 = 유료 사용자 몫 − 무료 사용자 원가 − 고정비
교안 기본값(원가 1.5원)으로 교안 문장을 재현하는지 먼저 보고, 내 서비스 원가(Langfuse 실측)로 다시 돌린다.
결과는 s4_pricing_calc.json."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
RATE = 1400  # 원/달러, 사용자 결정(2026-11-04) — 임시 가정


def pnl(cost, users=1000, per_day=20, free=10, conv=0.05, price=10, fee=0.0374, fixed=75000):
    paid = users * conv
    unpaid = users - paid
    margin = price - cost - price * fee
    bought = max(per_day - free, 0) * 30 * paid
    paid_share = bought * margin - paid * free * 30 * cost
    free_cost = unpaid * free * 30 * cost
    return {"margin_per_credit": round(margin, 3), "credits_sold": bought, "paid_share": round(paid_share),
            "free_cost": round(free_cost), "fixed": fixed, "pnl": round(paid_share - free_cost - fixed)}


def breakeven_free(cost, **kw):
    lo, hi = 0.0, 20.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if pnl(cost, free=mid, **kw)["pnl"] > 0:
            lo = mid
        else:
            hi = mid
    return round(lo, 2)


out = {}
cases = {
    "교안 기본값(원가 1.5원)": 1.5,
    "내 서비스 상위10%(0.000519달러)": 0.000519 * RATE,
    "내 서비스 gpt-4o 평균(0.007355달러)": 0.007355 * RATE,
}
for name, cost in cases.items():
    rows = {
        "기본(무료 10·10원)": pnl(cost),
        "가격 2배(20원)": pnl(cost, price=20),
        "무료 3개": pnl(cost, free=3),
        "무료 5개": pnl(cost, free=5),
        "무료 0개": pnl(cost, free=0),
    }
    be = breakeven_free(cost)
    out[name] = {"cost_won": round(cost, 3), "rows": rows, "breakeven_free_per_day": be}
    print(f"\n[{name}] 메시지 원가 {cost:.2f}원 · 손익 0이 되는 하루 무료 한도 ≈ {be}개")
    for k, r in rows.items():
        print(f"  {k:<14} 크레딧 1개 마진 {r['margin_per_credit']:>7}원 · 유료 몫 {r['paid_share']:>9,}원 · "
              f"무료 원가 {r['free_cost']:>8,}원 · 손익 {r['pnl']:>9,}원")
json.dump(out, open(os.path.join(HERE, "s4_pricing_calc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
