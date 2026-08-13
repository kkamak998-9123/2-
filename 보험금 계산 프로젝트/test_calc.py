# -*- coding: utf-8 -*-
"""calc.py 단위 테스트 (표준 라이브러리 unittest, 손계산 검산 포함)."""

import unittest

from calc import calculate_all, calculate_generation
from rules import GENERATIONS_BY_CODE


def gen_result(code, **kwargs):
    return calculate_generation(GENERATIONS_BY_CODE[code], **kwargs)


class TestOutpatientBasic(unittest.TestCase):
    """통원, 의원 아님(병원급 아님) 기본 케이스: 손계산과 대조."""

    def test_gen3_outpatient_clinic(self):
        # 급여 30,000 / 비급여 50,000, 의원, 3세대
        # 급여공제 = max(3000, 10000) = 10000 -> 지급 20000
        # 비급여공제 = max(10000, 10000) = 10000 -> 지급 40000
        r = gen_result(
            "gen3", care_type="통원", hospital_type="의원",
            paid_copay=30_000, nonpaid=50_000,
        )
        self.assertEqual(r["paid_pay"], 20_000)
        self.assertEqual(r["nonpaid_pay"], 40_000)
        self.assertEqual(r["expected_payout"], 60_000)
        self.assertFalse(r["outpatient_capped"])

    def test_gen4_outpatient_clinic_higher_copay(self):
        # 같은 입력, 4세대: 급여20%/비급여30%, 비급여 정액공제 3만
        # 급여공제 = max(6000, 10000)=10000 -> 지급 20000
        # 비급여공제 = max(15000, 30000)=30000 -> 지급 20000
        r = gen_result(
            "gen4", care_type="통원", hospital_type="의원",
            paid_copay=30_000, nonpaid=50_000,
        )
        self.assertEqual(r["paid_pay"], 20_000)
        self.assertEqual(r["nonpaid_pay"], 20_000)
        self.assertEqual(r["expected_payout"], 40_000)

    def test_gen1_most_generous(self):
        # 1세대: 자기부담 0%, 정액공제 5000원 고정
        # 급여: max(0,5000)=5000 -> 25000 / 비급여: max(0,5000)=5000 -> 45000
        r = gen_result(
            "gen1", care_type="통원", hospital_type="의원",
            paid_copay=30_000, nonpaid=50_000,
        )
        self.assertEqual(r["paid_pay"], 25_000)
        self.assertEqual(r["nonpaid_pay"], 45_000)
        self.assertEqual(r["expected_payout"], 70_000)

    def test_generation_ordering_generally_decreasing(self):
        """같은 입력에서 1세대가 가장 관대하고 4세대가 가장 적게 받는 일반적 경향."""
        results = calculate_all(
            care_type="통원", hospital_type="상급종합",
            paid_copay=100_000, nonpaid=200_000,
        )
        payouts = {r["generation"]: r["expected_payout"] for r in results}
        self.assertGreaterEqual(payouts["gen1"], payouts["gen2_1"])
        self.assertGreaterEqual(payouts["gen2_1"], payouts["gen2_2"])
        # gen2_2와 gen3는 규칙이 동일하므로 같아야 함
        self.assertEqual(payouts["gen2_2"], payouts["gen3"])


class TestHospitalTypeDeductible(unittest.TestCase):
    def test_higher_tier_hospital_higher_deductible(self):
        # 3세대, 급여 5만원(자기부담율 10%=5000원 < 모든 정액공제) -> 정액공제가 그대로 적용됨
        clinic = gen_result(
            "gen3", care_type="통원", hospital_type="의원",
            paid_copay=50_000, nonpaid=0,
        )
        hospital = gen_result(
            "gen3", care_type="통원", hospital_type="병원",
            paid_copay=50_000, nonpaid=0,
        )
        general = gen_result(
            "gen3", care_type="통원", hospital_type="상급종합",
            paid_copay=50_000, nonpaid=0,
        )
        self.assertEqual(clinic["paid_pay"], 40_000)    # 5만 - 1만
        self.assertEqual(hospital["paid_pay"], 35_000)  # 5만 - 1.5만
        self.assertEqual(general["paid_pay"], 30_000)   # 5만 - 2만


class TestHospitalization(unittest.TestCase):
    def test_hospitalization_no_flat_deductible(self):
        # 입원은 정액공제 없이 자기부담율만 적용
        r = gen_result(
            "gen4", care_type="입원", hospital_type="상급종합",
            paid_copay=1_000_000, nonpaid=500_000,
        )
        self.assertEqual(r["paid_pay"], 800_000)   # 100만 * (1-0.2)
        self.assertEqual(r["nonpaid_pay"], 350_000)  # 50만 * (1-0.3)
        self.assertEqual(r["expected_payout"], 1_150_000)
        self.assertFalse(r["outpatient_capped"])


class TestRiders(unittest.TestCase):
    def test_gen3_dosu_rider(self):
        # 3세대, 도수치료 30만원 특약: 공제 = max(30만*0.3=9만, 2만) = 9만 -> 지급 21만
        r = gen_result(
            "gen3", care_type="통원", hospital_type="병원",
            paid_copay=0, nonpaid=20_000,
            riders={"도수": 300_000},
        )
        self.assertIn("도수", r["rider_detail"])
        self.assertEqual(r["rider_detail"]["도수"]["deduct"], 90_000)
        self.assertEqual(r["rider_detail"]["도수"]["pay"], 210_000)
        self.assertEqual(r["rider_pay"], 210_000)

    def test_gen3_rider_min_copay_floor(self):
        # 특약 소액: 5만원 도수 -> 공제 = max(1.5만, 2만) = 2만 -> 지급 3만
        r = gen_result(
            "gen4", care_type="통원", hospital_type="의원",
            paid_copay=0, nonpaid=0,
            riders={"도수": 50_000},
        )
        self.assertEqual(r["rider_detail"]["도수"]["deduct"], 20_000)
        self.assertEqual(r["rider_detail"]["도수"]["pay"], 30_000)

    def test_rider_capped_at_annual_limit(self):
        # 단건이 연한도(도수 350만)를 초과하면 캡 적용
        r = gen_result(
            "gen4", care_type="통원", hospital_type="의원",
            paid_copay=0, nonpaid=0,
            riders={"도수": 10_000_000},
        )
        self.assertEqual(r["rider_detail"]["도수"]["pay"], 3_500_000)

    def test_gen1_no_rider_concept_merges_into_nonpaid(self):
        # 1세대는 특약 개념이 없어 비급여로 통합 계산
        r = gen_result(
            "gen1", care_type="통원", hospital_type="의원",
            paid_copay=0, nonpaid=0,
            riders={"도수": 100_000},
        )
        self.assertEqual(r["rider_detail"], {})
        # 비급여 통합: max(0,5000)=5000 공제 -> 95000 지급
        self.assertEqual(r["nonpaid_pay"], 95_000)
        self.assertEqual(r["expected_payout"], 95_000)


class TestOutpatientCap(unittest.TestCase):
    def test_outpatient_visit_cap_applied(self):
        # 4세대, 매우 큰 급여+비급여 통원 청구 -> 20만원 캡 적용
        # 캡 전 지급액: 급여 80만(100만-20만), 비급여 70만(100만-30만) -> 비율 8:7 유지되며 축소
        r = gen_result(
            "gen4", care_type="통원", hospital_type="상급종합",
            paid_copay=1_000_000, nonpaid=1_000_000,
        )
        self.assertTrue(r["outpatient_capped"])
        self.assertEqual(r["paid_pay"] + r["nonpaid_pay"], 200_000)
        self.assertAlmostEqual(r["paid_pay"] / r["nonpaid_pay"], 800_000 / 700_000, places=3)

    def test_no_cap_when_under_limit(self):
        r = gen_result(
            "gen3", care_type="통원", hospital_type="의원",
            paid_copay=30_000, nonpaid=50_000,
        )
        self.assertFalse(r["outpatient_capped"])


class TestPrescription(unittest.TestCase):
    def test_prescription_deductible(self):
        # 처방조제 8000원 정액공제 (2-1세대 이후), 급여 20000원
        # 공제 = max(20000*0.1=2000, 8000) = 8000 -> 지급 12000
        r = gen_result(
            "gen2_1", care_type="처방조제", hospital_type="의원",
            paid_copay=20_000, nonpaid=0,
        )
        self.assertEqual(r["paid_pay"], 12_000)

    def test_gen1_prescription_no_deductible(self):
        r = gen_result(
            "gen1", care_type="처방조제", hospital_type="의원",
            paid_copay=20_000, nonpaid=0,
        )
        self.assertEqual(r["paid_pay"], 20_000)


class TestCalculateAll(unittest.TestCase):
    def test_returns_five_generations_in_order(self):
        results = calculate_all(
            care_type="통원", hospital_type="의원",
            paid_copay=10_000, nonpaid=10_000,
        )
        self.assertEqual(
            [r["generation"] for r in results],
            ["gen1", "gen2_1", "gen2_2", "gen3", "gen4"],
        )

    def test_claim_total_includes_riders(self):
        results = calculate_all(
            care_type="통원", hospital_type="의원",
            paid_copay=10_000, nonpaid=10_000,
            riders={"MRI": 300_000},
        )
        for r in results:
            self.assertEqual(r["claim_total"], 320_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
