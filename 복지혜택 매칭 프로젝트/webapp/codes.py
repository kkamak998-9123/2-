# -*- coding: utf-8 -*-
"""복지서비스 분류 코드/이름 및 생애주기 매핑.

API 목록 응답의 lifeArray/themaArray/trgterArray는 코드가 아니라 한글 이름
CSV(예: "영유아,아동,청소년")로 오므로, 웹앱 필터도 이름 기준으로 매칭한다.
"""

# 생애주기(나이 → 이름). API가 실제로 쓰는 이름과 일치해야 한다.
LIFE_STAGES = ["영유아", "아동", "청소년", "청년", "중장년", "노년"]

# 관심주제 16종 (API 이름 그대로)
INTEREST_THEMES = [
    "신체건강", "정신건강", "생활지원", "주거", "일자리", "문화·여가",
    "안전·위기", "임신·출산", "보육", "교육", "입양·위탁", "보호·돌봄",
    "서민금융", "법률", "관계개선", "에너지",
]

# 가구상황 6종 (API 이름 그대로)
HOUSEHOLD_SITUATIONS = [
    "다문화·탈북민", "다자녀", "보훈대상자", "장애인", "저소득", "한부모·조손",
]


def life_stage_from_age(age: int) -> str:
    if age <= 6:
        return "영유아"
    if age <= 12:
        return "아동"
    if age <= 18:
        return "청소년"
    if age <= 34:
        return "청년"
    if age <= 64:
        return "중장년"
    return "노년"
