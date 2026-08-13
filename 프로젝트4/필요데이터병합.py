# -*- coding: utf-8 -*-
"""
투자활동현금흐름 데이터를 프로젝트4_필요데이터.csv에 추가
HPSP 중복 확인 및 제거
"""

import pandas as pd

# 기존 파일 로드
main_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
main_df = pd.read_csv(main_file)

# 투자활동현금흐름 파일 로드
invest_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_투자활동현금흐름.csv'
invest_df = pd.read_csv(invest_file)

print("=" * 80)
print("필요데이터 병합 및 HPSP 중복 제거")
print("=" * 80)

# HPSP 데이터 확인
print(f"\n[HPSP 투자활동현금흐름 데이터]")
print("-" * 80)
hpsp_invest = invest_df[invest_df['corp_name'] == 'HPSP'].copy()
print(f"총 {len(hpsp_invest)}행")
for idx, row in hpsp_invest.iterrows():
    print(f"  {int(row['bsns_year'])}년: {row['thstrm_amount']:>15,.0f}")

# HPSP 중복이 있는지 확인
print(f"\n[HPSP 중복 분석]")
print("-" * 80)
hpsp_year_count = hpsp_invest.groupby('bsns_year').size()
for year, count in hpsp_year_count.items():
    status = f"중복있음 ({count}행)" if count > 1 else "정상 (1행)"
    print(f"  {int(year)}년: {status}")

# HPSP 중복 제거 (금액이 큰 것만 유지)
if len(hpsp_invest) > 3:
    print(f"\n[HPSP 중복 제거 중...]")
    hpsp_filtered = []
    for year in [2024, 2023, 2025]:
        year_data = hpsp_invest[hpsp_invest['bsns_year'] == year]
        if len(year_data) > 0:
            # 금액 절대값이 큰 것 선택
            max_row = year_data.loc[year_data['thstrm_amount'].abs().idxmax()]
            hpsp_filtered.append(max_row)
            if len(year_data) > 1:
                print(f"  {int(year)}년: {len(year_data)}행 -> 1행 (금액 선택: {max_row['thstrm_amount']:,.0f})")

    hpsp_invest = pd.DataFrame(hpsp_filtered)

# 다른 기업의 투자활동현금흐름
other_invest = invest_df[invest_df['corp_name'] != 'HPSP'].copy()

# 투자활동현금흐름 데이터 결합 및 정렬
invest_final = pd.concat([other_invest, hpsp_invest], ignore_index=True)
invest_final = invest_final.sort_values(by=['corp_name', 'bsns_year'], ascending=[True, False])
invest_final = invest_final.reset_index(drop=True)

print(f"\n[투자활동현금흐름 최종 행 수]")
print(f"  처리 전: {len(invest_df)}행")
print(f"  처리 후: {len(invest_final)}행")

# 메인 데이터와 병합
print(f"\n[데이터 병합 중...]")
print(f"  영업활동현금흐름: {len(main_df)}행")
print(f"  투자활동현금흐름: {len(invest_final)}행")

result_df = pd.concat([main_df, invest_final], ignore_index=True)
result_df = result_df.sort_values(by=['corp_name', 'bsns_year', 'account_nm'],
                                  ascending=[True, False, True])
result_df = result_df.reset_index(drop=True)

print(f"  합계: {len(result_df)}행")

# 계정과목별 분포
print(f"\n[계정과목별 분포]")
print("-" * 80)
for account in sorted(result_df['account_nm'].unique()):
    count = len(result_df[result_df['account_nm'] == account])
    print(f"  {account:<25} {count:>3}행")

# 저장
output_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
result_df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n[완료]")
print(f"  저장: {output_file}")
print(f"  총 {len(result_df)}행 × 12컬럼")
print("=" * 80)
