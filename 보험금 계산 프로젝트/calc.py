# -*- coding: utf-8 -*-
"""세대별 실손보험 예상 수령액 계산 엔진 (SPEC.md 로직 구현).

입력(영수증 금액)을 받아 1/2-1/2-2/3/4세대 각각의 예상 수령액을 계산한다.
모든 세대 규칙은 rules.py의 표준(디폴트) 테이블을 사용하며, 실제 지급액은
가입 상품·약관에 따라 다를 수 있는 추정치다.
"""

from rules import (
    GENERATIONS,
    OUTPATIENT_VISIT_CAP,
    RIDER_COPAY_MIN,
    RIDER_COPAY_RATE,
    RIDER_LIMITS,
    GenerationRule,
)

RIDER_NAMES = ("도수", "주사", "MRI")


def _calc_rider(name: str, amount: float) -> dict:
    deduct = max(amount * RIDER_COPAY_RATE, RIDER_COPAY_MIN)
    pay = max(0.0, amount - deduct)
    cap = RIDER_LIMITS[name]["annual_cap"]
    pay = min(pay, cap)  # v1: 1회 영수증이지만 단건이 연한도를 넘는 경우 대비
    return {"input": amount, "deduct": round(deduct), "pay": round(pay)}


def _deduct_with_floor(amount: float, rate: float, floor: int) -> tuple[float, float]:
    """자기부담율 적용액과 정액공제 중 큰 값을 공제. (지급액, 공제액) 반환."""
    if amount <= 0:
        return 0.0, 0.0
    deduct = max(amount * rate, floor)
    pay = max(0.0, amount - deduct)
    return pay, min(deduct, amount)


def calculate_generation(
    gen: GenerationRule,
    care_type: str,
    hospital_type: str,
    paid_copay: float,
    nonpaid: float,
    riders: dict[str, float] | None = None,
) -> dict:
    """단일 세대에 대해 예상 수령액을 계산한다.

    care_type: "입원" | "통원" | "처방조제"
    hospital_type: "의원" | "병원" | "상급종합" (통원일 때만 사용)
    """
    riders = {k: v for k, v in (riders or {}).items() if v and v > 0}

    rider_results: dict[str, dict] = {}
    effective_nonpaid = nonpaid
    if gen.has_riders:
        for name, amt in riders.items():
            rider_results[name] = _calc_rider(name, amt)
    else:
        # 특약 개념이 없는 세대는 특약 대상 금액도 일반 비급여로 통합 계산
        effective_nonpaid += sum(riders.values())

    paid_pay = 0.0
    nonpaid_pay = 0.0
    paid_deduct = 0.0
    nonpaid_deduct = 0.0
    capped = False

    if care_type == "입원":
        paid_pay = paid_copay * (1 - gen.paid_copay_rate)
        nonpaid_pay = effective_nonpaid * (1 - gen.nonpaid_copay_rate)
        paid_deduct = paid_copay - paid_pay
        nonpaid_deduct = effective_nonpaid - nonpaid_pay
    else:
        if care_type == "통원":
            paid_floor = gen.outpatient_deductible[hospital_type]
            nonpaid_table = gen.nonpaid_outpatient_deductible or gen.outpatient_deductible
            nonpaid_floor = nonpaid_table[hospital_type]
        else:  # 처방조제
            paid_floor = gen.prescription_deductible
            nonpaid_floor = gen.prescription_deductible

        paid_pay, paid_deduct = _deduct_with_floor(paid_copay, gen.paid_copay_rate, paid_floor)
        nonpaid_pay, nonpaid_deduct = _deduct_with_floor(
            effective_nonpaid, gen.nonpaid_copay_rate, nonpaid_floor
        )

        outpatient_total = paid_pay + nonpaid_pay
        if outpatient_total > OUTPATIENT_VISIT_CAP:
            scale = OUTPATIENT_VISIT_CAP / outpatient_total
            paid_pay *= scale
            nonpaid_pay *= scale
            capped = True

    rider_pay_total = sum(r["pay"] for r in rider_results.values())
    total_pay = round(paid_pay) + round(nonpaid_pay) + round(rider_pay_total)
    total_claim = paid_copay + nonpaid + sum(riders.values())
    total_deduct = max(0, round(total_claim) - total_pay)

    return {
        "generation": gen.code,
        "label": gen.label,
        "period": gen.period,
        "claim_total": round(total_claim),
        "paid_pay": round(paid_pay),
        "nonpaid_pay": round(nonpaid_pay),
        "rider_pay": round(rider_pay_total),
        "rider_detail": rider_results,
        "deduct_total": total_deduct,
        "expected_payout": total_pay,
        "outpatient_capped": capped,
    }


def calculate_all(
    care_type: str,
    hospital_type: str,
    paid_copay: float,
    nonpaid: float,
    riders: dict[str, float] | None = None,
) -> list[dict]:
    """모든 세대(1~4)에 대해 계산 결과를 리스트로 반환한다."""
    return [
        calculate_generation(gen, care_type, hospital_type, paid_copay, nonpaid, riders)
        for gen in GENERATIONS
    ]
