# -*- coding: utf-8 -*-
"""
무형자산 추출 결과를 프로젝트4_필요데이터.csv 에 병합

규칙 (무형자산추출.py 와 동일):
1. '무형자산'(또는 '3. 무형자산') 단독 존재 -> 그 행 그대로 사용
2. '무형자산 및 영업권' / '무형자산과 영업권 합계' 합산 계정 존재 -> 그 행 그대로 사용
3. '영업권 이외의 무형자산' / '영업권외무형자산' 존재
   -> 같은 기업/연도/fs_div의 '영업권' 행이 있으면 금액을 합산, 없으면 그 행 그대로 사용
   -> 최종 account_nm 은 '무형자산'으로 통일
"""

import pandas as pd

raw = pd.read_csv(r'C:\Users\willo\Desktop\코딩\프로젝트4\kodex_semiconductor_statements.csv')
bs = raw[raw['sj_div'] == 'BS'].copy()


def norm(s):
    if pd.isna(s):
        return ''
    return str(s).replace(' ', '')


bs['norm'] = bs['account_nm'].apply(norm)

STANDALONE = {'무형자산', '3.무형자산'}
COMBINED = {'무형자산및영업권', '무형자산과영업권합계'}
EXCL_GOODWILL = {'영업권이외의무형자산', '영업권외무형자산'}
GOODWILL = {'영업권', '영업권,총액'}

new_rows = []

for (corp, year, fsdiv), g in bs.groupby(['corp_name', 'bsns_year', 'fs_div']):
    standalone = g[g['norm'].isin(STANDALONE)]
    combined = g[g['norm'].isin(COMBINED)]
    excl = g[g['norm'].isin(EXCL_GOODWILL)]
    goodwill = g[g['norm'].isin(GOODWILL)]

    matches = int(len(standalone) > 0) + int(len(combined) > 0) + int(len(excl) > 0)
    if matches == 0 or matches > 1:
        continue

    if len(standalone) > 0:
        base = standalone.iloc[0]
        thstrm = base['thstrm_amount']
        frmtrm = base['frmtrm_amount']
        bfefrmtrm = base['bfefrmtrm_amount']
        ord_val = base['ord']
    elif len(combined) > 0:
        base = combined.iloc[0]
        thstrm = base['thstrm_amount']
        frmtrm = base['frmtrm_amount']
        bfefrmtrm = base['bfefrmtrm_amount']
        ord_val = base['ord']
    else:
        base = excl.iloc[0]
        if len(goodwill) == 1:
            gw = goodwill.iloc[0]
            thstrm = base['thstrm_amount'] + gw['thstrm_amount']
            frmtrm = base['frmtrm_amount'] + gw['frmtrm_amount'] if pd.notna(base['frmtrm_amount']) and pd.notna(gw['frmtrm_amount']) else base['frmtrm_amount']
            bfefrmtrm = base['bfefrmtrm_amount'] + gw['bfefrmtrm_amount'] if pd.notna(base['bfefrmtrm_amount']) and pd.notna(gw['bfefrmtrm_amount']) else base['bfefrmtrm_amount']
        else:
            thstrm = base['thstrm_amount']
            frmtrm = base['frmtrm_amount']
            bfefrmtrm = base['bfefrmtrm_amount']
        ord_val = base['ord']

    new_rows.append({
        'stock_code': base['stock_code'],
        'corp_name': corp,
        'corp_code': base['corp_code'],
        'bsns_year': year,
        'fs_div': fsdiv,
        'sj_div': 'BS',
        'sj_nm': '재무상태표',
        'account_nm': '무형자산',
        'thstrm_amount': thstrm,
        'frmtrm_amount': frmtrm,
        'bfefrmtrm_amount': bfefrmtrm,
        'ord': ord_val,
        'duplicate_key': None,
    })

new_df = pd.DataFrame(new_rows)

main_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
main_df = pd.read_csv(main_file)

# 이미 '무형자산' 행이 있으면 중복 방지를 위해 제거 후 재삽입 (재실행 안전성)
main_df = main_df[main_df['account_nm'] != '무형자산'].copy()

result_df = pd.concat([main_df, new_df], ignore_index=True)
result_df = result_df.sort_values(by=['corp_name', 'bsns_year', 'account_nm'],
                                   ascending=[True, False, True])
result_df = result_df.reset_index(drop=True)

result_df.to_csv(main_file, index=False, encoding='utf-8-sig')

report = []
report.append('추가된 무형자산 행 수: ' + str(len(new_df)))
report.append('병합 전 총 행 수: ' + str(len(main_df)))
report.append('병합 후 총 행 수: ' + str(len(result_df)))
report.append('무형자산 회사 수 (중복 제외): ' + str(new_df['corp_name'].nunique()))
report_text = '\n'.join(report)
print(report_text)
with open(r'C:\Users\willo\Desktop\코딩\프로젝트4\무형자산병합_결과.txt', 'w', encoding='utf-8') as f:
    f.write(report_text)
