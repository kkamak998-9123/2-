# -*- coding: utf-8 -*-
"""
고정자산비율(%) = (유형자산 + 무형자산) / 총자산 * 100
프로젝트4_필요데이터.csv 에서 유형자산/무형자산/총자산을 뽑아 계산한 뒤
프로젝트4_재무비율분석.csv 에 컬럼으로 추가
"""

import pandas as pd

need_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
ratio_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_재무비율분석.csv'

need_df = pd.read_csv(need_file)
ratio_df = pd.read_csv(ratio_file)

bs_items = need_df[need_df['account_nm'].isin(['유형자산', '무형자산', '총자산'])].copy()

pivot = bs_items.pivot_table(index=['corp_code', 'bsns_year'],
                              columns='account_nm',
                              values='thstrm_amount',
                              aggfunc='first').reset_index()

pivot['고정자산비율(%)'] = ((pivot['유형자산'] + pivot['무형자산']) / pivot['총자산'] * 100).round(2)

pivot = pivot.rename(columns={'bsns_year': 'year'})
merge_cols = pivot[['corp_code', 'year', '고정자산비율(%)']]

# 재실행 안전성: 기존 컬럼 제거 후 재병합
if '고정자산비율(%)' in ratio_df.columns:
    ratio_df = ratio_df.drop(columns=['고정자산비율(%)'])

result_df = ratio_df.merge(merge_cols, on=['corp_code', 'year'], how='left')

missing = result_df[result_df['고정자산비율(%)'].isna()]

result_df.to_csv(ratio_file, index=False, encoding='utf-8-sig')

report = []
report.append('전체 행 수: ' + str(len(result_df)))
report.append('고정자산비율 계산된 행 수: ' + str(result_df['고정자산비율(%)'].notna().sum()))
report.append('누락된 행 수: ' + str(len(missing)))
if len(missing) > 0:
    report.append(str(missing[['corp_code', 'corp_name', 'year']].to_string()))
report_text = '\n'.join(report)
print(report_text)
with open(r'C:\Users\willo\Desktop\코딩\프로젝트4\고정자산비율추가_결과.txt', 'w', encoding='utf-8') as f:
    f.write(report_text)
