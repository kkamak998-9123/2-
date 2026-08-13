"""국가법령정보센터 Open API 클라이언트 (조세특례제한법 조회)."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OC = os.environ.get("LAW_API_KEY")
SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"
SERVICE_URL = "http://www.law.go.kr/DRF/lawService.do"

LAW_NAME = "조세특례제한법"


def _require_key():
    if not OC:
        raise RuntimeError(".env에 LAW_API_KEY가 설정되어 있지 않습니다.")


def search_law(query: str = LAW_NAME) -> dict:
    """법령명으로 검색해 법령일련번호(MST) 등 메타정보를 반환."""
    _require_key()
    params = {"OC": OC, "target": "law", "type": "JSON", "query": query}
    res = requests.get(SEARCH_URL, params=params, timeout=15)
    res.raise_for_status()
    return res.json()


def get_law_mst(query: str = LAW_NAME) -> str:
    """검색 결과에서 '현행' 법령의 MST(법령일련번호)를 반환."""
    data = search_law(query)
    laws = data.get("LawSearch", {}).get("law", [])
    if isinstance(laws, dict):
        laws = [laws]
    for law in laws:
        if law.get("법령명한글") == query and law.get("현행연혁코드") == "현행":
            return law["법령일련번호"]
    if laws:
        return laws[0]["법령일련번호"]
    raise RuntimeError(f"'{query}' 검색 결과가 없습니다.")


def fetch_law_content(mst: str) -> dict:
    """MST로 법령 본문 전체(조문 포함)를 조회."""
    _require_key()
    params = {"OC": OC, "target": "law", "type": "JSON", "MST": mst}
    res = requests.get(SERVICE_URL, params=params, timeout=30)
    res.raise_for_status()
    return res.json()


def fetch_articles(query: str = LAW_NAME) -> list[dict]:
    """법령명으로 검색 → 본문 조회 → 조문단위 리스트 반환."""
    mst = get_law_mst(query)
    data = fetch_law_content(mst)
    return data["법령"]["조문"]["조문단위"], mst
