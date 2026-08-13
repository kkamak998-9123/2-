# -*- coding: utf-8 -*-
"""candidates_raw.csv(KRX sector 원본 229건)를 검토해 4개 서브섹터(은행/증권/보험/카드캐피탈)
대상 기업만 골라 companies_universe.csv로 정리한다. 제외 사유는 excluded.csv에 남긴다.

분류 판단 근거(수작업 검증 완료):
- "기타 금융업" sector는 금융지주 + 카드/캐피탈뿐 아니라 LG/GS/SK/CJ 같은 일반 지주회사,
  창업투자회사(VC), 외국계 우회상장 쉘(900번대 종목코드)까지 섞여 있어 이름 기반으로 걸러야 함.
- "금융 지원 서비스업"은 증권사 외에 카카오페이/NHN KCP 같은 PG·전자금융업체와 스팩이 섞여 있음.
- "신탁업 및 집합투자업"(리츠·부동산신탁·VC)과 "보험 및 연금관련 서비스업"(GA 대리점)은
  재무제표 구조가 은행/증권/보험/카드와 또 달라 이번 스펙 범위에서 통째로 제외.
"""
import csv
from pathlib import Path

BASE_DIR = Path(__file__).parent
IN_PATH = BASE_DIR / "candidates_raw.csv"
UNIVERSE_PATH = BASE_DIR / "companies_universe.csv"
EXCLUDED_PATH = BASE_DIR / "excluded.csv"

# 실제 금융지주회사(9개) - "기타 금융업"에 섞인 일반 지주회사와 구분하기 위해 화이트리스트로 관리
FINANCIAL_HOLDINGS = {
    "KB금융", "신한지주", "하나금융지주", "우리금융지주", "JB금융지주",
    "BNK금융지주", "iM금융지주", "한국금융지주", "메리츠금융지주",
}

# 카드/캐피탈(여신전문금융업) - "기타 금융업"에서 이름 패턴으로 식별
CARD_CAPITAL_KEYWORDS = ("카드", "캐피탈")

# 신탁업 및 집합투자업 / 보험및연금관련서비스업 섹터는 통째로 제외
EXCLUDE_SECTORS = {"신탁업 및 집합투자업", "보험 및 연금관련 서비스업"}

# 증권사가 아닌 핀테크/PG/전자금융업체 (금융 지원 서비스업 섹터 내 노이즈)
NON_SECURITIES_FINTECH = {"카카오페이", "NHN KCP", "헥토파이낸셜", "글로벌텍스프리"}


def is_spac(name: str) -> bool:
    return "스팩" in name


def is_foreign_shell(stock_code: str) -> bool:
    # 900번대 종목코드 = 외국기업 국내 우회상장 (텐센트뮤직 계열 등 실질과 무관한 쉘 다수)
    return stock_code.startswith("900")


def classify(row: dict) -> tuple[str | None, str]:
    """(industry_id 또는 None, 분류/제외 사유)"""
    sector = row["sector"]
    name = row["corp_name"]
    stock_code = row["stock_code"]

    if is_spac(name):
        return None, "스팩(SPAC) - 실질 사업 없음"
    if is_foreign_shell(stock_code):
        return None, "900번대 종목코드 - 외국기업 우회상장 쉘로 추정, 수작업 확인 필요"
    if sector in EXCLUDE_SECTORS:
        return None, f"섹터 제외 대상({sector}) - 리츠/신탁/VC/GA대리점 등 이번 스펙 범위 밖"

    if sector == "은행 및 저축기관":
        return "bank", "은행/저축은행"

    if sector in ("보험업", "재 보험업"):
        return "insurance", "보험/재보험"

    if sector == "금융 지원 서비스업":
        if name in NON_SECURITIES_FINTECH:
            return None, "PG/전자금융업체 - 증권사 아님, 구조가 달라 제외"
        return "securities", "증권"

    if sector == "기타 금융업":
        if name in FINANCIAL_HOLDINGS:
            return "bank", "금융지주(은행 그룹으로 분류, PART V 한계 참고)"
        if any(k in name for k in CARD_CAPITAL_KEYWORDS):
            return "cardcapital", "카드/캐피탈"
        return None, "일반(비금융) 지주회사 또는 VC/창투사로 판단, 제외"

    return None, f"미분류 섹터({sector})"


def main():
    with open(IN_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    universe_rows = []
    excluded_rows = []
    for r in rows:
        industry_id, reason = classify(r)
        out = {
            "corp_code": r["corp_code"],
            "stock_code": r["stock_code"],
            "corp_name": r["corp_name"],
            "market": r["market_type"],
            "krx_sector": r["sector"],
        }
        if industry_id:
            out["industry_id"] = industry_id
            out["classification_note"] = reason
            universe_rows.append(out)
        else:
            out["exclude_reason"] = reason
            excluded_rows.append(out)

    with open(UNIVERSE_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["corp_code", "stock_code", "corp_name", "market", "krx_sector",
                        "industry_id", "classification_note"],
        )
        w.writeheader()
        w.writerows(sorted(universe_rows, key=lambda x: (x["industry_id"], x["corp_name"])))

    with open(EXCLUDED_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["corp_code", "stock_code", "corp_name", "market", "krx_sector", "exclude_reason"]
        )
        w.writeheader()
        w.writerows(excluded_rows)

    by_industry = {}
    for r in universe_rows:
        by_industry.setdefault(r["industry_id"], []).append(r["corp_name"])

    print(f"총 후보: {len(rows)}건 -> 포함: {len(universe_rows)}건 / 제외: {len(excluded_rows)}건")
    for industry_id, names in by_industry.items():
        print(f"\n[{industry_id}] {len(names)}개")
        for n in names:
            print(f"  - {n}")


if __name__ == "__main__":
    main()
