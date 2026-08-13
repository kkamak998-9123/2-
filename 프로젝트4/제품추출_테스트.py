# -*- coding: utf-8 -*-
"""
사업보고서 원문에서 '주요 제품 및 서비스' 섹션 파싱 포맷 확인용 테스트
대상: 한화시스템(방산 A), 스페코(방산 B) - 등급이 다른 2개 기업으로 비교
"""

import requests
import zipfile
import io
import re
from bs4 import BeautifulSoup

API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"

test_companies = [
    ("한화시스템", "00339391"),
    ("스페코", "00136165"),
]

def get_latest_biz_report_rcept_no(corp_code):
    """사업보고서(A001) 최신 접수번호 조회"""
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        'crtfc_key': API_KEY,
        'corp_code': corp_code,
        'bgn_de': '20240101',
        'end_de': '20260712',
        'pblntf_detail_ty': 'A001',  # 사업보고서
        'page_no': 1,
        'page_count': 10,
    }
    res = requests.get(url, params=params, timeout=10)
    data = res.json()
    print(f"  [list.json status] {data.get('status')} {data.get('message')}")
    if data.get('status') != '000':
        return None, data
    items = data.get('list', [])
    for item in items:
        print(f"    - {item.get('rcept_no')} | {item.get('report_nm')} | {item.get('rcept_dt')}")
    return (items[0]['rcept_no'] if items else None), data

def get_document(rcept_no):
    """document.xml로 원문 zip 다운로드 후 첫 파일 텍스트 반환"""
    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {'crtfc_key': API_KEY, 'rcept_no': rcept_no}
    res = requests.get(url, params=params, timeout=30)

    content_type = res.headers.get('Content-Type', '')
    print(f"  [document.xml] status_code={res.status_code}, content-type={content_type}, size={len(res.content)}")

    if 'zip' not in content_type and not res.content[:2] == b'PK':
        # 에러 응답일 가능성 (JSON/XML 에러 메시지)
        print(f"  [경고] zip이 아닌 응답: {res.content[:300]}")
        return None

    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        names = zf.namelist()
        print(f"  [zip 내부 파일 목록] {names}")
        all_text = ""
        for name in names:
            raw = zf.read(name)
            # 인코딩은 euc-kr인 경우가 많음
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                text = raw.decode('euc-kr', errors='ignore')
            all_text += text
        return all_text

def find_product_section(html_text):
    """'주요 제품' 관련 키워드 주변 텍스트 추출"""
    soup = BeautifulSoup(html_text, 'html.parser')
    full_text = soup.get_text(separator='\n')

    keywords = ['주요 제품', '주요제품', '제품 및 서비스']
    hits = []
    for kw in keywords:
        for m in re.finditer(re.escape(kw), full_text):
            start = max(0, m.start() - 100)
            end = min(len(full_text), m.start() + 1500)
            hits.append((kw, m.start(), full_text[start:end]))
    return hits

if __name__ == "__main__":
    out_lines = []

    def log(s=""):
        print(s)
        out_lines.append(str(s))

    for name, corp_code in test_companies:
        log("=" * 80)
        log(f"{name} ({corp_code})")
        log("=" * 80)

        rcept_no, raw_list = get_latest_biz_report_rcept_no(corp_code)
        if not rcept_no:
            log("  [실패] 사업보고서 접수번호 없음\n")
            continue

        log(f"  [선택된 rcept_no] {rcept_no}")
        doc_text = get_document(rcept_no)

        if doc_text is None:
            log("  [실패] 문서 다운로드 실패\n")
            continue

        log(f"  [문서 전체 길이] {len(doc_text)}자")

        hits = find_product_section(doc_text)
        log(f"  [키워드 매칭 수] {len(hits)}")
        for i, (kw, pos, snippet) in enumerate(hits[:3]):
            log(f"\n  --- 매칭 {i+1} (키워드: {kw}, 위치: {pos}) ---")
            log(f"  {snippet}")

        log()

    with open("제품추출_결과.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))
