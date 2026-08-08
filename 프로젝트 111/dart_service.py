"""DART 회사 검색, 재무제표 추출/가공 담당 모듈"""

import os

import dart_fss as dart

API_KEY = os.environ.get("DART_API_KEY")
if not API_KEY:
    raise RuntimeError("DART_API_KEY 환경변수를 설정해주세요.")
dart.set_api_key(api_key=API_KEY)

# 각 재무제표 종류의 연도 컬럼 패턴 (필요 시 년도 필터에 사용)
IS_LIKE_YEAR_PATTERN = r"label_ko|\d{8}-\d{8}"  # 손익계산서/현금흐름표: 기간
BS_YEAR_PATTERN = r"label_ko|\d{8}"  # 재무상태표: 시점


class 재무데이터없음(Exception):
    pass


def 회사목록_가져오기():
    print("⏳ DART 상장사 리스트를 불러오는 중...")
    목록 = dart.get_corp_list()
    print("✅ 완료\n")
    return 목록


def 회사이름찾기(회사목록):
    """대화형으로 회사를 검색해 corp 객체를 반환. 못 찾으면 None."""
    while True:
        이름입력 = input("회사명 입력 (취소: 빈 입력): ").strip()
        if not 이름입력:
            return None

        후보 = 회사목록.find_by_corp_name(이름입력, exactly=False, market="YK")
        if not 후보:
            print("❌ 회사를 찾을 수 없습니다. 다시 입력해 주세요.\n")
            continue

        if len(후보) > 1:
            print(f"검색된 기업 {len(후보)}개. 정확한 사명을 입력해주세요.")
            for c in 후보:
                print(f"  - {c.corp_name}")
            정확한이름 = input("정확한 회사명 (취소: 빈 입력): ").strip()
            if not 정확한이름:
                return None
            정확후보 = 회사목록.find_by_corp_name(정확한이름, exactly=True, market="YKNE")
            if not 정확후보:
                print("❌ 일치하는 회사가 없습니다. 처음부터 다시 검색합니다.\n")
                continue
            회사 = 정확후보[0]
        else:
            회사 = 후보[0]

        print(f"--- [{회사.corp_name}] 선택됨 ---\n")
        return 회사


def 재무제표추출(회사, bgn_de="20210101", end_de="20261231"):
    print(f"⏳ [{회사.corp_name}] 재무제표 추출 중...")
    재무제표 = dart.fs.extract(corp_code=회사.corp_code, bgn_de=bgn_de, end_de=end_de)
    print("✅ 재무제표 추출 완료\n")
    return 재무제표


def _통합조회(재무제표, keys, 에러메시지):
    for key in keys:
        table = 재무제표[key]
        if table is not None:
            return table
    raise 재무데이터없음(에러메시지)


def 손익계산서_가공(재무제표):
    표 = _통합조회(재무제표, ["is", "cis"], "손익계산서/포괄손익계산서 항목이 없습니다.")
    return 표.filter(regex=IS_LIKE_YEAR_PATTERN)


def 재무상태표_가공(재무제표):
    표 = _통합조회(재무제표, ["bs"], "재무상태표 항목이 없습니다.")
    return 표.filter(regex=BS_YEAR_PATTERN)


def 현금흐름표_가공(재무제표):
    표 = _통합조회(재무제표, ["cf", "ccf"], "현금흐름표/연결현금흐름표 항목이 없습니다.")
    return 표.filter(regex=IS_LIKE_YEAR_PATTERN)
