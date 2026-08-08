"""DART 재무제표 시각화 + 업종별 재무비율 분석 CLI

SPEC.md 기준 구현. 회사를 검색하면
  1) 원본 재무제표 지표를 그래프로 확인하거나
  2) 업종을 자동 판별해 추천 재무비율을 계정 매핑 후 계산/시각화할 수 있다.
"""

import dart_service
import ratios
from charting import 연도프레임_만들기, 지표_그래프, 비율_그래프
from industry import 업종분류기
from utils import 입력받기_예아니오


def _항목목록_출력(df, 제목):
    all_rows = df.iloc[:, 0].tolist()
    print(f"\n📊 {제목} 계정 목록:")
    for idx, row in enumerate(all_rows, 1):
        print(f"  {idx}. {row}")
    return all_rows


def _다중선택(all_rows):
    """쉼표로 구분된 여러 번호를 유효할 때까지 재입력받아 항목명 리스트로 반환. 빈 입력이면 None."""
    while True:
        raw = input("\n분석할 지표 번호를 입력하세요 (예: 1,3,5 / 취소: 빈 입력): ").strip()
        if not raw:
            return None
        try:
            idxs = [int(x.strip()) - 1 for x in raw.split(",")]
            if any(i < 0 or i >= len(all_rows) for i in idxs):
                raise ValueError
        except ValueError:
            print("❌ 잘못된 입력입니다. 목록에 있는 번호만 쉼표로 구분해 입력해주세요.")
            continue
        return [all_rows[i] for i in idxs]


def _단일선택(all_rows, prompt):
    """번호 하나를 유효할 때까지 재입력받아 항목명으로 반환. 0이면 건너뛰기(None)."""
    while True:
        raw = input(f"{prompt} (건너뛰기: 0): ").strip()
        if raw == "0":
            return None
        if not raw.isdigit():
            print("❌ 숫자를 입력해주세요.")
            continue
        idx = int(raw) - 1
        if idx < 0 or idx >= len(all_rows):
            print("❌ 목록에 있는 번호를 입력해주세요.")
            continue
        return all_rows[idx]


def 원본지표_그래프_플로우(회사, 재무데이터):
    print("\n📈 다음 중 하나를 선택하세요:")
    print("1. 손익계산서 (포괄손익계산서)")
    print("2. 재무상태표")
    print("3. 현금흐름표")
    print("4. 모두 보기")
    선택 = input("선택 (1-4): ").strip()

    표목록 = []
    if 선택 in ("1", "4") and 재무데이터.get("is") is not None:
        표목록.append(("손익계산서 주요 지표 추이", 재무데이터["is"]))
    if 선택 in ("2", "4") and 재무데이터.get("bs") is not None:
        표목록.append(("재무상태표 주요 지표 추이", 재무데이터["bs"]))
    if 선택 in ("3", "4") and 재무데이터.get("cf") is not None:
        표목록.append(("현금흐름표 주요 지표 추이", 재무데이터["cf"]))

    if not 표목록:
        print("❌ 선택 가능한 재무제표 데이터가 없습니다.")
        return

    for 제목, df in 표목록:
        all_rows = _항목목록_출력(df, 제목)
        선택항목 = _다중선택(all_rows)
        if not 선택항목:
            print("⏭️  선택을 건너뜁니다.")
            continue
        plot_df = 연도프레임_만들기(df, 선택항목)
        지표_그래프(plot_df, 제목, 회사.corp_name)


def 재무비율_분석_플로우(회사, 재무데이터, 대분류명, 세부업종명):
    print(f"\n🏢 업종 판별 결과: {세부업종명} (대분류: {대분류명 or '분류 실패'})")
    추천목록 = ratios.추천비율목록(대분류명 or "")

    print(f"\n📋 [{세부업종명}] 업종 추천 재무비율:")
    for 비율 in 추천목록:
        if 비율.계산가능:
            print(f"  - {비율.이름} = {비율.분자설명} / {비율.분모설명}")
        else:
            print(f"  - {비율.이름}: ⚠️ 계산 불가 — {비율.비고}")

    stmt_map = {"IS": 재무데이터.get("is"), "BS": 재무데이터.get("bs")}
    비율결과 = {}

    for 비율 in 추천목록:
        if not 비율.계산가능:
            continue

        분자df, 분모df = stmt_map.get(비율.분자출처), stmt_map.get(비율.분모출처)
        if 분자df is None or 분모df is None:
            print(f"\n⏭️  [{비율.이름}] 계산에 필요한 재무제표가 없어 건너뜁니다.")
            continue

        print(f"\n--- [{비율.이름}] = {비율.분자설명} / {비율.분모설명} ---")

        분자항목목록 = _항목목록_출력(분자df, f"{비율.이름} 분자 ({비율.분자설명})")
        분자항목 = _단일선택(분자항목목록, f"'{비율.분자설명}'에 해당하는 계정 번호")
        if 분자항목 is None:
            print("⏭️  건너뜁니다.")
            continue

        분모항목목록 = _항목목록_출력(분모df, f"{비율.이름} 분모 ({비율.분모설명})")
        분모항목 = _단일선택(분모항목목록, f"'{비율.분모설명}'에 해당하는 계정 번호")
        if 분모항목 is None:
            print("⏭️  건너뜁니다.")
            continue

        분자값 = ratios.항목별_연도값(분자df, 분자항목)
        분모값 = ratios.항목별_연도값(분모df, 분모항목)
        연도별비율 = ratios.비율계산(분자값, 분모값, 비율.단위)

        if not 연도별비율:
            print("❌ 두 항목의 공통 연도 데이터가 없어 계산할 수 없습니다.")
            continue

        print(f"  📅 연도별 {비율.이름}:")
        for 연도, 값 in sorted(연도별비율.items()):
            단위표시 = f"{값:.2f}%" if 비율.단위 == "%" else f"{값:.2f}배"
            print(f"     {연도}: {단위표시}")

        비율결과[f"{비율.이름} ({비율.단위})"] = 연도별비율

    if 비율결과 and 입력받기_예아니오("\n계산된 비율을 그래프로 볼까요?"):
        비율_그래프(비율결과, f"{세부업종명} 업종 추천 재무비율 추이", 회사.corp_name)


def 회사_분석(회사, 업종분류):
    try:
        원본재무제표 = dart_service.재무제표추출(회사)
    except Exception as e:
        print(f"❌ 재무제표 추출 실패: {e}")
        return

    재무데이터 = {}
    for key, 가공함수, 이름 in [
        ("is", dart_service.손익계산서_가공, "손익계산서"),
        ("bs", dart_service.재무상태표_가공, "재무상태표"),
        ("cf", dart_service.현금흐름표_가공, "현금흐름표"),
    ]:
        try:
            재무데이터[key] = 가공함수(원본재무제표)
        except dart_service.재무데이터없음 as e:
            print(f"⚠️ {이름}: {e}")
            재무데이터[key] = None

    대분류명, 세부업종명 = 업종분류.분류(getattr(회사, "sector", None))

    while True:
        print(f"\n{'=' * 50}")
        print(f"[{회사.corp_name}] 무엇을 하시겠어요?")
        print("1. 원본 재무제표 지표 그래프 보기")
        print("2. 업종별 추천 재무비율 분석")
        print("3. 다른 회사 검색")
        print("4. 종료")
        print("=" * 50)
        선택 = input("선택 (1-4): ").strip()

        if 선택 == "1":
            원본지표_그래프_플로우(회사, 재무데이터)
        elif 선택 == "2":
            재무비율_분석_플로우(회사, 재무데이터, 대분류명, 세부업종명)
        elif 선택 == "3":
            return "재검색"
        elif 선택 == "4":
            return "종료"
        else:
            print("❌ 1~4 중에서 선택해주세요.")


def 프로그램_실행():
    print("=" * 50)
    print("📊 DART 재무제표 인터랙티브 시각화 + 업종별 재무비율 분석 프로그램")
    print("=" * 50)

    회사목록 = dart_service.회사목록_가져오기()
    업종분류 = 업종분류기()

    while True:
        회사 = dart_service.회사이름찾기(회사목록)
        if 회사 is None:
            print("\n프로그램을 종료합니다.")
            return

        결과 = 회사_분석(회사, 업종분류)
        if 결과 == "종료":
            print("\n프로그램을 종료합니다.")
            return
        # "재검색"이거나 None(정상 종료 없이 빠져나온 경우)이면 바깥 루프에서 다시 회사 검색


if __name__ == "__main__":
    프로그램_실행()
