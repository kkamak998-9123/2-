"""조세특례제한법 개인 특례 매칭 CLI 진입점."""
import sys
from datetime import date

from matcher import match
from db import get_article, cache_is_empty

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DISCLAIMER = (
    "이 결과는 조세특례제한법 조문을 바탕으로 한 1차 스크리닝이며, "
    "법적 효력이 있는 세무 자문이 아닙니다. 실제 적용 여부는 반드시 "
    "세무사 등 전문가 확인 및 원문 대조가 필요합니다."
)


def ask(prompt: str) -> str:
    return input(prompt).strip()


def ask_yn(prompt: str, default: bool | None = None) -> bool:
    suffix = " (y/n)" if default is None else (" (Y/n)" if default else " (y/N)")
    while True:
        raw = ask(prompt + suffix + ": ").lower()
        if not raw and default is not None:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  y 또는 n으로 답해주세요.")


def ask_int(prompt: str, allow_blank=False) -> int | None:
    while True:
        raw = ask(prompt + ": ")
        if not raw and allow_blank:
            return None
        try:
            return int(raw)
        except ValueError:
            print("  숫자로 입력해주세요.")


def ask_choice(prompt: str, options: dict[str, str]) -> str:
    print(prompt)
    for key, label in options.items():
        print(f"  {key}) {label}")
    while True:
        raw = ask("선택: ")
        if raw in options:
            return raw
        print("  목록에 있는 번호를 입력해주세요.")


ZONE_DESCRIPTIONS = {
    "1": ("연구개발특구", "대덕(대전)·광주·대구·부산·전북 등 정부 지정 첨단기술 클러스터 (2026년 기준 5개 광역특구)"),
    "2": ("제주첨단과학기술단지", "제주특별자치도 제주시 아라동 일대에 지정된 첨단과학기술단지"),
    "3": ("제주투자진흥지구", "제주특별자치도 내 관광·첨단산업 등 투자 유치를 위해 지정된 지구"),
    "4": ("기업도시개발구역 등", "충주·원주(지식기반형), 태안·영암해남(관광레저형) 등 기업도시 및 새만금·평화경제특구 등 유사 개발구역"),
    "5": ("기회발전특구", "2024~2025년 비수도권 14개 시·도(대구·부산·전남·경북·전북·경남·대전·제주·울산·세종·광주·충남·충북·강원) 전역에 지정된 지방투자 유치 특구"),
    "6": ("농공단지 / 중소기업특별지원지역", "농공단지는 농어촌 지역 산업단지, 중소기업특별지원지역은 산업 침체·구조조정으로 중기부가 지정한 지역(예: 부산 금사공업지역, 포항철강산단 등)"),
    "7": ("위기지역(고용위기지역 등)", "고용노동부 지정 고용위기지역(2026년 기준 울산 남구·인천 제물포구 등) 및 산업통상자원부 지정 산업위기대응특별지역"),
    "8": ("해당 없음", ""),
}


def ask_zone() -> str:
    print("\n아래 특구/산업단지 중 입주(예정) 중인 곳이 있나요?")
    for key, (label, desc) in ZONE_DESCRIPTIONS.items():
        line = f"  {key}) {label}"
        if desc:
            line += f" — {desc}"
        print(line)
    while True:
        raw = ask("선택: ")
        if raw in ZONE_DESCRIPTIONS:
            return raw
        print("  목록에 있는 번호를 입력해주세요.")


def _blank_business_fields(profile: dict):
    profile.setdefault("company_size", None)
    profile.setdefault("relocation_type", None)
    profile.setdefault("zone_type", "해당없음")
    profile.setdefault("employment_increased", None)
    profile.setdefault("wage_increased", None)
    profile.setdefault("is_public_agency_relocation", False)
    profile.setdefault("region", None)
    profile.setdefault("startup_date", None)


def _blank_individual_only_fields(profile: dict):
    for key in ("is_disabled", "is_60_plus", "is_career_break_woman", "is_foreigner", "no_house"):
        profile.setdefault(key, False if key != "no_house" else None)
    profile.setdefault("annual_salary_10k", None)


def ask_region() -> str:
    region = ask_choice(
        "거주/사업장 지역을 선택하세요.",
        {
            "1": "수도권과밀억제권역 (서울 대부분, 인천 일부, 성남·안양·부천 등)",
            "2": "수도권(과밀억제권역·인구감소지역 제외)",
            "3": "수도권 인구감소지역",
            "4": "수도권 외 지역",
        },
    )
    return {"1": "seoul_dense", "2": "seoul_other", "3": "seoul_decline", "4": "nonseoul"}[region]


def ask_business_common_block(profile: dict, is_corp: bool):
    """개인사업자·법인 공통 질문(지역/규모/이전/특구/고용)."""
    profile["region"] = ask_region()

    startup = ask("\n사업 개시(법인 설립)일자를 입력하세요 (YYYY-MM-DD, 모르면 공백): ")
    profile["startup_date"] = startup or None

    size_choice = ask_choice(
        "\n기업 규모를 선택하세요.",
        {"1": "중소기업", "2": "중견기업", "3": "대기업", "4": "모름"},
    )
    profile["company_size"] = {"1": "중소기업", "2": "중견기업", "3": "대기업", "4": None}[size_choice]

    reloc_choice = ask_choice(
        "\n공장·본사를 수도권 밖(또는 지방)으로 이전했거나 이전할 계획이 있나요?",
        {"1": "공장만", "2": "본사만", "3": "공장과 본사 둘 다", "4": "해당 없음"},
    )
    profile["relocation_type"] = {"1": "공장", "2": "본사", "3": "둘다", "4": None}[reloc_choice]

    profile["is_public_agency_relocation"] = False
    if is_corp:
        profile["is_public_agency_relocation"] = ask_yn(
            "「혁신도시 조성 및 발전에 관한 특별법」상 이전공공기관에 해당하나요?", default=False
        )

    zone_choice = ask_zone()
    zone_map = {
        "1": "연구개발특구", "2": "제주첨단과학기술단지", "3": "제주투자진흥지구",
        "4": "기업도시등", "5": "기회발전특구", "6": "농공단지",
        "7": "위기지역", "8": "해당없음",
    }
    profile["zone_type"] = zone_map[zone_choice]
    if profile["zone_type"] == "농공단지":
        sub = ask_choice("   농공단지와 중소기업특별지원지역 중 무엇인가요?", {"1": "농공단지", "2": "중소기업특별지원지역"})
        profile["zone_type"] = "농공단지" if sub == "1" else "중소기업특별지원지역"

    profile["employment_increased"] = ask_yn("\n전년 대비 상시근로자 수가 늘었나요?", default=False)
    profile["wage_increased"] = ask_yn("상시근로자 평균임금 증가율이 최근 3년 평균보다 높나요?", default=False)


def collect_individual() -> dict:
    print("\n=== 개인(근로소득자) 질문 ===")
    profile = {"is_employee": True, "is_business_owner": False, "is_corp": False}

    age = ask_int("나이(만 나이)를 입력하세요")
    profile["age"] = age

    is_youth_default = age is not None and age <= 34
    print("※ 만 34세 이하는 조특법상 '청년' 관련 특례 후보로 우선 표시합니다 "
          "(세부 청년 기준은 조문별로 다를 수 있어 확인 필요로 분류됩니다).")
    profile["is_youth"] = ask_yn("청년 취업 지원 특례 대상으로 보고 싶으신가요?", default=is_youth_default)
    profile["is_disabled"] = ask_yn("장애인에 해당하나요?", default=False)
    profile["is_60_plus"] = age is not None and age >= 60
    profile["is_career_break_woman"] = ask_yn("경력단절 여성에 해당하나요?", default=False)
    profile["is_foreigner"] = ask_yn("외국인/재외 내국인 특례(외국인기술자, 해외 우수인력 복귀 등)에 관심 있으신가요?", default=False)

    profile["annual_salary_10k"] = ask_int("\n연간 총급여액(만원 단위, 모르면 공백)", allow_blank=True)

    no_house_ans = ask_choice(
        "\n무주택 세대주(또는 세대원)에 해당하나요?",
        {"1": "예", "2": "아니오", "3": "모름/공백"},
    )
    profile["no_house"] = {"1": True, "2": False, "3": None}[no_house_ans]

    profile["married_this_year"] = ask_yn("\n올해 혼인신고를 하셨나요?", default=False)

    _blank_business_fields(profile)
    return profile


def collect_business_owner() -> dict:
    print("\n=== 개인사업자 질문 ===")
    profile = {"is_employee": False, "is_business_owner": True, "is_corp": False}

    age = ask_int("나이(만 나이)를 입력하세요")
    profile["age"] = age
    is_youth_default = age is not None and age <= 34
    print("※ 만 34세 이하는 조특법상 '청년' 관련 특례(청년창업중소기업 등) 후보로 우선 표시합니다.")
    profile["is_youth"] = ask_yn("청년 창업 특례 대상으로 보고 싶으신가요?", default=is_youth_default)

    profile["married_this_year"] = ask_yn("\n올해 혼인신고를 하셨나요?", default=False)

    ask_business_common_block(profile, is_corp=False)

    _blank_individual_only_fields(profile)
    return profile


def collect_corp() -> dict:
    print("\n=== 법인 질문 ===")
    profile = {"is_employee": False, "is_business_owner": False, "is_corp": True, "age": None,
               "married_this_year": False}

    profile["is_youth"] = ask_yn("대표자가 청년(만 34세 이하 등)에 해당하는 '청년창업'으로 보고 싶으신가요?", default=False)

    ask_business_common_block(profile, is_corp=True)

    _blank_individual_only_fields(profile)
    return profile


def collect_profile() -> dict:
    print("=== 조세특례제한법 개인·법인 특례 매칭 ===\n")
    branch = ask_choice(
        "먼저 큰 갈래를 선택하세요.",
        {
            "1": "개인 (근로소득자)",
            "2": "개인사업자",
            "3": "법인",
        },
    )
    if branch == "1":
        return collect_individual()
    if branch == "2":
        return collect_business_owner()
    return collect_corp()


def print_results(results: list[dict]):
    print("\n" + "=" * 70)
    print(f"매칭 결과: {len(results)}건")
    print("=" * 70)

    if not results:
        print("입력하신 조건으로 매칭되는 특례가 없습니다 (1차 버전 수록 범위 내에서).")
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r['조번호']} {r['특례명']}  — {r['상태']}")
        if r["감면율"]:
            print(f"    감면율/공제율 : {r['감면율']}")
        if r["한도금액"]:
            print(f"    한도금액       : {r['한도금액']}")
        if r["적용기한"]:
            print(f"    적용기한       : {r['적용기한']}")
        if r["확인사항"]:
            print(f"    확인사항       : {r['확인사항']}")

    print("\n" + "-" * 70)
    print(DISCLAIMER)
    print("-" * 70)


def offer_article_lookup():
    if cache_is_empty():
        print("\n(조문 원문 캐시가 비어 있습니다. python refresh_cache.py 실행 후 원문 조회가 가능합니다.)")
        return
    while True:
        raw = ask("\n원문을 확인하고 싶은 조번호를 입력하세요 (예: 30 또는 91-18, 종료는 Enter): ")
        if not raw:
            return
        if "-" in raw:
            no, branch = raw.split("-", 1)
        else:
            no, branch = raw, ""
        article = get_article(no.strip(), branch.strip())
        if not article:
            print("  해당 조문을 캐시에서 찾을 수 없습니다.")
            continue
        print(f"\n--- 제{no}조" + (f"의{branch}" if branch else "") + f" {article.get('조문제목', '')} ---")
        print(article.get("조문내용", ""))
        for hang in article.get("항", []):
            print(hang.get("항내용", ""))


def main():
    profile = collect_profile()
    results = match(profile)
    print_results(results)
    offer_article_lookup()


if __name__ == "__main__":
    main()
