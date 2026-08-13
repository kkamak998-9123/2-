# -*- coding: utf-8 -*-
"""
KODEX 반도체 ETF 35개 기업 - DART 재무제표 일괄 다운로드
2023~2025년 데이터 추출 및 CSV 저장
"""

import pandas as pd
import requests
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# KODEX 반도체 ETF 구성 기업 정보 (기업명, 종목코드, DART고유번호)
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

API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"

def fetch_company_statements(api_key, corp_code, company_info):
    """단일 회사의 2023~2025년 모든 재무제표 추출"""
    comp_name, stock_code, _ = company_info
    api_url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

    all_rows = []

    # 각 연도별로 데이터 모두 추출
    for year in ['2025', '2024', '2023']:
        year_found = False

        # CFS 우선, 없으면 OFS
        for fs_div in ['CFS', 'OFS']:
            params = {
                'crtfc_key': api_key,
                'corp_code': corp_code,
                'bsns_year': year,
                'reprt_code': '11011',
                'fs_div': fs_div
            }

            try:
                res = requests.get(api_url, params=params, timeout=10)
                data = res.json()
                status = data.get('status')

                if status == '000' and 'list' in data and len(data['list']) > 0:
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
                            'stock_code': stock_code,
                            'corp_name': comp_name,
                            'corp_code': corp_code,
                            'bsns_year': year,
                            'fs_div': fs_div,
                            'sj_div': sj_div_val,
                            'sj_nm': sj_nm,
                            'account_nm': row.get('account_nm'),
                            'thstrm_amount': row.get('thstrm_amount'),
                            'frmtrm_amount': row.get('frmtrm_amount'),
                            'bfefrmtrm_amount': row.get('bfefrmtrm_amount'),
                            'ord': row.get('ord')
                        }
                        all_rows.append(cleaned_row)

                    year_found = True
                    break  # 이 연도는 찾았으니 다음 연도로

            except Exception as e:
                continue

            time.sleep(0.05)

    return all_rows if all_rows else None

def download_all_statements(output_filename="kodex_semiconductor_statements.csv"):
    """35개 기업의 모든 재무제표 다운로드"""

    print("=" * 80)
    print("KODEX 반도체 ETF 35개 기업 - DART 재무제표 일괄 다운로드")
    print("=" * 80)
    print(f"\n다운로드 대상: {len(companies_data)}개 기업")
    print(f"기간: 2023~2025년\n")

    all_results = []

    # 멀티스레드로 병렬 다운로드 (5개 스레드)
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_company = {
            executor.submit(fetch_company_statements, API_KEY, corp_code, (name, code, corp_code)): (name, code, corp_code)
            for name, code, corp_code in companies_data
        }

        for future in tqdm(as_completed(future_to_company), total=len(companies_data), desc="다운로드 진행"):
            company_info = future_to_company[future]
            try:
                result_rows = future.result()
                if result_rows:
                    all_results.extend(result_rows)
                    print(f"[OK] {company_info[0]}: {len(result_rows)}행")
                else:
                    print(f"[NO] {company_info[0]}: 데이터 없음")
            except Exception as e:
                print(f"[ER] {company_info[0]}: 오류 - {e}")

            time.sleep(0.05)

    # DataFrame 생성 및 정렬
    if all_results:
        print("\n" + "=" * 80)
        print("데이터 정렬 및 저장 중...")
        print("=" * 80)

        final_df = pd.DataFrame(all_results)

        # 재무제표 종류별 정렬 가중치
        sj_order = {'BS': 1, 'IS': 2, 'CIS': 3, 'CF': 4, 'SCE': 5}
        final_df['sj_weight'] = final_df['sj_div'].map(lambda x: sj_order.get(x, 99))

        # 정렬: 회사 -> 연도(역순) -> 재무제표 종류 -> 계정과목 순서
        final_df = final_df.sort_values(
            by=['corp_name', 'bsns_year', 'sj_weight', 'ord'],
            ascending=[True, False, True, True]
        ).drop(columns=['sj_weight']).reset_index(drop=True)

        # CSV 저장
        csv_path = f'C:\\Users\\willo\\Desktop\\코딩\\프로젝트4\\{output_filename}'
        final_df.to_csv(csv_path, index=False, encoding='utf-8-sig')

        print(f"\n[SUCCESS] 다운로드 완료!")
        print(f"총 {len(final_df):,}행의 재무제표 데이터 추출")
        print(f"저장 경로: {csv_path}")
        print("\n파일 요약:")
        print(f"  - 회사 수: {final_df['corp_name'].nunique()}")
        print(f"  - 기간: {final_df['bsns_year'].min()}~{final_df['bsns_year'].max()}년")
        print(f"  - 재무제표 유형: {final_df['sj_nm'].nunique()}개")
        print("\n컬럼:")
        print(final_df.columns.tolist())

        return final_df
    else:
        print("\n[ERROR] 추출된 데이터가 없습니다.")
        return None

if __name__ == "__main__":
    df = download_all_statements()

    if df is not None:
        print("\n" + "=" * 80)
        print("샘플 데이터 (처음 10행):")
        print("=" * 80)
        print(df.head(10).to_string())
