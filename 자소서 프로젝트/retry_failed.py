"""
auditor_raw_results.json에서 status == 'ERR' 인 항목 + 아직 조회 안 된 기업을
동시성 없이 하나씩 순차적으로 재수집한다.
매 저장 시 항상 "전체 상장기업" 기준 완전한 결과셋을 기록해 중단되어도 데이터가 사라지지 않는다.
"""
import json
import os
import time

import requests

import collect_auditors as ca

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_PATH = os.path.join(BASE_DIR, "auditor_raw_results.json")
DELAY_SEC = 0.3


def main():
    api_key = ca.load_api_key()
    all_companies = ca.load_listed_companies()  # 전체 3977개 (corp_code, corp_name, stock_code)

    results_by_code = {}
    if os.path.exists(RAW_PATH):
        with open(RAW_PATH, encoding="utf-8") as f:
            for r in json.load(f):
                results_by_code[r["corp_code"]] = r

    def save():
        with open(RAW_PATH, "w", encoding="utf-8") as f:
            json.dump(list(results_by_code.values()), f, ensure_ascii=False, indent=2)

    targets = [
        c
        for c in all_companies
        if results_by_code.get(c["corp_code"], {}).get("status") in (None, "ERR")
    ]
    print(f"전체 상장기업: {len(all_companies)}건, 재시도/신규 대상: {len(targets)}건")

    session = requests.Session()

    for i, company in enumerate(targets, 1):
        new_r = ca.process_company(session, api_key, company)
        results_by_code[company["corp_code"]] = new_r

        if i % 50 == 0 or i == len(targets):
            print(f"진행: {i}/{len(targets)}  (마지막 status={new_r['status']}, {new_r['corp_name']})")
            save()

        if new_r.get("status") == "020":
            print("사용한도 초과(020) - 중단")
            break

        time.sleep(DELAY_SEC)

    save()

    from collections import Counter

    statuses = Counter(r["status"] for r in results_by_code.values())
    print("최종 결과 총", len(results_by_code), "건. 상태 분포:", dict(statuses))


if __name__ == "__main__":
    main()
