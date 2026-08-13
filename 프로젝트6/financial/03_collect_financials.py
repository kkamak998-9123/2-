# -*- coding: utf-8 -*-
"""companies_universe.csv의 50개 금융회사에 대해 dart-fss로 CFS(연결) 재무제표를
추출해 Samil Project DB 스키마(corp_code, stock_code, corp_name, year, fs_div, sj_div,
account_name, amount, memo, updated_at)의 롱포맷 CSV로 저장한다.

계정 선정 방법(파일럿 검증 완료 - pilot_*.csv 참고):
1) 표준 IFRS concept_id로 잡히는 항목(자산총계/부채총계/자본총계/당기순이익/영업이익/
   이자수익/이자비용/수수료수익 등)은 CONCEPT_MAP으로 정규화한다. concept_id는 회사마다
   라벨 표기가 달라도(예: "당기순이익" vs "연결당기순이익") 안정적으로 동일하다.
2) 업권 고유 항목(신용판매수익/할부금융자산/보험수익/예수부채 등)은 label_ko가 회사마다
   커스텀 확장 태그를 쓰는 경우가 많아 concept_id로 못 묶는다 - 업권별 label_ko
   키워드 허용목록으로 잡는다. 못 잡는 회사가 있을 수 있음(커버리지 100% 아님, 스펙 PART V 참고).
"""
import csv
import re
import time
from pathlib import Path

import dart_fss

BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / ".env"
UNIVERSE_PATH = BASE_DIR / "companies_universe.csv"
OUT_PATH = BASE_DIR / "financial_raw.csv"

BGN_DE = "20250101"
END_DE = "20260630"

# concept_id -> 정규화된 계정명 (업권 공통, 파일럿에서 4개 업권 모두 확인됨)
CONCEPT_MAP = {
    "ifrs-full_Assets": "자산총계",
    "ifrs-full_Liabilities": "부채총계",
    "ifrs-full_Equity": "자본총계",
    "ifrs-full_ProfitLoss": "당기순이익",
    "ifrs-full_ProfitLossFromOperatingActivities": "영업이익",
    "ifrs-full_ProfitLossBeforeTax": "법인세비용차감전순이익",
    "ifrs-full_RevenueFromInterest": "이자수익",
    "ifrs-full_InterestExpense": "이자비용",
    "ifrs-full_InterestRevenueExpense": "순이자손익",
    "ifrs-full_FeeAndCommissionIncome": "수수료수익",
    "ifrs-full_FeeAndCommissionExpense": "수수료비용",
    "ifrs-full_FeeAndCommissionIncomeExpense": "순수수료손익",
    "ifrs-full_DepositsFromCustomers": "예수부채",
    "ifrs-full_InsuranceRevenue": "보험수익",
    "ifrs-full_InsuranceServiceExpensesFromInsuranceContractsIssued": "보험서비스비용",
    "dart_InsuranceRevenueExpense": "보험손익",
    "dart_LoansAtAmortisedCost": "대출채권",
    "ifrs-full_ImpairmentLossImpairmentGainAndReversalOfImpairmentLossDeterminedInAccordanceWithIFRS9": "금융자산손상차손",
    "ifrs-full_CashAndCashEquivalents": "현금및현금성자산",
    "dart_CashAndDuefromBanks": "현금및예치금",
}

# concept_id 컬럼 자체가 없는 회사(예: 삼성화재해상보험 - web dataset이 단순 표만 반환)를 위한
# label_ko 직접 매칭용 - CONCEPT_MAP의 정규화된 계정명과 동일한 라벨이 보이면 그대로 채택
CANONICAL_LABELS = set(CONCEPT_MAP.values())

# 업권별 label_ko 키워드 허용목록(정확히 일치하는 라벨만) - concept_id로 못 묶는 업권 고유 항목
INDUSTRY_LABEL_ALLOWLIST = {
    "bank": {"상각후원가대출채권", "차입부채", "사채"},
    "securities": {"차입부채", "순영업손익", "발행사채"},
    "insurance": {"보험계약부채", "투자손익", "보험영업수익", "보험영업비용"},
    "cardcapital": {
        "영업수익", "신용판매수익", "금융상품수익", "할부금융수익", "리스수익",
        "신용판매자산", "할부금융자산", "운용리스자산", "차입금", "사채", "대손상각비",
    },
}

FS_TP = ("bs", "cis")
SJ_DIV_MAP = {"bs": "BS", "cis": "IS"}


def load_universe():
    with open(UNIVERSE_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_api_key():
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            if line.startswith("DART_API_KEY="):
                return line.strip().split("=", 1)[1]
    raise RuntimeError("DART_API_KEY not found")


def rows_from_sheet(df, sj_div, industry_id, company):
    """FinancialStatement의 bs/cis 데이터프레임에서 필요한 행만 롱포맷으로 변환"""
    if df is None:
        return []

    allow_labels = INDUSTRY_LABEL_ALLOWLIST.get(industry_id, set())
    cols = df.columns
    # 첫 레벨 헤더(보고서 제목)는 무시하고, concept_id/label_ko/연도컬럼만 사용
    # 회사에 따라(특히 web 데이터셋 fallback 시) concept_id 컬럼 자체가 없는 경우가 있어
    # label_ko 매칭만으로도 동작하도록 방어적으로 처리
    concept_matches = [c for c in cols if isinstance(c, tuple) and c[1] == "concept_id"]
    label_matches = [c for c in cols if isinstance(c, tuple) and c[1] == "label_ko"]
    if not label_matches:
        return []
    concept_col = concept_matches[0] if concept_matches else None
    label_col = label_matches[0]
    # BS 연도컬럼은 'YYYYMMDD'(시점), CIS/IS 연도컬럼은 'YYYYMMDD-YYYYMMDD'(기간) 형식이라
    # 둘 다 잡아야 함 - 기간 형식은 종료일(뒤 8자리) 기준으로 연도를 판단
    year_cols = [
        c for c in cols
        if isinstance(c, tuple)
        and (re.fullmatch(r"\d{8}", str(c[0])) or re.fullmatch(r"\d{8}-\d{8}", str(c[0])))
    ]

    out = []
    for _, row in df.iterrows():
        label = row[label_col]
        account_name = None
        if concept_col is not None:
            concept_id = row[concept_col]
            account_name = CONCEPT_MAP.get(concept_id)
        if account_name is None:
            if label in CANONICAL_LABELS:
                account_name = label
            elif label in allow_labels:
                account_name = label
            else:
                continue
        for ycol in year_cols:
            amount = row[ycol]
            if amount is None or (isinstance(amount, float) and amount != amount):  # NaN
                continue
            year = ycol[0][-8:][:4]
            out.append({
                "corp_code": company["corp_code"],
                "stock_code": company["stock_code"],
                "corp_name": company["corp_name"],
                "year": year,
                "fs_div": "CFS",
                "sj_div": sj_div,
                "account_name": account_name,
                "amount": amount,
                "memo": "",
                "updated_at": "",
            })
    return out


def collect_company(corp_list, company):
    corp = corp_list.find_by_corp_code(company["corp_code"])
    if corp is None:
        return [], f"corp_code {company['corp_code']} not found in corp_list"

    try:
        fs = corp.extract_fs(bgn_de=BGN_DE, end_de=END_DE, fs_tp=FS_TP, dataset="web", progressbar=False)
    except Exception as e:  # dart-fss가 문서 파싱 실패 시 다양한 예외를 던짐
        return [], f"extract_fs failed: {e}"

    rows = []
    for tp in FS_TP:
        try:
            sheet = fs[tp]
            rows.extend(rows_from_sheet(sheet, SJ_DIV_MAP[tp], company["industry_id"], company))
        except Exception as e:
            return rows, f"{tp} sheet processing failed: {e}"
    if not rows:
        return [], "no matching accounts extracted"
    return rows, None


def main():
    dart_fss.set_api_key(load_api_key())
    corp_list = dart_fss.get_corp_list()
    companies = load_universe()

    done_codes = set()
    existing_rows = []
    if OUT_PATH.exists():
        with open(OUT_PATH, encoding="utf-8-sig") as f:
            existing_rows = list(csv.DictReader(f))
        done_codes = {r["corp_code"] for r in existing_rows}

    fieldnames = ["corp_code", "stock_code", "corp_name", "year", "fs_div", "sj_div",
                  "account_name", "amount", "memo", "updated_at"]
    errors = []
    all_rows = list(existing_rows)

    remaining = [c for c in companies if c["corp_code"] not in done_codes]
    print(f"총 대상: {len(companies)}건, 이미 수집됨: {len(done_codes)}건, 남은 대상: {len(remaining)}건")

    for i, company in enumerate(remaining, 1):
        try:
            rows, err = collect_company(corp_list, company)
        except Exception as e:  # 한 회사의 예상 못한 실패로 전체 배치가 죽지 않도록 최종 방어선
            rows, err = [], f"unexpected error: {e}"
        if err:
            errors.append((company["corp_name"], err))
        all_rows.extend(rows)

        with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_rows)

        status = "OK" if not err else f"FAIL({err[:60]})"
        with open(BASE_DIR / "collect_progress.log", "a", encoding="utf-8") as logf:
            logf.write(f"[{i}/{len(remaining)}] {company['corp_name']} {status}\n")

        time.sleep(0.3)

    with open(BASE_DIR / "collect_errors.txt", "w", encoding="utf-8") as f:
        for name, err in errors:
            f.write(f"{name}: {err}\n")

    print(f"완료. 총 {len(all_rows)}행 저장, 실패 {len(errors)}건 (collect_errors.txt 참고)")


if __name__ == "__main__":
    main()
