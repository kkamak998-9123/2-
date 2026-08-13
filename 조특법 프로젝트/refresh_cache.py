"""조세특례제한법 전체 조문을 API에서 받아 로컬 캐시(sqlite)를 갱신한다.

사용법: python refresh_cache.py
"""
from law_api import fetch_articles
from db import save_articles


def main():
    print("국가법령정보센터에서 조세특례제한법 조문을 가져오는 중...")
    items, mst = fetch_articles()
    save_articles(items, mst)
    print(f"완료: {len(items)}개 조문 항목을 캐시에 저장했습니다. (법령일련번호={mst})")


if __name__ == "__main__":
    main()
