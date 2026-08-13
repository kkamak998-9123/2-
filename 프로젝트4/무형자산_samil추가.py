# -*- coding: utf-8 -*-
"""
프로젝트4_필요데이터.csv 에 추가된 '무형자산' 행을
'Samil Project DB - semiconductor.csv' 양식에 맞춰 추가
"""

import pandas as pd
from datetime import date

main_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
samil_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\Samil Project DB - semiconductor.csv'

main_df = pd.read_csv(main_file)
samil_df = pd.read_csv(samil_file)

intangible = main_df[main_df['account_nm'] == '무형자산'].copy()

def fmt_corp(code):
    return '="' + str(int(code)).zfill(8) + '"'

def fmt_stock(code):
    return '="' + str(int(code)).zfill(6) + '"'

new_rows = pd.DataFrame({
    'corp_code': intangible['corp_code'].apply(fmt_corp),
    'stock_code': intangible['stock_code'].apply(fmt_stock),
    'corp_name': intangible['corp_name'],
    'year': intangible['bsns_year'],
    'fs_div': intangible['fs_div'],
    'sj_div': intangible['sj_div'],
    'account_name': intangible['account_nm'],
    'amount': intangible['thstrm_amount'],
    'memo': None,
    'updated_at': date.today().isoformat(),
})

# 재실행 안전성: 기존 '무형자산' 행 제거 후 재삽입
samil_df = samil_df[samil_df['account_name'] != '무형자산'].copy()

result_df = pd.concat([samil_df, new_rows], ignore_index=True)
result_df = result_df.sort_values(by=['corp_name', 'year', 'account_name'],
                                   ascending=[True, False, True])
result_df = result_df.reset_index(drop=True)

result_df.to_csv(samil_file, index=False, encoding='utf-8-sig')

report = []
report.append('추가된 행 수: ' + str(len(new_rows)))
report.append('병합 전 총 행 수: ' + str(len(samil_df)))
report.append('병합 후 총 행 수: ' + str(len(result_df)))
report_text = '\n'.join(report)
print(report_text)
with open(r'C:\Users\willo\Desktop\코딩\프로젝트4\무형자산_samil추가_결과.txt', 'w', encoding='utf-8') as f:
    f.write(report_text)
