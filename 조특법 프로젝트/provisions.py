"""조세특례제한법 개인(소득세) 특례 — 1차 버전 구조화 데이터.

각 항목의 요건/감면율/한도금액은 law.go.kr에서 받아온 실제 조문 원문
(법령일련번호 280409, 2026-07-01 시행)을 근거로 요약했다. 조문은 항/호/목이
복잡하게 얽혀 있어 이 파일은 "1차 스크리닝"을 위한 단순화된 버전이며,
정확한 적용 여부는 반드시 원문(조번호)을 대조해야 한다.

애초 후보였던 제86조의4(연금계좌세액공제 등, 50세 이상 한도 특례)는 원문상
"2022년 12월 31일까지 적용"으로 명시되어 있어 이미 만료된 조항이라 제외했다.
"""

STATUS_OK = "적용 가능"
STATUS_CHECK = "확인 필요"
STATUS_NO = "해당 없음"


def _is_individual(pf):
    return bool(pf.get("is_employee") or pf.get("is_business_owner"))


def _rng(profile, lo=None, hi=None, field="age"):
    v = profile.get(field)
    if v is None:
        return None
    if lo is not None and v < lo:
        return False
    if hi is not None and v > hi:
        return False
    return True


# ---------------------------------------------------------------------------
# 개별 조항 평가 함수. 각 함수는 (status, rate, cap, deadline, note) 반환.
# ---------------------------------------------------------------------------

def _p6(pf):
    if not (pf.get("is_business_owner") or pf.get("is_corp")):
        return STATUS_NO, None, None, None, None
    youth = pf.get("is_youth", False)
    region = pf.get("region")
    if region == "seoul_dense":
        rate = "100분의 100(청년) / 100분의 50(일반)" if youth else "100분의 50"
    elif region == "seoul_decline":
        rate = "100분의 100"
    elif region == "seoul_other":
        rate = "100분의 75(청년) / 100분의 25(일반)"
    else:  # nonseoul
        rate = "100분의 100(청년) / 100분의 50(일반)"
    return (
        STATUS_CHECK,
        rate + " (2026.1.1 이후 창업 기준, 청년/지역에 따라 세분화)",
        "감면세액 합계 연 5억원 한도. 수입금액 1.04억원 이하 소기업은 별도 100%/50% 규정(6항)",
        "2027-12-31 이전 창업분까지",
        "업종 요건(제3항 각 호: 제조업·건설업·정보통신업 등 열거 업종 여부)은 원문 확인 필요. "
        "부동산업·숙박업 등 열거되지 않은 업종은 제외됨.",
    )


def _p7(pf):
    if not (pf.get("is_business_owner") or pf.get("is_corp")):
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "업종·지역·기업규모별 100분의 5~30 (도매업 등은 별도)",
        "1억원(상시근로자 감소 시 차감), 10년 이상 계속 사업 등 요건 충족 시 110% 가산",
        "2028-12-31 이전 종료 과세연도까지",
        "감면 업종(제1항제1호 가~부목 열거 업종)에 해당하는지 원문 확인 필요.",
    )


def _p18(pf):
    if not (pf["is_foreigner"] and pf["is_employee"]):
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "100분의 50 (소재·부품·장비 관련 기술자는 최초 3년 70%, 이후 2년 50%)",
        "한도 규정 없음(해당 근로소득 전체에 비율 적용)",
        "2026-12-31 이전 최초 근로제공분까지, 그 후 10년간",
        "'대통령령으로 정하는 외국인기술자' 요건 충족 여부 확인 필요.",
    )


def _p18_2(pf):
    if not (pf["is_foreigner"] and pf["is_employee"]):
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "단일세율 19% 적용 (누진세율 대신 선택 가능)",
        "한도 없음(단, 각종 비과세·공제·세액공제 규정 적용 배제)",
        "2026-12-31 이전 최초 근로제공 개시분까지, 그 후 20년간",
        "특수관계기업(외국인투자기업 제외) 근무는 제외 대상.",
    )


def _p18_3(pf):
    if not pf["is_employee"]:
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "100분의 50",
        "한도 규정 없음",
        "2028-12-31 이전 취업분까지, 그 후 10년간",
        "'학위 취득 후 국외 5년 이상 거주 + 연구개발 경험을 갖춘 내국인 우수인력'이 대통령령으로 정하는 "
        "연구기관 등에 취업한 경우만 해당. 해외 거주·학위 요건 확인 필요.",
    )


def _p29_6(pf):
    if not pf["is_employee"]:
        return STATUS_NO, None, None, None, None
    youth = pf.get("is_youth", False)
    rate = "청년: 중소기업 90% / 중견기업 50%" if youth else "일반: 중소기업 50% / 중견기업 30%"
    return (
        STATUS_CHECK,
        rate,
        "한도 규정 없음(공제금 중 기업 기여금 부분에 비율 적용)",
        "성과보상공제(내일채움공제 등)에 2027-12-31까지 가입한 경우",
        "중소기업 인력지원 특별법상 성과보상기금(내일채움공제 등)에 가입해 3년 이상 납입 후 수령해야 적용됨.",
    )


def _p30(pf):
    if not pf["is_employee"]:
        return STATUS_NO, None, None, None, None
    youth = pf.get("is_youth", False)
    disabled = pf.get("is_disabled", False)
    sixty = pf.get("is_60_plus", False)
    career_break = pf.get("is_career_break_woman", False)
    if not (youth or disabled or sixty or career_break):
        return STATUS_CHECK, None, None, None, "청년/60세 이상/장애인/경력단절여성 중 어디에도 해당하지 않으면 대상이 아닐 가능성이 큼."
    rate = "100분의 90 (청년)" if youth else "100분의 70 (60세 이상·장애인·경력단절여성)"
    period = "5년" if youth else "3년"
    return (
        STATUS_OK,
        rate,
        "과세기간별 200만원 한도",
        "2026-12-31 이전 중소기업체 취업분까지, 취업일로부터 " + period,
        "'중소기업체'(비영리 포함, 대통령령으로 정한 업종 제외)에 해당하는지, 최초 취업일 기준으로 계산됨을 유의.",
    )


def _p87(pf):
    if not pf["is_employee"]:
        return STATUS_NO, None, None, None, None
    if pf.get("no_house") is False:
        return STATUS_NO, None, None, None, "무주택 세대주(또는 세대주 배우자)만 대상."
    salary = pf.get("annual_salary_10k")
    if salary is not None and salary > 7000:
        return STATUS_NO, None, None, None, "총급여 7천만원 초과 시 소득공제 대상 아님."
    note = "청년우대형(가입 당시 청년+무주택 세대주 등, 직전 총급여 3,600만원 이하 등)은 이자소득 500만원까지 비과세 별도 적용."
    return (
        STATUS_OK,
        "납입액의 100분의 40",
        "연 300만원 납입한도 기준 소득공제(다른 주택 관련 공제와 합산 연 400만~800만원 한도)",
        "2028-12-31까지 납입분",
        note,
    )


def _p91_18(pf):
    if not _is_individual(pf):
        return STATUS_NO, None, None, None, None
    age = pf.get("age")
    if age is not None and age < 15:
        return STATUS_NO, None, None, None, None
    salary = pf.get("annual_salary_10k")
    cap = "일반 200만원 비과세"
    if salary is not None and salary <= 5000:
        cap = "총급여 5천만원 이하 등 서민형 요건 충족 시 400만원 비과세"
    return (
        STATUS_OK,
        "비과세 한도 초과분은 100분의 9 분리과세",
        cap + " (초과분은 9% 세율)",
        "만기·재가입 제한 없음(계약기간 3년 이상, 총납입한도 1억원)",
        "ISA(개인종합자산관리계좌). 3년 이내 중도해지 시 비과세 혜택 추징됨.",
    )


def _p91_20(pf):
    if not _is_individual(pf) or not pf.get("is_youth"):
        return STATUS_NO, None, None, None, None
    salary = pf.get("annual_salary_10k")
    if salary is not None and salary > 5000:
        return STATUS_CHECK, None, None, None, "총급여 5천만원 초과 시 가입 자체는 가능하나 실제 소득공제는 8천만원 초과 시 배제됨."
    return (
        STATUS_OK,
        "납입액의 100분의 40",
        "연 600만원 납입한도 기준 소득공제",
        "2025-12-31까지 가입분, 계약기간 3~5년",
        "청년형 장기집합투자증권저축. 3년 미만 해지 시 추징세액(납입누계액의 6%) 발생.",
    )


def _p91_22(pf):
    if not _is_individual(pf) or not pf.get("is_youth"):
        return STATUS_NO, None, None, None, None
    salary = pf.get("annual_salary_10k")
    if salary is not None and salary > 7500:
        return STATUS_NO, None, None, None, "총급여 7,500만원 초과 시 대상 아님."
    return (
        STATUS_OK,
        "이자·배당소득 전액 비과세",
        "연 840만원 납입한도",
        "2025-12-31까지 가입분",
        "청년도약계좌. 3년 이내 해지 시 비과세 추징(부득이한 사유·청년미래적금 전환 제외).",
    )


def _p92(pf):
    if not _is_individual(pf) or not pf.get("married_this_year"):
        return STATUS_NO, None, None, None, None
    return (
        STATUS_OK,
        "정액 공제",
        "50만원 (평생 1회 한정)",
        "2026-12-31 이전 혼인신고분까지",
        "혼인신고 1회에 한해 적용, 재혼 등도 생애 1회로 한정.",
    )


def _p95_2(pf):
    if not pf["is_employee"]:
        return STATUS_NO, None, None, None, None
    if pf.get("no_house") is False:
        return STATUS_NO, None, None, None, "무주택 세대주(또는 세대원)만 대상."
    salary = pf.get("annual_salary_10k")
    if salary is not None and salary > 8000:
        return STATUS_NO, None, None, None, "총급여 8천만원 초과 시 대상 아님."
    rate = "100분의 17" if (salary is not None and salary <= 5500) else "100분의 15"
    return (
        STATUS_OK,
        rate,
        "월세액 연 1,000만원까지만 인정",
        "상시 적용(과세기간 단위)",
        "배우자가 별도 세대인 경우 등 일정 요건 하에 배우자도 추가 공제 가능(2026년 개정분).",
    )


def _p100_2(pf):
    if not pf["is_employee"] and not pf["is_business_owner"]:
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "가구 유형(단독/홑벌이/맞벌이)·총급여액 구간별 산정표 적용 (예: 단독가구 최대 165만원, 홑벌이 285만원, 맞벌이 330만원)",
        "재산합계액 1억7천만원 이상이면 산정액의 50%만 지급, 재산 요건(2.4억원 등) 초과 시 미지급",
        "매년 정기/반기 신청",
        "근로장려금(EITC). 소득·재산 요건이 세부적이라 국세청 모의계산이 필요. 근로소득자·사업소득자·종교인소득자 모두 대상.",
    )


def _p100_27(pf):
    if not _is_individual(pf):
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "부양자녀 수·총급여액 구간별 산정",
        "자녀 1인당 최대 100만원 수준(요건별 상이)",
        "매년 신청",
        "자녀장려금. 부양자녀(만 18세 미만)가 있는 경우만 해당하며, 세부 산정은 국세청 모의계산 필요.",
    )


def _p122_3(pf):
    if not pf["is_business_owner"]:
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "의료비 15%(난임시술 30%) + 월세액 15~17%",
        "의료비: 소득세법 제59조의4 준용 한도 / 월세액: 연 1,000만원 한도",
        "2026-12-31이 속하는 과세연도까지",
        "'성실사업자' 요건(직전 3년 평균 대비 수입 50% 이상 증가, 2년 이상 계속사업 등) 또는 성실신고확인대상사업자 확인 필요.",
    )


def _p126_2(pf):
    if not pf["is_employee"]:
        return STATUS_NO, None, None, None, None
    salary = pf.get("annual_salary_10k")
    base_cap = "연 300만원" if (salary is not None and salary <= 7000) else "연 250만원"
    return (
        STATUS_CHECK,
        "신용카드 15% / 직불·선불카드·현금영수증 30% / 전통시장·대중교통 40%",
        base_cap + " (자녀 1명 이상이면 최대 350~400만원까지 확대)",
        "2028-12-31까지 사용분",
        "총급여의 25% 초과 사용액부터 공제 대상. 정확한 공제액은 사용처별 비중에 따라 달라짐.",
    )


PROVISIONS = [
    {"article": "6", "branch": "", "title": "창업중소기업 등에 대한 세액감면", "eval": _p6},
    {"article": "7", "branch": "", "title": "중소기업에 대한 특별세액감면", "eval": _p7},
    {"article": "18", "branch": "", "title": "외국인기술자에 대한 소득세의 감면", "eval": _p18},
    {"article": "18", "branch": "2", "title": "외국인근로자에 대한 과세특례", "eval": _p18_2},
    {"article": "18", "branch": "3", "title": "내국인 우수 인력의 국내복귀에 대한 소득세 감면", "eval": _p18_3},
    {"article": "29", "branch": "6", "title": "중소기업 청년근로자 및 핵심인력 성과보상기금 수령액에 대한 소득세 감면 등", "eval": _p29_6},
    {"article": "30", "branch": "", "title": "중소기업 취업자에 대한 소득세 감면", "eval": _p30},
    {"article": "87", "branch": "", "title": "주택청약종합저축 등에 대한 소득공제 등", "eval": _p87},
    {"article": "91", "branch": "18", "title": "개인종합자산관리계좌(ISA)에 대한 과세특례", "eval": _p91_18},
    {"article": "91", "branch": "20", "title": "청년형 장기집합투자증권저축에 대한 소득공제", "eval": _p91_20},
    {"article": "91", "branch": "22", "title": "청년도약계좌에 대한 비과세", "eval": _p91_22},
    {"article": "92", "branch": "", "title": "혼인에 대한 세액공제", "eval": _p92},
    {"article": "95", "branch": "2", "title": "월세액에 대한 세액공제", "eval": _p95_2},
    {"article": "100", "branch": "2", "title": "근로장려세제", "eval": _p100_2},
    {"article": "100", "branch": "27", "title": "자녀장려세제", "eval": _p100_27},
    {"article": "122", "branch": "3", "title": "성실사업자에 대한 의료비 등 공제", "eval": _p122_3},
    {"article": "126", "branch": "2", "title": "신용카드 등 사용금액에 대한 소득공제", "eval": _p126_2},
]
