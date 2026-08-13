"""
DART OpenAPI를 이용해 전체 상장기업의 외부감사인(회계법인) 정보를 수집하고,
4대회계법인(삼일PwC/삼정KPMG/한영EY/안진Deloitte)별 감사 대상 기업 현황을 정리한다.
"""
import io
import json
import os
import time
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
CORPCODE_PATH = os.path.join(BASE_DIR, "CORPCODE.xml")
RAW_OUT_PATH = os.path.join(BASE_DIR, "auditor_raw_results.json")

BSNS_YEAR = "2025"
REPRT_CODE = "11011"  # 사업보고서(연간)
FALLBACK_YEAR = "2024"

BIG4_MAP = {
    "삼일회계법인": "삼일PwC",
    "삼정회계법인": "삼정KPMG",
    "한영회계법인": "한영EY",
    "안진회계법인": "안진Deloitte",
}

MARKET_MAP = {"Y": "코스피", "K": "코스닥", "N": "코넥스", "E": "기타"}


def load_api_key():
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            if line.startswith("DART_API_KEY="):
                return line.strip().split("=", 1)[1]
    raise RuntimeError("DART_API_KEY not found in .env")


def ensure_corpcode(api_key):
    if os.path.exists(CORPCODE_PATH):
        return
    r = requests.get(
        "https://opendart.fss.or.kr/api/corpCode.xml",
        params={"crtfc_key": api_key},
        timeout=30,
    )
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(BASE_DIR)


def load_listed_companies():
    tree = ET.parse(CORPCODE_PATH)
    root = tree.getroot()
    listed = []
    for corp in root.findall("list"):
        stock_code = (corp.findtext("stock_code") or "").strip()
        if stock_code:
            listed.append(
                {
                    "corp_code": corp.findtext("corp_code").strip(),
                    "corp_name": corp.findtext("corp_name").strip(),
                    "stock_code": stock_code,
                }
            )
    return listed


def fetch_auditor(session, api_key, corp_code, bsns_year, reprt_code=REPRT_CODE):
    url = "https://opendart.fss.or.kr/api/accnutAdtorNmNdAdtOpinion.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
    }
    for attempt in range(3):
        try:
            r = session.get(url, params=params, timeout=20)
            data = r.json()
            return data
        except (requests.RequestException, json.JSONDecodeError):
            time.sleep(0.5 * (attempt + 1))
    return {"status": "ERR", "message": "request failed after retries"}


def pick_current_year_row(items):
    """당기(현재 사업연도) 행만 골라 첫 건 반환. 없으면 첫 행 반환."""
    for item in items:
        if "당기" in item.get("bsns_year", ""):
            return item
    return items[0] if items else None


def process_company(session, api_key, company):
    corp_code = company["corp_code"]
    data = fetch_auditor(session, api_key, corp_code, BSNS_YEAR)

    used_year = BSNS_YEAR
    if data.get("status") != "000":
        # 최신 연도 사업보고서가 아직 없는 경우 전년도로 재시도
        data = fetch_auditor(session, api_key, corp_code, FALLBACK_YEAR)
        used_year = FALLBACK_YEAR

    result = {
        "corp_code": corp_code,
        "corp_name": company["corp_name"],
        "stock_code": company["stock_code"],
        "status": data.get("status"),
        "queried_year": used_year,
        "market": None,
        "adtor": None,
        "adt_opinion": None,
        "bsns_year_label": None,
        "stlm_dt": None,
    }

    if data.get("status") == "000":
        row = pick_current_year_row(data.get("list", []))
        if row:
            result["market"] = MARKET_MAP.get(row.get("corp_cls"), row.get("corp_cls"))
            result["adtor"] = row.get("adtor")
            result["adt_opinion"] = row.get("adt_opinion")
            result["bsns_year_label"] = row.get("bsns_year", "").replace("\n", " ")
            result["stlm_dt"] = row.get("stlm_dt")

    return result


def main():
    api_key = load_api_key()
    ensure_corpcode(api_key)
    companies = load_listed_companies()
    print(f"대상 상장기업 수: {len(companies)}")

    results = []
    if os.path.exists(RAW_OUT_PATH):
        with open(RAW_OUT_PATH, encoding="utf-8") as f:
            results = json.load(f)
        done_codes = {r["corp_code"] for r in results}
        companies = [c for c in companies if c["corp_code"] not in done_codes]
        print(f"이미 수집됨: {len(done_codes)}건, 남은 대상: {len(companies)}건")

    if not companies:
        print("모든 기업 수집 완료 상태.")
        return

    session = requests.Session()
    stop_flag = {"stop": False}

    def save():
        with open(RAW_OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(process_company, session, api_key, c): c for c in companies
        }
        count = 0
        for fut in as_completed(futures):
            if stop_flag["stop"]:
                break
            res = fut.result()
            results.append(res)
            count += 1
            if res.get("status") == "020":
                print("사용한도 초과(020) 발생 - 중단합니다.")
                stop_flag["stop"] = True
            if count % 200 == 0:
                print(f"진행: {count}/{len(companies)}")
                save()

    save()
    print(f"완료. 총 수집: {len(results)}건. 저장 위치: {RAW_OUT_PATH}")


if __name__ == "__main__":
    main()
