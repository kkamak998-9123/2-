# -*- coding: utf-8 -*-
"""
계정과목명을 표준명으로 통일
"""

import pandas as pd

# 추출된 데이터 로드
input_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
df = pd.read_csv(input_file)

print("=" * 80)
print("계정과목명 정규화")
print("=" * 80)

print(f"\n[정규화 전]")
print(f"고유 계정과목명: {df['account_nm'].nunique()}개")
print("-" * 80)
for i, account in enumerate(sorted(df['account_nm'].unique()), 1):
    count = len(df[df['account_nm'] == account])
    print(f"{i}. {account:<50} ({count}행)")

# 계정과목명을 통일
df['account_nm'] = '영업활동현금흐름'

print(f"\n[정규화 후]")
print(f"고유 계정과목명: {df['account_nm'].nunique()}개")
print(f"모든 행의 계정과목: {df['account_nm'].unique()[0]}")

# 결과 출력
print(f"\n[샘플 데이터]")
print("-" * 80)
print(df[['corp_name', 'bsns_year', 'account_nm', 'thstrm_amount']].head(10).to_string())

# 저장
output_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n[완료]")
print(f"저장: {output_file}")
print(f"총 {len(df)}행이 정규화되었습니다.")
print("=" * 80)
