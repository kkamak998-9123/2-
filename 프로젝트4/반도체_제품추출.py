# -*- coding: utf-8 -*-
"""
KODEX 반도체 ETF 35개 기업 - 사업보고서 '주요 제품 및 서비스' 표 추출
list.json -> document.xml -> 표 파싱(pandas.read_html) -> 정리된 CSV
"""

import re
import io
import time
import zipfile

import pandas as pd
import requests

API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"

companies_data = [
    ("SK하이닉스", "000660", "00164779"),
    ("삼성전자", "005930", "00126380"),
    ("한미반도체", "042700", "00161383"),
    ("주성엔지니어링", "036930", "00252135"),
    ("리노공업", "058430", "00369657"),
    ("DB하이텍", "068270", "00160843"),
    ("원익IPS", "240810", "01135941"),
    ("피에스케이", "066800", "01365825"),
    ("이오테크닉스", "011930", "00246417"),
    ("심텍", "058650", "01095722"),
    ("HPSP", "061970", "01288827"),
    ("파두", "224110", "01292291"),
    ("제주반도체", "090460", "00447487"),
    ("유진테크", "039440", "00531014"),
    ("하나마이크론", "081370", "00445054"),
    ("ISC", "024800", "00572905"),
    ("고영", "092220", "00579999"),
    ("티씨케이", "036620", "00245472"),
    ("두산테스나", "367770", "00563545"),
    ("테크윙", "204940", "00535676"),
    ("피에스케이홀딩스", "020960", "00208444"),
    ("RFHIC", "204210", "01078178"),
    ("코미코", "054450", "00997812"),
    ("태성", "323280", "01366000"),
    ("에스앤에스텍", "034230", "00411048"),
    ("케이씨텍", "063770", "01261893"),
    ("HD현대에너지솔루션", "267260", "01199550"),
    ("하나머티리얼즈", "205470", "00660750"),
    ("필옵틱스", "039030", "00938721"),
    ("LX세미콘", "148040", "00525934"),
    ("와이씨", "041920", "01109539"),
    ("SFA반도체", "007920", "00301246"),
    ("덕산네오룩스", "126340", "01061558"),
    ("넥스틴", "396770", "01080252"),
    ("가온칩스", "052690", "01364747"),
]


def get_latest_biz_report_rcept_no(corp_code):
    """사업보고서(A001) 최신 접수번호 조회"""
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        'crtfc_key': API_KEY,
        'corp_code': corp_code,
        'bgn_de': '20240101',
        'end_de': '20260712',
        'pblntf_detail_ty': 'A001',
        'page_no': 1,
        'page_count': 10,
    }
    res = requests.get(url, params=params, timeout=10)
    data = res.json()
    if data.get('status') != '000':
        return None, data.get('message')
    items = data.get('list', [])
    if not items:
        return None, "목록 없음"
    return items[0]['rcept_no'], items[0]['report_nm']


def get_document(rcept_no):
    """document.xml로 원문 zip 다운로드 후 텍스트 반환"""
    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {'crtfc_key': API_KEY, 'rcept_no': rcept_no}
    res = requests.get(url, params=params, timeout=30)

    if res.content[:2] != b'PK':
        return None

    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        all_text = ""
        for name in zf.namelist():
            raw = zf.read(name)
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                text = raw.decode('euc-kr', errors='ignore')
            all_text += text

    # lxml은 유니코드 문자열에 XML 인코딩 선언이 있으면 파싱을 거부함
    all_text = re.sub(r'<\?xml[^>]*\?>', '', all_text)
    return all_text


HEADER_KEYWORDS = ['구체적용도', '매출유형', '품목', '품 목', '매출액', '주요상표', '주요상품']


def find_section_anchor(doc_text):
    """실제 'N. 주요 제품 및 서비스' 섹션 제목만 찾음 (재무제표 주석 등에서
    '주요 제품과 서비스' 같은 문구가 나오는 오탐을 피하기 위해 </TITLE> 직전만 인정)"""
    m = re.search(r'주요\s*제품[^<]{0,20}</TITLE>', doc_text)
    return m.start() if m else None


def find_candidate_tables(doc_text):
    """'주요 제품' 섹션 ~ 다음 섹션 제목 전까지만 잘라내어 그 안의 표들을 파싱.
    (문서 전체를 read_html하면 수천 개 표 중 깨진 표 하나 때문에 전체가 죽는 문제가 있음)"""
    anchor_idx = find_section_anchor(doc_text)
    if anchor_idx is None:
        return []

    next_title_idx = doc_text.find('<TITLE', anchor_idx + 50)
    section_end = next_title_idx if next_title_idx != -1 else anchor_idx + 20000
    section_html = doc_text[anchor_idx:section_end]

    try:
        tables = pd.read_html(io.StringIO(section_html), flavor='lxml')
    except (ValueError, ImportError):
        return []

    # 단위표시용 1행짜리 표는 제외하고, 품목/매출 등 표 헤더 키워드가 있는 표만 후보로
    # (회사마다 '매출액' 대신 '2025년' 처럼 연도만 쓰는 등 표기가 달라 '매출' 단어에만
    # 의존하면 놓치는 경우가 있어 HEADER_KEYWORDS 전체로 판단)
    def looks_like_product_table(df):
        header_text = " ".join(str(c) for c in df.columns)
        body_text = " ".join(df.astype(str).values.flatten())
        return any(kw in header_text or kw in body_text for kw in HEADER_KEYWORDS)

    candidates = [df for df in tables if looks_like_product_table(df)]
    candidates.sort(key=len, reverse=True)
    return candidates


def dedupe_columns(columns):
    """멀티행 헤더 등으로 컬럼명이 중복되면 concat 시 에러가 나서 뒤에 번호를 붙임"""
    seen = {}
    new_cols = []
    for c in columns:
        c = str(c)
        if c not in seen:
            seen[c] = 0
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
    return new_cols


def clean_product_table(df, corp_name):
    """헤더 행을 실제 컬럼명으로 승격하고 병합 셀 문제를 정리"""
    # <THEAD><TH>가 있으면 pandas가 이미 컬럼명으로 인식함
    if any(any(kw in str(c) for kw in HEADER_KEYWORDS) for c in df.columns):
        body = df.copy()
        body.columns = dedupe_columns(body.columns)
        body.insert(0, 'corp_name', corp_name)
        return body.reset_index(drop=True)

    # <TH> 없이 첫 데이터 행이 헤더 역할을 하는 경우 (품목/구체적용도/매출액 등)
    header_row_idx = None
    for i in range(min(3, len(df))):
        row_text = " ".join(df.iloc[i].astype(str))
        if any(kw in row_text for kw in HEADER_KEYWORDS):
            header_row_idx = i
            break

    if header_row_idx is None:
        return None

    new_header = df.iloc[header_row_idx]
    body = df.iloc[header_row_idx + 1:].copy()
    body.columns = dedupe_columns(new_header)
    body.insert(0, 'corp_name', corp_name)
    return body.reset_index(drop=True)


def process_company(name, stock_code, corp_code):
    result = {
        'corp_name': name, 'stock_code': stock_code, 'corp_code': corp_code,
        'rcept_no': None, 'report_nm': None, 'status': None, 'table': None,
    }

    rcept_no, info = get_latest_biz_report_rcept_no(corp_code)
    if not rcept_no:
        result['status'] = f"실패(목록조회): {info}"
        return result

    result['rcept_no'] = rcept_no
    result['report_nm'] = info

    doc_text = get_document(rcept_no)
    if doc_text is None:
        result['status'] = "실패(문서다운로드)"
        return result

    candidates = find_candidate_tables(doc_text)
    if not candidates:
        result['status'] = "실패(표없음-수동확인필요)"
        return result

    for df in candidates:
        cleaned = clean_product_table(df, name)
        if cleaned is not None and not cleaned.empty:
            result['status'] = "성공"
            result['table'] = cleaned
            return result

    result['status'] = "실패(헤더인식실패-수동확인필요)"
    return result


if __name__ == "__main__":
    out_lines = []
    all_tables = []
    summary = []

    def log(s=""):
        print(s)
        out_lines.append(str(s))

    for name, stock_code, corp_code in companies_data:
        log(f"\n{'=' * 60}\n{name}\n{'=' * 60}")
        r = process_company(name, stock_code, corp_code)
        log(f"상태: {r['status']} | rcept_no: {r['rcept_no']} | 보고서명: {r['report_nm']}")
        summary.append({
            'corp_name': name, 'stock_code': stock_code, 'corp_code': corp_code,
            'status': r['status'], 'rcept_no': r['rcept_no'],
        })
        if r['table'] is not None:
            log(r['table'].to_string())
            all_tables.append(r['table'])
        time.sleep(0.3)

    with open("반도체_제품추출_로그.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))

    pd.DataFrame(summary).to_csv("반도체_제품추출_요약.csv", index=False, encoding='utf-8-sig')

    if all_tables:
        combined = pd.concat(all_tables, ignore_index=True, sort=False)
        combined.to_csv("반도체_제품추출_전체.csv", index=False, encoding='utf-8-sig')
        print(f"\n전체 저장 완료: 반도체_제품추출_전체.csv ({len(combined)}행)")

    success_count = sum(1 for s in summary if s['status'] == '성공')
    print(f"\n성공: {success_count}/{len(companies_data)}")
