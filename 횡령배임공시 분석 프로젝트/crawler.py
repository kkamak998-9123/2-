# -*- coding: utf-8 -*-
"""
KIND(kind.krx.co.kr) '횡령 등' 투자유의사항 공시 크롤링 파이프라인

1. 목록 페이지에서 번호(row_no) 범위에 해당하는 공시 항목을 수집
2. 각 공시의 접수번호(acptno) -> 문서번호(docNo) -> 실제 문서 경로 순으로 추적하여 본문을 가져옴
3. 본문 텍스트에서 핵심 항목(사고내용/금액/자기자본대비/사고발생일 등)을 파싱
4. 회사명 기준으로 그룹핑하고, 각 회사의 공시를 시간순 정렬하여 요약/분류
"""

import re
import sys
import time
import json
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE = "https://kind.krx.co.kr"
LIST_URL = f"{BASE}/investwarn/investattentEmbezzlement.do"
VIEWER_URL = f"{BASE}/common/disclsviewer.do"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)

TAKE_LATEST = 111
SLEEP_SEC = 0.35


def fetch_list_rows(take_latest: int) -> list[dict]:
    """목록 전체를 한 번에 받아서 가장 최신 take_latest건을 추출 (최신순)."""
    resp = requests.post(
        LIST_URL,
        headers={**HEADERS, "Referer": f"{LIST_URL}?method=searchInvestAttentEmbezzlementMain"},
        data={
            "method": "searchInvestAttentEmbezzlementSub",
            "forward": "investattentEmbezzlement_sub",
            "currentPageSize": "2000",
            "pageIndex": "1",
            "marketType": "",
            "searchCorpName": "",
            "searchCorpNameTmp": "",
            "fromDate": "",
            "toDate": "",
            "repIsuSrtCd": "",
            "isurCd": "",
        },
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    rows = []
    for tr in soup.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        no_text = tds[0].get_text(strip=True)
        if not no_text.isdigit():
            continue
        row_no = int(no_text)

        date_text = tds[1].get_text(strip=True)

        company_a = tds[2].find("a", id="companysum")
        company_name = company_a.get_text(strip=True) if company_a else tds[2].get_text(strip=True)
        stock_code = ""
        if company_a and company_a.get("onclick"):
            m = re.search(r"companysummary_open\('([^']+)'\)", company_a["onclick"])
            if m:
                stock_code = m.group(1)

        market = ""
        img = tds[2].find("img")
        if img and img.get("alt"):
            market = img["alt"]

        title_a = tds[3].find("a")
        title = title_a.get_text(strip=True) if title_a else tds[3].get_text(strip=True)
        acptno = ""
        if title_a and title_a.get("onclick"):
            m = re.search(r"openDisclsViewer\('([^']+)'", title_a["onclick"])
            if m:
                acptno = m.group(1)

        rows.append({
            "row_no": row_no,
            "date": date_text,
            "company": company_name,
            "stock_code": stock_code,
            "market": market,
            "title": title,
            "acptno": acptno,
        })

    rows.sort(key=lambda r: r["row_no"], reverse=True)
    return rows[:take_latest]


def resolve_doc_url(acptno: str) -> tuple[str, str]:
    """acptno -> (docNo, 실제 문서 URL) 을 3단계로 추적."""
    resp = requests.get(
        VIEWER_URL,
        params={"method": "search", "acptno": acptno, "docno": "", "viewerhost": "", "viewerport": ""},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    option = soup.select_one("#mainDoc option[selected]") or soup.select_one("#mainDoc option[value]:not([value=''])")
    if not option or not option.get("value"):
        return "", ""
    doc_no = option["value"].split("|")[0]

    resp2 = requests.post(
        VIEWER_URL,
        headers={**HEADERS, "Referer": f"{VIEWER_URL}?method=search&acptno={acptno}"},
        data={"method": "searchContents", "docNo": doc_no},
        timeout=30,
    )
    resp2.raise_for_status()
    m = re.search(r"parent\.setPath\('([^']*)',\s*'([^']*)'", resp2.text)
    if not m:
        return doc_no, ""
    doc_url = m.group(2)
    return doc_no, doc_url


FIELD_LABELS = [
    "사고발생내용", "발생금액(원)", "자기자본(원)", "자기자본대비(%)", "대기업해당여부",
    "향후대책", "사고발생일자", "확인일자", "기타 투자판단에 참고할 사항",
]


def parse_doc(doc_url: str) -> dict:
    """공시 본문 문서에서 표를 key-value로 파싱. 표준 서식이 아니면 전체 텍스트만 반환."""
    resp = requests.get(doc_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    full_text = soup.get_text(separator="\n", strip=True)

    fields = {}
    for tr in soup.select("table tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        label = tds[0].get_text(strip=True)
        value = tds[-1].get_text(" ", strip=True)
        if label:
            fields[label] = value

    return {"full_text": full_text, "fields": fields}


AMOUNT_RE = re.compile(r"([\d,]{4,})")
PCT_RE = re.compile(r"([\d.]+)\s*%?")


def classify(row: dict, parsed: dict) -> dict:
    title = row["title"]
    text = parsed.get("full_text", "")
    fields = parsed.get("fields", {})

    if "횡령" in title and "배임" in title:
        crime_type = "횡령·배임"
    elif "횡령" in title:
        crime_type = "횡령"
    elif "배임" in title:
        crime_type = "배임"
    elif "유용" in title:
        crime_type = "자금유용"
    elif "조회공시" in title:
        crime_type = "조회공시(풍문/보도 답변)"
    elif "관리종목" in title or "실질심사" in title:
        crime_type = "후속 시장조치(관리종목/실질심사 등)"
    else:
        crime_type = "기타"

    status = "미확정" if ("미확정" in title or "미확정" in text) else (
        "확정" if ("확정" in title) else "")

    pct_val = None
    pct_raw = fields.get("자기자본대비(%)", "")
    if pct_raw:
        m = PCT_RE.search(pct_raw)
        if m:
            try:
                pct_val = float(m.group(1))
            except ValueError:
                pct_val = None

    if pct_val is None:
        severity = ""
    elif pct_val < 5:
        severity = "경미(<5%)"
    elif pct_val < 20:
        severity = "중대(5~20%)"
    else:
        severity = "심각(>=20%)"

    return {
        "crime_type": crime_type,
        "status": status,
        "amount": fields.get("발생금액(원)", ""),
        "equity": fields.get("자기자본(원)", ""),
        "equity_pct": pct_raw,
        "severity": severity,
        "accident_date": fields.get("사고발생일자", ""),
        "confirm_date": fields.get("확인일자", ""),
        "accident_content": fields.get("사고발생내용", ""),
        "future_plan": fields.get("향후대책", ""),
        "note": fields.get("기타 투자판단에 참고할 사항", ""),
    }


def main():
    print(f"[1/3] 목록 수집 중... (최신 {TAKE_LATEST}건)")
    rows = fetch_list_rows(TAKE_LATEST)
    print(f"  -> {len(rows)}건 수집됨 (범위: {rows[-1]['date']} ~ {rows[0]['date']})")

    results = []
    for i, row in enumerate(rows, 1):
        print(f"[2/3] ({i}/{len(rows)}) 번호 {row['row_no']} - {row['company']} - {row['title']}")
        rec = dict(row)
        if not row["acptno"]:
            rec["parse_error"] = "acptno 없음"
            results.append(rec)
            continue
        try:
            doc_no, doc_url = resolve_doc_url(row["acptno"])
            rec["doc_no"] = doc_no
            rec["doc_url"] = doc_url
            if doc_url:
                parsed = parse_doc(doc_url)
                rec.update(classify(row, parsed))
                rec["full_text"] = parsed["full_text"]
            else:
                rec["parse_error"] = "문서 URL 확인 실패"
        except Exception as e:
            rec["parse_error"] = str(e)
        results.append(rec)
        time.sleep(SLEEP_SEC)

    print("[3/3] 저장 중...")
    df = pd.DataFrame(results)
    df.to_csv(OUT_DIR / "raw_disclosures.csv", index=False, encoding="utf-8-sig")
    df.to_excel(OUT_DIR / "raw_disclosures.xlsx", index=False)
    with open(OUT_DIR / "raw_disclosures.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"완료: {len(results)}건 -> {OUT_DIR}")


if __name__ == "__main__":
    main()
