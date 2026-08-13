# -*- coding: utf-8 -*-
"""
DART-FSS Real KOSPI 100 Extractor (v7)
Description: 네이버 금융에서 실시간 KOSPI 시가총액 상위 100개 종목을 정확히 크롤링한 후,
             해당 순서대로 DART에서 3개년 재무제표를 다운로드하여 하나의 CSV로 병합합니다.
"""

import dart_fss as dart
import pandas as pd
import time
from tqdm import tqdm
import requests
import urllib.request
import re

def initialize_dart(api_key):
    """DART-FSS 라이브러리를 초기화합니다."""
    print("[INFO] DART-FSS 라이브러리를 초기화합니다...")
    dart.set_api_key(api_key=api_key)

def get_real_kospi100_tickers():
    """네이버 금융 시가총액 페이지에서 KOSPI 상위 100개 종목코드와 기업명을 정확히 순서대로 추출"""
    print("[INFO] 네이버 금융에서 KOSPI 시가총액 순위를 조회하고 있습니다...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    kospi100_list = []
    # 네이버 금융 시가총액 페이지는 한 페이지당 50개씩 보여주므로 1페이지, 2페이지를 긁습니다 (총 100개)
    for page in [1, 2]:
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={page}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('cp949', errors='ignore')
                
            # 종목 링크와 이름에서 종목코드(6자리)와 종목명 추출하는 정규식
            # 예: <a href="/item/main.naver?code=005930" class="tltle">삼성전자</a>
            pattern = r'href="/item/main\.naver\?code=(\d{6})"[^>]* class="tltle">([^<]+)</a>'
            matches = re.findall(pattern, html)
            
            for code, name in matches:
                kospi100_list.append({'stock_code': code, 'corp_name': name})
                if len(kospi100_list) >= 100:
                    break
        except Exception as e:
            print(f"[ERROR] 시가총액 페이지 로드 실패 (Page {page}): {e}")
            
    df_top100 = pd.DataFrame(kospi100_list)
    print(f"[SUCCESS] 시가총액 1위({df_top100.iloc[0]['corp_name']})부터 100위({df_top100.iloc[-1]['corp_name']})까지 선별 완료!")
    return df_top100

def get_kospi100_financial_statements_stable(api_key, output_filename="kospi100_financials_2025_final.csv"):
    # 1. DART 초기화
    initialize_dart(api_key)
    
    # 2. 실시간 시가총액 기준 TOP 100 리스트 확보 (삼성전자, SK하이닉스 순)
    target_corps_df = get_real_kospi100_tickers()
    
    # 3. DART 고유번호 목록 로드
    print("[INFO] DART 고유번호 목록을 불러오는 중입니다...")
    try:
        corp_list = dart.get_corp_list()
    except Exception as e:
        print(f"[ERROR] 고유번호 목록을 가져오지 못했습니다: {e}")
        return
        
    all_dfs = []
    print(f"[INFO] 시가총액 순위대로 100개 기업의 재무제표 수집을 시작합니다.")
    
    # 4. 시가총액 순으로 정렬된 리스트를 돌면서 DART 데이터 추출
    for idx, row in tqdm(target_corps_df.iterrows(), total=len(target_corps_df), desc="재무 데이터 수집 진행률"):
        stock_code = row['stock_code']
        corp_name = row['corp_name']
        
        try:
            # 6자리 상장 종목코드로 DART 기업 고유번호를 정확하게 조회
            corp = corp_list.find_by_stock_code(stock_code)
            
            if corp is None:
                # 종목코드로 매칭 실패 시 이름으로 재시도
                corp = corp_list.find_by_corp_name(corp_name, exactly=True)
                
            if corp is None:
                print(f"\n[INFO] {corp_name}({stock_code}) 종목을 DART 고유번호 목록에서 찾을 수 없어 스킵합니다.")
                continue
                
            # 2025년 조회를 통해 3개년 데이터 일괄 추출
            fs = corp.extract_fs(bgn_de='20250101', end_de='20251231')
            
            if fs is None:
                continue
                
            # 포괄손익계산서(cis) 또는 손익계산서(is) 추출
            df_is = fs['cis'] if 'cis' in fs.labels else (fs['is'] if 'is' in fs.labels else None)
            
            if df_is is not None:
                # Multi-Index 컬럼 구조 평탄화 (v6 에러 방지 강화 적용)
                if isinstance(df_is.columns, pd.MultiIndex):
                    new_columns = []
                    for col in df_is.columns.values:
                        col_cleaned = [str(item[0]) if isinstance(item, tuple) else str(item) for item in col]
                        new_columns.append('_'.join(col_cleaned).strip())
                    df_is.columns = new_columns
                
                # 인덱스 초기화 (계정과목을 컬럼으로)
                df_is = df_is.reset_index()
                
                # 메타데이터 및 시가총액 순위 정보 추가
                df_is['market_cap_rank'] = idx + 1
                df_is['corp_code'] = corp.corp_code
                df_is['corp_name'] = corp_name
                df_is['stock_code'] = stock_code
                
                all_dfs.append(df_is)
                
            # API 제한 방지를 위해 1.2초 대기
            time.sleep(1.2)
            
        except requests.exceptions.RequestException as re:
            print(f"\n[NETWORK WARNING] {corp_name} 처리 중 네트워크 지연 발생: {str(re)}")
            time.sleep(3.0)
            continue
        except Exception as e:
            print(f"\n[SKIP WARNING] {corp_name} 데이터 처리 중 에러 발생 (스킵): {str(e)}")
            time.sleep(0.5)
            continue
            
    # 5. 하나의 단일 CSV 파일로 결합 및 저장
    if all_dfs:
        print("[INFO] 수집된 모든 데이터를 하나의 파일로 통합하고 있습니다...")
        final_df = pd.concat(all_dfs, ignore_index=True, sort=False)
        
        # 컬럼 순서 정렬 (순위와 식별 메타데이터를 맨 앞으로)
        meta_cols = ['market_cap_rank', 'corp_code', 'corp_name', 'stock_code']
        other_cols = [col for col in final_df.columns if col not in meta_cols]
        final_df = final_df[meta_cols + other_cols]
        
        # CSV 파일 저장 (한글 깨짐 방지 utf-8-sig)
        final_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        print(f"[SUCCESS] 다운로드가 완료되었습니다! 파일명: '{output_filename}'")
    else:
        print("[ERROR] 데이터가 전혀 수집되지 않았습니다. API 키 권한이나 DART 서버 상태를 확인해 주세요.")

if __name__ == "__main__":
    # ⚠️ 본인의 OpenDART API Key를 입력하세요 (https://opendart.fss.or.kr/)
    MY_API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"
    if MY_API_KEY == "YOUR_DART_API_KEY_HERE":
        print("[ERROR] 스크립트 하단의 'MY_API_KEY' 변수에 실제 OpenDART API 키를 입력해 주세요.")
    else:
        get_kospi100_financial_statements_stable(api_key=MY_API_KEY)