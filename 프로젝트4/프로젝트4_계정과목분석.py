# -*- coding: utf-8 -*-
"""
CSV 파일에서 실제 계정과목 추출 및 분석
"""

import pandas as pd

# CSV 파일 로드
csv_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\kodex_semiconductor_statements.csv'
df = pd.read_csv(csv_file)

print("=" * 100)
print("KODEX 반도체 ETF 35개 기업 - 계정과목 분석")
print("=" * 100)

# 기본 정보
print(f"\n[기본 정보]")
print(f"총 행 수: {len(df):,}")
print(f"기업 수: {df['corp_name'].nunique()}")
print(f"연도: {sorted(df['bsns_year'].unique())}")
print(f"재무제표 유형: {df['sj_div'].unique().tolist()}")

# 재무제표별 계정과목 추출
print("\n" + "=" * 100)
print("재무제표별 계정과목 현황")
print("=" * 100)

for sj_div in ['BS', 'IS', 'CF', 'CIS', 'SCE']:
    sj_df = df[df['sj_div'] == sj_div]
    if len(sj_df) == 0:
        continue

    sj_nm = sj_df['sj_nm'].iloc[0]
    accounts = sj_df['account_nm'].unique()

    print(f"\n[{sj_div}] {sj_nm}")
    print(f"계정과목 수: {len(accounts)}")
    print("-" * 100)

    for idx, account in enumerate(sorted(accounts), 1):
        print(f"{idx:2}. {account}")

# 손익계산서 (IS) 상세 분석
print("\n" + "=" * 100)
print("손익계산서(IS) - 1개 기업의 2025년 예시")
print("=" * 100)

sample_df = df[(df['sj_div'] == 'IS') &
               (df['corp_name'] == '삼성전자') &
               (df['bsns_year'] == 2025) &
               (df['fs_div'] == 'CFS')].copy()

if len(sample_df) > 0:
    print(f"\n기업: 삼성전자, 연도: 2025년, 구분: CFS(연결)")
    print(f"계정과목 수: {len(sample_df)}")
    print("-" * 100)
    print(sample_df[['account_nm', 'thstrm_amount', 'ord']].to_string(index=False))

# 재무상태표 (BS) 상세 분석
print("\n" + "=" * 100)
print("재무상태표(BS) - 1개 기업의 2025년 예시")
print("=" * 100)

sample_df = df[(df['sj_div'] == 'BS') &
               (df['corp_name'] == '삼성전자') &
               (df['bsns_year'] == 2025) &
               (df['fs_div'] == 'CFS')].copy()

if len(sample_df) > 0:
    print(f"\n기업: 삼성전자, 연도: 2025년, 구분: CFS(연결)")
    print(f"계정과목 수: {len(sample_df)}")
    print("-" * 100)
    print(sample_df[['account_nm', 'thstrm_amount', 'ord']].to_string(index=False))

# 현금흐름표 (CF) 상세 분석
print("\n" + "=" * 100)
print("현금흐름표(CF) - 1개 기업의 2025년 예시")
print("=" * 100)

sample_df = df[(df['sj_div'] == 'CF') &
               (df['corp_name'] == '삼성전자') &
               (df['bsns_year'] == 2025) &
               (df['fs_div'] == 'CFS')].copy()

if len(sample_df) > 0:
    print(f"\n기업: 삼성전자, 연도: 2025년, 구분: CFS(연결)")
    print(f"계정과목 수: {len(sample_df)}")
    print("-" * 100)
    print(sample_df[['account_nm', 'thstrm_amount', 'ord']].to_string(index=False))

# 주요 계정과목 검색
print("\n" + "=" * 100)
print("주요 계정과목 검색")
print("=" * 100)

search_terms = ['매출', '영업', '이익', '자산', '부채', '자본', '현금']

for term in search_terms:
    matching = df['account_nm'].unique()
    matching = [acc for acc in matching if term in acc]
    if matching:
        print(f"\n['{term}' 포함 계정과목] ({len(matching)}개)")
        for account in sorted(matching):
            print(f"  - {account}")

print("\n" + "=" * 100)
