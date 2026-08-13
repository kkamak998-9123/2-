# -*- coding: utf-8 -*-
"""실손의료보험 세대별 표준 규칙 테이블 (SPEC.md 기준, 2026-08 조사 반영).

보험사·상품별 편차가 있는 "표준(디폴트)" 값이며, 계산 결과는 항상 추정치임을
함께 표시한다(main.py/프론트에서 면책 문구 처리).
"""

from dataclasses import dataclass, field

# 통원 정액공제 병원 종별
HOSPITAL_TYPES = ["의원", "병원", "상급종합"]

# 특약 3종 공통 자기부담: max(30%, 2만원)
RIDER_COPAY_RATE = 0.30
RIDER_COPAY_MIN = 20_000

RIDER_LIMITS = {
    "도수": {"annual_cap": 3_500_000, "annual_count": 50},
    "주사": {"annual_cap": 2_500_000, "annual_count": 50},
    "MRI": {"annual_cap": 3_000_000, "annual_count": None},
}

OUTPATIENT_VISIT_CAP = 200_000  # 통원(외래+처방) 1회 지급 한도 — v1 단순화(SPEC 참고)


@dataclass(frozen=True)
class GenerationRule:
    code: str
    label: str
    period: str
    paid_copay_rate: float          # 급여 자기부담율
    nonpaid_copay_rate: float       # 비급여 자기부담율
    outpatient_deductible: dict     # {"의원": int, "병원": int, "상급종합": int} — 급여 기준
    nonpaid_outpatient_deductible: dict | None  # None이면 급여와 동일 정액공제 사용
    prescription_deductible: int    # 처방조제 정액공제
    has_riders: bool                # 3대 비급여 특약 분리 여부(3·4세대만 True)


GENERATIONS: list[GenerationRule] = [
    GenerationRule(
        code="gen1",
        label="1세대",
        period="~2009.9",
        paid_copay_rate=0.0,
        nonpaid_copay_rate=0.0,
        outpatient_deductible={"의원": 5_000, "병원": 5_000, "상급종합": 5_000},
        nonpaid_outpatient_deductible=None,
        prescription_deductible=0,
        has_riders=False,
    ),
    GenerationRule(
        code="gen2_1",
        label="2-1세대",
        period="2009.10~2015.8",
        paid_copay_rate=0.10,
        nonpaid_copay_rate=0.10,
        outpatient_deductible={"의원": 10_000, "병원": 15_000, "상급종합": 20_000},
        nonpaid_outpatient_deductible=None,
        prescription_deductible=8_000,
        has_riders=False,
    ),
    GenerationRule(
        code="gen2_2",
        label="2-2세대",
        period="2015.9~2017.3",
        paid_copay_rate=0.10,
        nonpaid_copay_rate=0.20,
        outpatient_deductible={"의원": 10_000, "병원": 15_000, "상급종합": 20_000},
        nonpaid_outpatient_deductible=None,
        prescription_deductible=8_000,
        has_riders=False,
    ),
    GenerationRule(
        code="gen3",
        label="3세대",
        period="2017.4~2021.6",
        paid_copay_rate=0.10,
        nonpaid_copay_rate=0.20,
        outpatient_deductible={"의원": 10_000, "병원": 15_000, "상급종합": 20_000},
        nonpaid_outpatient_deductible=None,
        prescription_deductible=8_000,
        has_riders=True,
    ),
    GenerationRule(
        code="gen4",
        label="4세대",
        period="2021.7~",
        paid_copay_rate=0.20,
        nonpaid_copay_rate=0.30,
        outpatient_deductible={"의원": 10_000, "병원": 15_000, "상급종합": 20_000},
        nonpaid_outpatient_deductible={"의원": 30_000, "병원": 30_000, "상급종합": 30_000},
        prescription_deductible=8_000,
        has_riders=True,
    ),
]

GENERATIONS_BY_CODE = {g.code: g for g in GENERATIONS}
