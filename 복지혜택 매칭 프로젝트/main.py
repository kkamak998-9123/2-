import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from codes import (
    HOUSEHOLD_SITUATIONS,
    INTEREST_THEMES,
    life_stage_from_age,
    matches_life_stage,
)
from welfare_api import (
    WelfareApiError,
    fetch_local_detail,
    fetch_local_list,
    fetch_national_detail,
    fetch_national_list,
)

DISCLAIMER = (
    "※ 이 결과는 법적 효력이 있는 복지 상담이 아닙니다. "
    "최종 신청 가능 여부는 관할 주민센터 또는 복지로(bokjiro.go.kr)에서 반드시 확인하세요."
)


def ask_age():
    while True:
        raw = input("나이를 입력하세요: ").strip()
        if raw.isdigit():
            return int(raw)
        print("숫자로 입력해주세요.")


def ask_region():
    ctpv = input("거주지 시/도를 입력하세요 (예: 서울특별시, 모르면 엔터): ").strip()
    if not ctpv:
        return None, None
    sgg = input("거주지 시/군/구를 입력하세요 (예: 종로구, 모르면 엔터): ").strip()
    return ctpv, sgg or None


def ask_multi_select(title, code_map):
    print(f"\n{title} (해당하는 번호를 콤마로 구분해 입력, 없으면 엔터)")
    items = list(code_map.items())
    for i, (code, name) in enumerate(items, start=1):
        print(f"  {i}. {name}")
    raw = input("선택: ").strip()
    if not raw:
        return []
    selected_codes = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit() and 1 <= int(token) <= len(items):
            selected_codes.append(items[int(token) - 1][0])
    return selected_codes


def ask_keyword():
    return input("\n찾고 싶은 키워드가 있으면 입력하세요 (없으면 엔터): ").strip()


DISPLAY_LIMIT = 30


def print_group(title, services):
    print(f"\n=== {title} ({len(services)}건) ===")
    if not services:
        print("  해당 조건에 맞는 서비스가 없습니다.")
        return
    for i, s in enumerate(services[:DISPLAY_LIMIT], start=1):
        print(f"\n  [{i}] {s['servNm']}  (servId: {s['servId']})")
        if s["jur"]:
            print(f"      소관: {s['jur']}")
        print(f"      요약: {s['servDgst']}")
        if s["servDtlLink"]:
            print(f"      링크: {s['servDtlLink']}")
    if len(services) > DISPLAY_LIMIT:
        print(f"\n  ... 외 {len(services) - DISPLAY_LIMIT}건 더 있습니다. 키워드나 관심주제로 좁혀보세요.")


def print_detail(detail):
    if not detail:
        print("  상세 정보를 찾을 수 없습니다.")
        return
    print(f"\n--- {detail['servNm']} 상세 ---")
    if detail.get("wlfareInfoOutlCn"):
        print(f"서비스 요약: {detail['wlfareInfoOutlCn']}")
    if detail.get("tgtrDtlCn"):
        print(f"\n[지원대상]\n{detail['tgtrDtlCn']}")
    if detail.get("slctCritCn"):
        print(f"\n[선정기준]\n{detail['slctCritCn']}")
    if detail.get("alwServCn"):
        print(f"\n[급여/지원내용]\n{detail['alwServCn']}")
    if detail.get("sprtCycNm"):
        print(f"\n지원주기: {detail['sprtCycNm']}")
    if detail.get("srvPvsnNm"):
        print(f"제공유형: {detail['srvPvsnNm']}")


def main():
    print("복지 혜택 매칭 CLI\n" + "=" * 40)

    age = ask_age()
    ctpv, sgg = ask_region()
    theme_codes = ask_multi_select("관심주제", INTEREST_THEMES)
    household_codes = ask_multi_select("가구상황(해당사항)", HOUSEHOLD_SITUATIONS)
    keyword = ask_keyword()

    life_stage = life_stage_from_age(age)
    theme_csv = ",".join(theme_codes) if theme_codes else None
    household_csv = ",".join(household_codes) if household_codes else None
    srch_key_code = "001" if keyword else "003"

    print("\n조회 중입니다...")

    # lifeArray는 서버 필터로 걸지 않는다 — 비어있는(전 생애 대상) 항목이
    # 통째로 빠지기 때문에, 넓게 받아온 뒤 아래에서 직접 걸러낸다.
    all_national = []
    try:
        all_national = fetch_national_list(
            trgter_indvdl_array=household_csv,
            intrs_thema_array=theme_csv,
            age=age,
            search_wrd=keyword,
            srch_key_code=srch_key_code,
            num_of_rows=500,
        )
        all_national = [
            s for s in all_national if matches_life_stage(s["lifeArray"], life_stage)
        ]
    except WelfareApiError as e:
        print(f"[중앙부처 API 오류] {e}")
    except Exception as e:
        print(f"[중앙부처 API 호출 실패] {e}")

    print_group("전국 공통 (중앙부처)", all_national)

    all_local = []
    if ctpv:
        try:
            all_local = fetch_local_list(
                ctpv_nm=ctpv,
                sgg_nm=sgg,
                trgter_indvdl_array=household_csv,
                intrs_thema_array=theme_csv,
                # 지자체 API는 age 파라미터를 보내면 무조건 0건을 반환한다(실측 확인,
                # 2026-08-12) — 생애주기는 national과 동일하게 클라이언트에서 걸러낸다.
                search_wrd=keyword,
                srch_key_code=srch_key_code,
                num_of_rows=500,
            )
            all_local = [
                s for s in all_local if matches_life_stage(s["lifeArray"], life_stage)
            ]
        except WelfareApiError as e:
            print(f"\n[지자체 API 오류] {e}")
        except Exception as e:
            print(f"\n[지자체 API 호출 실패] {e}")

        region_label = f"{ctpv} {sgg or ''}".strip()
        print_group(f"지역 ({region_label})", all_local)
    else:
        print("\n(거주지를 입력하지 않아 지자체 혜택은 조회하지 않았습니다)")

    print(f"\n{DISCLAIMER}")

    while True:
        choice = input(
            "\n상세 정보를 볼 서비스 ID(servId)를 입력하세요 (없으면 엔터로 종료): "
        ).strip()
        if not choice:
            break

        detail = None
        if any(s["servId"] == choice for s in all_national):
            try:
                detail = fetch_national_detail(choice)
            except WelfareApiError as e:
                print(f"[오류] {e}")
        elif any(s["servId"] == choice for s in all_local):
            try:
                detail = fetch_local_detail(choice)
            except WelfareApiError as e:
                print(f"[오류] {e}")
        else:
            print("목록에 없는 servId입니다.")
            continue

        print_detail(detail)


if __name__ == "__main__":
    main()
