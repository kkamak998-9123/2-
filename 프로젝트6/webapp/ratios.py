# -*- coding: utf-8 -*-
"""업종별 재무비율 계산. 업종마다 사업보고서에서 뽑아둔 계정과목이 달라서
(반도체는 20개 계정, 방산은 7개뿐) 업종별로 계산 가능한 비율셋을 따로 정의한다.

반도체 비율/공식은 사용자가 이미 검증해 둔 반도체_재무비율_대시보드.html 기준을 그대로 따름.
EBITDA는 외부 데이터 소스로 2025년치만 입력되어 있어, EBITDA 기반 지표는 2025년만 산출된다.
방산·건설은 현재 확보된 계정과목 안에서 의미있는 지표를 임시로 구성 - 계정과목이
보강되면(예: 방산에 당기순이익/자산총계 추가) 언제든 갱신 가능.
"""


def _safe_div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def _pct(a, b):
    v = _safe_div(a, b)
    return v * 100 if v is not None else None


# ---------------------------------------------------------------------------
# 반도체: 20개 계정과목(19개 재무제표 계정 + EBITDA) -> 17개 파생비율
# 기존 반도체_재무비율_대시보드.html과 동일 공식에 EBITDA마진율·Capex/EBITDA를 추가.
# ---------------------------------------------------------------------------

def compute_semiconductor(acc: dict) -> dict:
    revenue = acc.get("매출액")
    cogs = acc.get("매출원가")
    opinc = acc.get("영업이익")
    ni = acc.get("당기순이익")
    assets = acc.get("총자산")
    liab = acc.get("부채총계")
    equity = acc.get("자본총계")
    sga = acc.get("판매비와관리비")
    ar = acc.get("매출채권")
    inv = acc.get("재고자산")
    ppe = acc.get("유형자산")
    intangible = acc.get("무형자산")
    capex_ppe = acc.get("유형자산의 취득")
    capex_intangible = acc.get("무형자산의 취득")
    ocf = acc.get("영업활동현금흐름")
    dividend = acc.get("배당금지급")
    interest = acc.get("금융비용")
    ebitda = acc.get("EBITDA")

    capex = None
    if capex_ppe is not None or capex_intangible is not None:
        capex = (capex_ppe or 0) + (capex_intangible or 0)

    fcf = None
    if ocf is not None and capex is not None:
        fcf = ocf - capex

    fixed_assets = None
    if ppe is not None or intangible is not None:
        fixed_assets = (ppe or 0) + (intangible or 0)

    return {
        "revenue": revenue,
        "opinc": opinc,
        "ni": ni,
        "opm": _pct(opinc, revenue),
        "roe": _pct(ni, equity),
        "roa": _pct(ni, assets),
        "gpm": _pct(revenue - cogs, revenue) if revenue is not None and cogs is not None else None,
        "cogsRatio": _pct(cogs, revenue),
        "sgaRatio": _pct(sga, revenue),
        "debtRatio": _pct(liab, equity),
        "equityRatio": _pct(equity, assets),
        "intCov": _safe_div(opinc, interest),
        "assetTurn": _safe_div(revenue, assets),
        "invTurn": _safe_div(cogs, inv),
        "arTurn": _safe_div(revenue, ar),
        "capex": capex,
        "capexRatio": _pct(capex, revenue),
        "fcf": fcf,
        "fcfMargin": _pct(fcf, revenue),
        "fixedAssetRatio": _pct(fixed_assets, assets),
        "ocf": ocf,
        "dividend": dividend,
        "ebitda": ebitda,
        "ebitdaMargin": _pct(ebitda, revenue),
        "capexEbitda": _safe_div(capex, ebitda),
    }


SEMICONDUCTOR_TABLE_COLS = [
    ("revenue", "매출액", "won"),
    ("opm", "영업이익률", "pct"),
    ("roe", "ROE", "pct"),
    ("debtRatio", "부채비율", "pct"),
    ("capexRatio", "Capex/매출", "pct"),
    ("fcfMargin", "FCF마진", "pct"),
    ("fixedAssetRatio", "고정자산비율", "pct"),
]
SEMICONDUCTOR_DETAIL_COLS = [
    ("gpm", "매출총이익률", "pct"),
    ("cogsRatio", "매출원가율", "pct"),
    ("sgaRatio", "SGA비율", "pct"),
    ("roa", "ROA", "pct"),
    ("equityRatio", "자기자본비율", "pct"),
    ("debtRatio", "부채비율", "pct"),
    ("fixedAssetRatio", "고정자산비율", "pct"),
    ("intCov", "이자보상배수", "x"),
    ("assetTurn", "자산회전율", "x"),
    ("invTurn", "재고회전율", "x"),
    ("arTurn", "매출채권회전율", "x"),
    ("capex", "Capex", "won"),
    ("dividend", "배당금지급", "won"),
    ("ebitdaMargin", "EBITDA마진율", "pct"),
    ("capexEbitda", "Capex/EBITDA", "x"),
]
SEMICONDUCTOR_SPARKS = [
    ("revenue", "매출액", "won"),
    ("opm", "영업이익률", "pct"),
    ("roe", "ROE", "pct"),
    ("capex", "유무형자산 취득액", "won"),
]


# ---------------------------------------------------------------------------
# 건설: 17개 계정과목. 영업이익/자본총계가 없어 매출총이익-판관비, 자산-부채로 역산.
# 수주산업 특유의 미청구공사(계약자산) 비중과 유동비율을 핵심 지표로 추가.
# ---------------------------------------------------------------------------

def compute_construction(acc: dict) -> dict:
    revenue = acc.get("매출액")
    cogs = acc.get("매출원가")
    gross_profit = acc.get("매출총이익")
    sga = acc.get("판매비와관리비")
    ni = acc.get("당기순이익")
    assets = acc.get("자산총계")
    liab = acc.get("부채총계")
    ar = acc.get("매출채권")
    inv = acc.get("재고자산")
    ppe = acc.get("유형자산")
    current_assets = acc.get("유동자산")
    current_liab = acc.get("유동부채")
    borrowings = acc.get("차입금")
    contract_asset = acc.get("계약자산(미청구공사)")
    ocf = acc.get("영업활동현금흐름")

    equity = None
    if assets is not None and liab is not None:
        equity = assets - liab

    opinc = None
    if gross_profit is not None and sga is not None:
        opinc = gross_profit - sga

    return {
        "revenue": revenue,
        "opinc": opinc,
        "ni": ni,
        "opm": _pct(opinc, revenue),
        "roe": _pct(ni, equity),
        "roa": _pct(ni, assets),
        "gpm": _pct(gross_profit, revenue),
        "cogsRatio": _pct(cogs, revenue),
        "sgaRatio": _pct(sga, revenue),
        "debtRatio": _pct(liab, equity),
        "equityRatio": _pct(equity, assets),
        "currentRatio": _pct(current_assets, current_liab),
        "contractAssetRatio": _pct(contract_asset, revenue),
        "borrowingRatio": _pct(borrowings, assets),
        "fixedAssetRatio": _pct(ppe, assets),
        "arTurn": _safe_div(revenue, ar),
        "invTurn": _safe_div(cogs, inv),
        "ocfMargin": _pct(ocf, revenue),
        "ocf": ocf,
    }


CONSTRUCTION_TABLE_COLS = [
    ("revenue", "매출액", "won"),
    ("opm", "영업이익률", "pct"),
    ("roe", "ROE", "pct"),
    ("debtRatio", "부채비율", "pct"),
    ("currentRatio", "유동비율", "pct"),
    ("contractAssetRatio", "미청구공사비율", "pct"),
    ("borrowingRatio", "차입금의존도", "pct"),
]
CONSTRUCTION_DETAIL_COLS = [
    ("gpm", "매출총이익률", "pct"),
    ("cogsRatio", "매출원가율", "pct"),
    ("sgaRatio", "SGA비율", "pct"),
    ("roa", "ROA", "pct"),
    ("equityRatio", "자기자본비율", "pct"),
    ("fixedAssetRatio", "고정자산비율(유형자산)", "pct"),
    ("arTurn", "매출채권회전율", "x"),
    ("invTurn", "재고회전율", "x"),
    ("ocfMargin", "OCF마진", "pct"),
]
CONSTRUCTION_SPARKS = [
    ("revenue", "매출액", "won"),
    ("opm", "영업이익률", "pct"),
    ("currentRatio", "유동비율", "pct"),
    ("contractAssetRatio", "미청구공사비율", "pct"),
]


# ---------------------------------------------------------------------------
# 방산: 계정과목 7개뿐(매출액/영업이익/영업활동현금흐름/매출채권/재고자산/계약자산/계약부채).
# 수주산업 특성상 계약자산(미청구)-계약부채(초과청구) 순포지션을 핵심 지표로 사용.
# 당기순이익/총자산 등은 계정과목 미확보로 계산 불가 - 추후 데이터 보강 시 추가.
# ---------------------------------------------------------------------------

def compute_defense(acc: dict) -> dict:
    revenue = acc.get("매출액")
    opinc = acc.get("영업이익")
    ocf = acc.get("영업활동현금흐름")
    ar = acc.get("매출채권")
    inv = acc.get("재고자산")
    contract_asset = acc.get("계약자산")
    contract_liab = acc.get("계약부채")

    net_contract = None
    if contract_asset is not None or contract_liab is not None:
        net_contract = (contract_asset or 0) - (contract_liab or 0)

    return {
        "revenue": revenue,
        "opinc": opinc,
        "opm": _pct(opinc, revenue),
        "ocfMargin": _pct(ocf, revenue),
        "arTurn": _safe_div(revenue, ar),
        "invTurn": _safe_div(revenue, inv),
        "netContractRatio": _pct(net_contract, revenue),
        "contractAssetRatio": _pct(contract_asset, revenue),
        "contractLiabRatio": _pct(contract_liab, revenue),
        "ocf": ocf,
    }


DEFENSE_TABLE_COLS = [
    ("revenue", "매출액", "won"),
    ("opm", "영업이익률", "pct"),
    ("ocfMargin", "OCF마진", "pct"),
    ("netContractRatio", "순계약자산비율", "pct"),
]
DEFENSE_DETAIL_COLS = [
    ("contractAssetRatio", "계약자산비율(미청구)", "pct"),
    ("contractLiabRatio", "계약부채비율(초과청구)", "pct"),
]
DEFENSE_SPARKS = [
    ("revenue", "매출액", "won"),
    ("opm", "영업이익률", "pct"),
    ("ocfMargin", "OCF마진", "pct"),
    ("netContractRatio", "순계약자산비율", "pct"),
    ("arTurn", "매출채권회전율", "x"),
    ("invTurn", "재고회전율", "x"),
]


# ---------------------------------------------------------------------------
# 금융업(은행/증권/보험/카드캐피탈): 매출액 개념이 없고 업권마다 손익구조가 달라
# 업종별로 완전히 다른 계정셋을 씀. 계정은 dart-fss 표준 XBRL concept_id 기준으로
# 정규화된 것(자산총계/부채총계/자본총계/당기순이익/영업이익 등, 업권 공통)과
# 업권 고유 라벨(예수부채/보험수익/신용판매자산 등, concept_id가 회사마다 커스텀 확장
# 태그라 라벨명으로만 잡음)이 섞여 있음 - 03_collect_financials.py 참고.
# BIS비율/K-ICS/NCR/연체율 등 감독규정상 규제비율은 재무제표 자체에 없어 이번 버전엔
# 미포함(사업보고서 원문 파싱 별도 과제, PART V 한계 참고).
# ---------------------------------------------------------------------------

def compute_bank(acc: dict) -> dict:
    interest_income = acc.get("이자수익")
    interest_expense = acc.get("이자비용")
    nii = acc.get("순이자손익")
    fee_income = acc.get("수수료수익")
    fee_expense = acc.get("수수료비용")
    net_fee = acc.get("순수수료손익")
    opinc = acc.get("영업이익")
    ni = acc.get("당기순이익")
    assets = acc.get("자산총계")
    liab = acc.get("부채총계")
    equity = acc.get("자본총계")
    loans = acc.get("대출채권") or acc.get("상각후원가대출채권")
    deposits = acc.get("예수부채")
    cash_due = acc.get("현금및예치금")
    impairment = acc.get("금융자산손상차손")
    borrowings = acc.get("차입부채")
    bonds = acc.get("사채")

    impairment_expense = abs(impairment) if impairment is not None else None
    funding = None
    if borrowings is not None or bonds is not None:
        funding = (borrowings or 0) + (bonds or 0)

    return {
        "nii": nii,
        "interestIncome": interest_income,
        "interestExpense": interest_expense,
        "netFee": net_fee,
        "feeIncome": fee_income,
        "feeExpense": fee_expense,
        "opinc": opinc,
        "ni": ni,
        "roe": _pct(ni, equity),
        "roa": _pct(ni, assets),
        "debtRatio": _pct(liab, equity),
        "equityRatio": _pct(equity, assets),
        "loanDepositRatio": _pct(loans, deposits),
        "impairmentToLoans": _pct(impairment_expense, loans),
        "fundingDependency": _pct(funding, assets),
        "assets": assets,
        "equity": equity,
        "loans": loans,
        "deposits": deposits,
        "cashDue": cash_due,
    }


BANK_TABLE_COLS = [
    ("nii", "순이자손익", "won"),
    ("roe", "ROE", "pct"),
    ("roa", "ROA", "pct"),
    ("loanDepositRatio", "예대율(근사)", "pct"),
    ("impairmentToLoans", "대손비용률(근사)", "pct"),
    ("equityRatio", "자기자본비율", "pct"),
]
BANK_DETAIL_COLS = [
    ("interestIncome", "이자수익", "won"),
    ("interestExpense", "이자비용", "won"),
    ("netFee", "순수수료손익", "won"),
    ("opinc", "영업이익", "won"),
    ("ni", "당기순이익", "won"),
    ("debtRatio", "부채비율", "pct"),
    ("fundingDependency", "차입금·사채의존도", "pct"),
    ("assets", "자산총계", "won"),
    ("loans", "대출채권", "won"),
    ("deposits", "예수부채", "won"),
]
BANK_SPARKS = [
    ("nii", "순이자손익", "won"),
    ("roe", "ROE", "pct"),
    ("loanDepositRatio", "예대율(근사)", "pct"),
    ("impairmentToLoans", "대손비용률(근사)", "pct"),
]


def compute_securities(acc: dict) -> dict:
    fee_income = acc.get("수수료수익")
    fee_expense = acc.get("수수료비용")
    net_fee = acc.get("순수수료손익")
    interest_income = acc.get("이자수익")
    interest_expense = acc.get("이자비용")
    net_interest = acc.get("순이자손익")
    net_operating = acc.get("순영업손익")
    opinc = acc.get("영업이익")
    ni = acc.get("당기순이익")
    assets = acc.get("자산총계")
    liab = acc.get("부채총계")
    equity = acc.get("자본총계")
    deposits = acc.get("예수부채")
    borrowings = acc.get("차입부채")
    bonds = acc.get("발행사채")

    funding = None
    if borrowings is not None or bonds is not None:
        funding = (borrowings or 0) + (bonds or 0)

    return {
        "netOperatingIncome": net_operating,
        "feeIncomeRatio": _pct(net_fee, net_operating),
        "netInterestRatio": _pct(net_interest, net_operating),
        "opinc": opinc,
        "ni": ni,
        "roe": _pct(ni, equity),
        "roa": _pct(ni, assets),
        "debtRatio": _pct(liab, equity),
        "equityRatio": _pct(equity, assets),
        "customerDepositRatio": _pct(deposits, assets),
        "fundingDependency": _pct(funding, assets),
        "netFee": net_fee,
        "assets": assets,
        "equity": equity,
    }


SECURITIES_TABLE_COLS = [
    ("netOperatingIncome", "순영업손익(매출액 대용)", "won"),
    ("roe", "ROE", "pct"),
    ("feeIncomeRatio", "수수료손익비중", "pct"),
    ("netInterestRatio", "순이자손익비중", "pct"),
    ("equityRatio", "자기자본비율", "pct"),
]
SECURITIES_DETAIL_COLS = [
    ("netFee", "순수수료손익", "won"),
    ("opinc", "영업이익", "won"),
    ("ni", "당기순이익", "won"),
    ("roa", "ROA", "pct"),
    ("debtRatio", "부채비율", "pct"),
    ("customerDepositRatio", "투자자예수금비율", "pct"),
    ("fundingDependency", "차입금·사채의존도", "pct"),
    ("assets", "자산총계", "won"),
]
SECURITIES_SPARKS = [
    ("netOperatingIncome", "순영업손익", "won"),
    ("roe", "ROE", "pct"),
    ("feeIncomeRatio", "수수료손익비중", "pct"),
]


def compute_insurance(acc: dict) -> dict:
    insurance_revenue = acc.get("보험수익")
    insurance_service_expense = acc.get("보험서비스비용")
    insurance_pl = acc.get("보험손익")
    investment_pl = acc.get("투자손익")
    opinc = acc.get("영업이익")
    ni = acc.get("당기순이익")
    assets = acc.get("자산총계")
    liab = acc.get("부채총계")
    equity = acc.get("자본총계")
    insurance_liab = acc.get("보험계약부채")

    if insurance_pl is None and insurance_revenue is not None and insurance_service_expense is not None:
        insurance_pl = insurance_revenue - insurance_service_expense

    return {
        "insurancePL": insurance_pl,
        "insuranceRevenue": insurance_revenue,
        "insuranceServiceExpense": insurance_service_expense,
        "investmentPL": investment_pl,
        "opinc": opinc,
        "ni": ni,
        "roe": _pct(ni, equity),
        "roa": _pct(ni, assets),
        "debtRatio": _pct(liab, equity),
        "equityRatio": _pct(equity, assets),
        "insuranceLiabRatio": _pct(insurance_liab, assets),
        "investmentPLShare": _pct(investment_pl, opinc),
        "assets": assets,
        "equity": equity,
    }


INSURANCE_TABLE_COLS = [
    ("insurancePL", "보험손익", "won"),
    ("investmentPL", "투자손익", "won"),
    ("roe", "ROE", "pct"),
    ("insuranceLiabRatio", "보험계약부채비율", "pct"),
    ("equityRatio", "자기자본비율", "pct"),
]
INSURANCE_DETAIL_COLS = [
    ("insuranceRevenue", "보험수익", "won"),
    ("insuranceServiceExpense", "보험서비스비용", "won"),
    ("investmentPLShare", "투자손익/영업이익", "pct"),
    ("opinc", "영업이익", "won"),
    ("ni", "당기순이익", "won"),
    ("roa", "ROA", "pct"),
    ("debtRatio", "부채비율", "pct"),
    ("assets", "자산총계", "won"),
]
INSURANCE_SPARKS = [
    ("insurancePL", "보험손익", "won"),
    ("investmentPL", "투자손익", "won"),
    ("roe", "ROE", "pct"),
]


def compute_cardcapital(acc: dict) -> dict:
    revenue = acc.get("영업수익")
    credit_sales_revenue = acc.get("신용판매수익")
    bad_debt = acc.get("대손상각비")
    opinc = acc.get("영업이익")
    ni = acc.get("당기순이익")
    assets = acc.get("자산총계")
    liab = acc.get("부채총계")
    equity = acc.get("자본총계")
    credit_sales_asset = acc.get("신용판매자산")
    installment_asset = acc.get("할부금융자산")
    borrowings = acc.get("차입금")
    bonds = acc.get("사채")

    funding = None
    if borrowings is not None or bonds is not None:
        funding = (borrowings or 0) + (bonds or 0)

    return {
        "revenue": revenue,
        "creditSalesRevenue": credit_sales_revenue,
        "opinc": opinc,
        "ni": ni,
        "opm": _pct(opinc, revenue),
        "roa": _pct(ni, assets),
        "roe": _pct(ni, equity),
        "leverageRatio": _safe_div(assets, equity),
        "debtRatio": _pct(liab, equity),
        "fundingDependency": _pct(funding, assets),
        "badDebtToRevenue": _pct(bad_debt, revenue),
        "creditSalesAssetRatio": _pct(credit_sales_asset, assets),
        "installmentAssetRatio": _pct(installment_asset, assets),
        "assets": assets,
        "equity": equity,
    }


CARDCAPITAL_TABLE_COLS = [
    ("revenue", "영업수익(매출액 대용)", "won"),
    ("opm", "영업이익률", "pct"),
    ("roa", "ROA", "pct"),
    ("leverageRatio", "레버리지배율", "x"),
    ("badDebtToRevenue", "대손상각비/영업수익", "pct"),
]
CARDCAPITAL_DETAIL_COLS = [
    ("creditSalesRevenue", "신용판매수익", "won"),
    ("opinc", "영업이익", "won"),
    ("ni", "당기순이익", "won"),
    ("roe", "ROE", "pct"),
    ("debtRatio", "부채비율", "pct"),
    ("fundingDependency", "차입금·사채의존도", "pct"),
    ("creditSalesAssetRatio", "신용판매자산비율", "pct"),
    ("installmentAssetRatio", "할부금융자산비율", "pct"),
    ("assets", "자산총계", "won"),
]
CARDCAPITAL_SPARKS = [
    ("revenue", "영업수익", "won"),
    ("opm", "영업이익률", "pct"),
    ("leverageRatio", "레버리지배율", "x"),
    ("badDebtToRevenue", "대손상각비/영업수익", "pct"),
]


INDUSTRY_CONFIG = {
    "semiconductor": {
        "label": "반도체",
        "compute": compute_semiconductor,
        "table_cols": SEMICONDUCTOR_TABLE_COLS,
        "detail_cols": SEMICONDUCTOR_DETAIL_COLS,
        "sparks": SEMICONDUCTOR_SPARKS,
        "note": "20개 계정과목 기반 17개 파생비율. Capex/FCF는 유형·무형자산 취득액 기준. "
                "EBITDA마진율·Capex/EBITDA는 외부 데이터로 확보한 2025년 EBITDA 기준으로만 산출됩니다.",
    },
    "construction": {
        "label": "건설",
        "compute": compute_construction,
        "table_cols": CONSTRUCTION_TABLE_COLS,
        "detail_cols": CONSTRUCTION_DETAIL_COLS,
        "sparks": CONSTRUCTION_SPARKS,
        "note": "영업이익은 매출총이익-판관비로 역산, 자본총계는 자산-부채로 역산한 값입니다. "
                "미청구공사비율·유동비율은 수주산업 특성상 핵심 지표로 추가했습니다. (임시 구성 - 추후 보강 예정)",
    },
    "defense": {
        "label": "방산",
        "compute": compute_defense,
        "table_cols": DEFENSE_TABLE_COLS,
        "detail_cols": DEFENSE_DETAIL_COLS,
        "sparks": DEFENSE_SPARKS,
        "note": "현재 확보된 계정과목이 7개뿐이라 당기순이익·ROE 등은 계산할 수 없습니다. "
                "순계약자산비율(계약자산-계약부채)로 수주 회수 리스크를 대신 보여줍니다. (임시 구성 - 추후 보강 예정)",
    },
    "bank": {
        "label": "은행/지주",
        "compute": compute_bank,
        "table_cols": BANK_TABLE_COLS,
        "detail_cols": BANK_DETAIL_COLS,
        "sparks": BANK_SPARKS,
        "note": "매출액 개념이 없어 순이자손익을 핵심 지표로 사용합니다. 예대율·대손비용률은 "
                "원화 기준이 아닌 연결 전체 기준 근사치입니다. BIS비율·NIM·고정이하여신비율 등 "
                "감독규정상 규제비율은 재무제표에 없어 사업보고서 원문 파싱 없이는 산출 불가(추후 보강 과제).",
    },
    "securities": {
        "label": "증권",
        "compute": compute_securities,
        "table_cols": SECURITIES_TABLE_COLS,
        "detail_cols": SECURITIES_DETAIL_COLS,
        "sparks": SECURITIES_SPARKS,
        "note": "순영업손익(수수료+이자+트레이딩손익 합계)을 매출액 대용 지표로 사용합니다. "
                "영업용순자본비율(신NCR) 등 자본적정성 규제비율은 사업보고서 원문 파싱 필요(추후 보강 과제).",
    },
    "insurance": {
        "label": "보험",
        "compute": compute_insurance,
        "table_cols": INSURANCE_TABLE_COLS,
        "detail_cols": INSURANCE_DETAIL_COLS,
        "sparks": INSURANCE_SPARKS,
        "note": "2023년 IFRS17 전면 도입 이후 기준(보험수익/보험손익)만 산출합니다. 2022년 이전 "
                "수치와는 개념이 달라 단순 비교하면 안 됩니다. 지급여력비율(K-ICS)·손해율·사업비율은 "
                "사업보고서 원문 파싱 필요(추후 보강 과제).",
    },
    "cardcapital": {
        "label": "카드/캐피탈",
        "compute": compute_cardcapital,
        "table_cols": CARDCAPITAL_TABLE_COLS,
        "detail_cols": CARDCAPITAL_DETAIL_COLS,
        "sparks": CARDCAPITAL_SPARKS,
        "note": "영업수익을 매출액 대용 지표로 사용합니다. 예수금이 없어 차입금·사채의존도가 "
                "은행과 다른 의미(전액 시장성 조달)를 가집니다. 연체율·대손충당금적립률·"
                "조정자기자본비율은 사업보고서 원문 파싱 필요(추후 보강 과제).",
    },
}
