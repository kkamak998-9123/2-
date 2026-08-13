# -*- coding: utf-8 -*-
"""
OpenDART Multi-Company All-Statements Ultra-Fast Extractor (v12)
Description: 필수 파라미터 누락 에러(fs_div)를 해결하고, 연결재무제표(CFS) 우선 및 
             개별재무제표(OFS) 폴백 조회를 통해 100개 기업의 3대 재무제표를 완벽 추출합니다.
"""

import FinanceDataReader as fdr
import pandas as pd
import requests
import zipfile
import io
import xml.etree.ElementTree as ET
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_kospi100_by_fdr():
    """FinanceDataReader를 통해 KOSPI 실시간 시가총액 상위 100개 종목 추출 (동적 컬럼 감지)"""
    print("[INFO] 1단계: FinanceDataReader로 KOSPI 실시간 시가총액 순위를 조회합니다...")
    df_kospi = fdr.StockListing('KOSPI')
    
    marcap_col = None
    for col in df_kospi.columns:
        if col.lower() in ['marcap', 'marketcap'] or '시가총액' in str(col):
            marcap_col = col
            break
            
    if marcap_col is None:
        df_krx = fdr.StockListing('KRX')
        df_kospi = df_krx[df_krx['Market'] == 'KOSPI'].copy()
        for col in df_kospi.columns:
            if col.lower() in ['marcap', 'marketcap'] or '시가총액' in str(col):
                marcap_col = col
                break
                
    if marcap_col is None:
        raise KeyError("[ERROR] 시가총액 컬럼을 찾을 수 없습니다.")
        
    df_kospi[marcap_col] = pd.to_numeric(df_kospi[marcap_col], errors='coerce')
    df_sorted = df_kospi.sort_values(by=marcap_col, ascending=False)
    
    df_top100 = df_sorted.head(100).copy()
    df_top100['rank'] = range(1, 101)
    
    code_col = 'Code' if 'Code' in df_top100.columns else ('종목코드' if '종목코드' in df_top100.columns else df_top100.columns[0])
    name_col = 'Name' if 'Name' in df_top100.columns else ('종목명' if '종목명' in df_top100.columns else df_top100.columns[1])
    
    df_top100['Code'] = df_top100[code_col].astype(str).str.zfill(6)
    df_top100['Name'] = df_top100[name_col]
    
    print(f"[SUCCESS] 시가총액 1위({df_top100.iloc[0]['Name']})부터 100위({df_top100.iloc[-1]['Name']}) 타겟팅 완료!")
    return df_top100[['rank', 'Code', 'Name']]

def get_corp_code_map(api_key):
    """OpenDART 고유번호 ZIP 파일을 다운로드하여 [종목코드:고유번호] 딕셔너리 생성"""
    print("[INFO] 2단계: OpenDART 기업 고유번호 매핑 테이블을 생성합니다 (초고속 인메모리 방식)...")
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"고유번호 다운로드 실패 (HTTP {response.status_code})")
        
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        xml_data = zf.read('CORPCODE.xml')
        
    root = ET.fromstring(xml_data)
    
    code_map = {}
    for list_node in root.findall('list'):
        stock_code = list_node.findtext('stock_code')
        corp_code = list_node.findtext('corp_code')
        if stock_code and len(stock_code.strip()) == 6:
            code_map[stock_code.strip()] = corp_code.strip()
            
    print(f"[SUCCESS] 상장사 고유번호 매핑 완료 (총 {len(code_map)}개 기업 로드)")
    return code_map

def fetch_single_company_all_statements(api_key, corp_code, info):
    """단일회사 전체 재무제표 API(fnlttSinglAcntAll.json) 호출 (CFS우선, OFS폴백)"""
    api_url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    
    # 2025년 기준 조회 시 당기(25), 전기(24), 전전기(23) 3개년 데이터가 일괄 반환됩니다.
    # 2025년 보고서 미제출 기업은 2024년으로 자동 폴백합니다.
    for year in ['2025', '2024']:
        # ⭐ [에러 수정 핵심 포인트] 연결재무제표('CFS') 우선 시도 후, 없으면 개별재무제표('OFS') 시도
        for fs_div in ['CFS', 'OFS']:
            params = {
                'crtfc_key': api_key,
                'corp_code': corp_code,
                'bsns_year': year,
                'reprt_code': '11011',  # 11011: 사업보고서
                'fs_div': fs_div        # ⭐ 필수 파라미터 장착!
            }
            try:
                res = requests.get(api_url, params=params, timeout=10)
                data = res.json()
                status = data.get('status')
                
                # '000': 정상 응답
                if status == '000' and 'list' in data:
                    rows = []
                    for row in data['list']:
                        sj_div_val = row.get('sj_div')
                        sj_nm = row.get('sj_nm') or (
                            '재무상태표' if sj_div_val == 'BS' else
                            '손익계산서' if sj_div_val == 'IS' else
                            '포괄손익계산서' if sj_div_val == 'CIS' else
                            '현금흐름표' if sj_div_val == 'CF' else
                            '자본변동표' if sj_div_val == 'SCE' else sj_div_val
                        )
                        
                        cleaned_row = {
                            'market_cap_rank': info.get('rank'),
                            'stock_code': info.get('Code'),
                            'corp_name': info.get('Name') or row.get('corp_name'),
                            'corp_code': corp_code,
                            'bsns_year': year,                    # 조회 성공한 연도
                            'fs_div': fs_div,                     # CFS(연결) 또는 OFS(개별)
                            'sj_div': sj_div_val,                 # 약어 (BS, IS, CIS, CF, SCE)
                            'sj_nm': sj_nm,                       # 재무제표 한글명
                            'account_nm': row.get('account_nm'),  # 계정과목명
                            'thstrm_amount_current': row.get('thstrm_amount'),       # 당기 금액
                            'frmtrm_amount_prior': row.get('frmtrm_amount'),         # 전기 금액
                            'bfefrmtrm_amount_before': row.get('bfefrmtrm_amount'),  # 전전기 금액
                            'ord': row.get('ord')                 # 정규 정렬 순서
                        }
                        rows.append(cleaned_row)
                    return rows  # 성공 시 즉시 데이터 반환하고 루프 종료!
                    
                # '013': 조회된 데이터 없음 (예: 연결재무제표 미작성 기업 -> 다음 OFS로 넘어감)
                elif status == '013':
                    continue
                else:
                    # 💡 실제 인증키 에러나 API 한도 초과 시 콘솔에 경고 출력 (원인 파악용)
                    if year == '2025' and fs_div == 'CFS': # 로그 과다 출력 방지
                        print(f"\n[API WARNING] {info.get('Name')} 조회 경고: [코드 {status}] {data.get('message')}")
                        
            except Exception as e:
                print(f"\n[NETWORK ERROR] {info.get('Name')} 요청 중 예외 발생: {e}")
            time.sleep(0.05)
    return None

def get_all_statements_ultra_fast(api_key, output_filename="kospi100_all_statements_2025_v12.csv"):
    start_time = time.time()
    
    # 1. KOSPI 100 시가총액 종목 및 고유번호 매핑
    target_df = get_kospi100_by_fdr()
    code_map = get_corp_code_map(api_key)
    
    target_df['corp_code'] = target_df['Code'].map(code_map)
    valid_targets = target_df.dropna(subset=['corp_code']).copy()
    meta_info = valid_targets.set_index('corp_code')[['rank', 'Code', 'Name']].to_dict('index')
    
    print("[INFO] 3단계: ⚡ 재무상태표(BS), 손익계산서(IS/CIS), 현금흐름표(CF) 통합 고속 수집 엔진 가동...")
    print("[INFO] OpenDART 단일회사 전체 재무제표 API(fnlttSinglAcntAll.json)를 5개 스레드로 병렬 호출합니다.")
    
    all_rows = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_corp = {
            executor.submit(fetch_single_company_all_statements, api_key, c_code, meta_info[c_code]): c_code 
            for c_code in valid_targets['corp_code']
        }
        
        for future in tqdm(as_completed(future_to_corp), total=len(valid_targets), desc="⚡ 3대 재무제표 통합 수집 진행률"):
            result_rows = future.result()
            if result_rows:
                all_rows.extend(result_rows)
            time.sleep(0.05)
            
    # 4. 데이터프레임 변환 및 정렬
    if all_rows:
        print("\n[INFO] 4단계: 수집된 전체 재무제표 데이터를 하나의 파일로 통합 및 정렬합니다...")
        final_df = pd.DataFrame(all_rows)
        
        # 💡 [회계 표준 정렬 가중치] 재무상태표(BS) -> 손익계산서(IS/CIS) -> 현금흐름표(CF) 순으로 정돈
        sj_order = {'BS': 1, 'IS': 2, 'CIS': 3, 'CF': 4, 'SCE': 5}
        final_df['sj_weight'] = final_df['sj_div'].map(lambda x: sj_order.get(x, 99))
        
        # 순위 -> 연결/개별 -> 재무제표 종류 -> 계정과목 순서대로 정렬
        final_df = final_df.sort_values(by=['market_cap_rank', 'fs_div', 'sj_weight', 'ord']).drop(columns=['sj_weight']).reset_index(drop=True)
        
        # 한글 깨짐 방지 utf-8-sig 포맷 CSV 저장
        final_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        
        elapsed_time = round(time.time() - start_time, 2)
        print(f"[SUCCESS] 🎉 단 {elapsed_time}초 만에 3대 재무제표 완벽 추출 완료! 최종 파일: '{output_filename}'")
        print(f"[INFO] 총 수집된 재무제표 행(Row) 수: {len(final_df):,}개")
        print("[TIP] 출력된 CSV 파일의 'sj_nm' 컬럼을 필터링하여 재무상태표/손익계산서/현금흐름표를 편하게 비교해 보세요.")
    else:
        print("[ERROR] 추출된 재무 데이터가 없습니다. 콘솔에 출력된 [API WARNING] 문구를 확인해 주세요!")

if __name__ == "__main__":
    # ⚠️ 본인의 OpenDART API Key를 입력하세요 (https://opendart.fss.or.kr/)
    MY_API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"
    
    if MY_API_KEY == "YOUR_DART_API_KEY_HERE":
        print("[ERROR] 스크립트 하단의 'MY_API_KEY' 변수에 실제 OpenDART API 키를 입력해 주세요.")
    else:
        get_all_statements_ultra_fast(api_key=MY_API_KEY)