# -*- coding: utf-8 -*-
"""
필요 계정과목만 추출하여 새 CSV 파일 생성
"""

import pandas as pd
import re

csv_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\kodex_semiconductor_statements.csv'
df = pd.read_csv(csv_file)

def norm(s):
    if pd.isna(s): return ''
    return s.replace(' ', '')

# 현금흐름표만 필터링
cf_df = df[df['sj_div'] == 'CF'].copy()

# 검색 조건
simple_targets_norm = set(norm(t) for t in ['영업활동현금흐름', '영업활동순현금흐름'])
regex_pattern = r'영업활동으로인한.*현금흐름'

print("=" * 80)
print("필요 데이터 추출 중...")
print("=" * 80)

# 매칭되는 행 찾기
matching_rows = []

for idx, row in cf_df.iterrows():
    account_nm = row['account_nm']
    norm_account = norm(account_nm)

    # 정확일치 또는 정규식 매칭
    if norm_account in simple_targets_norm or re.search(regex_pattern, norm_account):
        matching_rows.append(row)

# DataFrame으로 변환
result_df = pd.DataFrame(matching_rows)

# 기업별, 연도별로 정렬
result_df = result_df.sort_values(by=['corp_name', 'bsns_year'], ascending=[True, False])
result_df = result_df.reset_index(drop=True)

print(f"\n추출된 행 수: {len(result_df)}")
print(f"기업 수: {result_df['corp_name'].nunique()}")
print(f"연도: {sorted(result_df['bsns_year'].unique())}")

# 샘플 출력
print("\n[추출된 데이터 샘플]")
print("-" * 80)
print(result_df[['corp_name', 'bsns_year', 'account_nm', 'thstrm_amount']].head(10).to_string())

# CSV로 저장
output_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
result_df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n[완료]")
print(f"저장 경로: {output_file}")
print(f"파일 크기: {len(result_df)} 행 × {len(result_df.columns)} 컬럼")

# 기업별 요약
print("\n[기업별 행 수]")
print("-" * 80)
company_summary = result_df.groupby('corp_name').size().sort_values(ascending=False)
for company, count in company_summary.items():
    print(f"{company:<25} {count}행")

print("\n" + "=" * 80)
