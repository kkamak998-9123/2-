LIFE_STAGES = {
    "001": "영유아",
    "002": "아동",
    "003": "청소년",
    "004": "청년",
    "005": "중장년",
    "006": "노년",
    "007": "임신·출산",
}

HOUSEHOLD_SITUATIONS = {
    "010": "다문화·탈북민",
    "020": "다자녀",
    "030": "보훈대상자",
    "040": "장애인",
    "050": "저소득",
    "060": "한부모·조손",
}

INTEREST_THEMES = {
    "010": "신체건강",
    "020": "정신건강",
    "030": "생활지원",
    "040": "주거",
    "050": "일자리",
    "060": "문화·여가",
    "070": "안전·위기",
    "080": "임신·출산",
    "090": "보육",
    "100": "교육",
    "110": "입양·위탁",
    "120": "보호·돌봄",
    "130": "서민금융",
    "140": "법률",
    "150": "관계개선",
    "160": "에너지",
}


def matches_life_stage(serv_life_array: str, stage_code: str) -> bool:
    """비어있는 lifeArray는 전 생애 대상으로 간주해 통과시키고,
    다른 생애주기만 명시된 항목은 걸러낸다."""
    if not serv_life_array:
        return True
    label = LIFE_STAGES.get(stage_code)
    return label in serv_life_array if label else True


def life_stage_from_age(age: int) -> str:
    if age <= 6:
        return "001"
    if age <= 12:
        return "002"
    if age <= 18:
        return "003"
    if age <= 34:
        return "004"
    if age <= 64:
        return "005"
    return "006"
