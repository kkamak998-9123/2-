"""공용 유틸 함수: 숫자 표시 포맷, 재무제표 컬럼 파싱 등"""


def 연도_라벨(col) -> str:
    """dart_fss가 반환하는 컬럼 라벨에서 연도(앞 4자리)를 뽑아낸다.

    컬럼은 'label_ko' 같은 단순 문자열이거나, 재무제표에 연결/별도 등
    보고서 종류가 함께 존재할 때 ('20181231', ('연결재무제표',)) 같은
    튜플 형태로 들어온다. 둘 다 지원한다.
    """
    date_part = col[0] if isinstance(col, tuple) else col
    return str(date_part)[:4]


def 연결여부(col) -> bool:
    """컬럼 라벨의 보고서 구분에 '연결'이 포함되는지 여부"""
    if not isinstance(col, tuple) or len(col) < 2:
        return False
    구분 = col[1]
    if isinstance(구분, tuple):
        구분 = 구분[0] if 구분 else ""
    return "연결" in str(구분)


def 숫자줄이기(amount) -> str:
    """큰 금액을 '조'/'억' 단위 문자열로 변환 (소수점 2자리)"""
    amount = float(amount)
    if abs(amount) >= 1_000_000_000_000:
        return f"{amount / 1_000_000_000_000:.2f}조"
    elif abs(amount) >= 100_000_000:
        return f"{amount / 100_000_000:.2f}억"
    else:
        return f"{amount:,.2f}"


def 입력받기_숫자(prompt: str, min_value: int, max_value: int):
    """min_value~max_value 범위의 정수를 받을 때까지 재입력을 요구한다."""
    while True:
        raw = input(prompt).strip()
        if not raw.isdigit():
            print("❌ 숫자를 입력해주세요.")
            continue
        value = int(raw)
        if value < min_value or value > max_value:
            print(f"❌ {min_value}~{max_value} 범위의 번호를 입력해주세요.")
            continue
        return value


def 입력받기_예아니오(prompt: str) -> bool:
    while True:
        raw = input(f"{prompt} (y/n): ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("❌ y 또는 n으로 입력해주세요.")
