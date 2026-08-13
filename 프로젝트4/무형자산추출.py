# -*- coding: utf-8 -*-
"""
무형자산 추출 (기업 x 연도 x fs_div 단위)

규칙:
1. '무형자산'(또는 '3. 무형자산') 단독 존재 -> 그 값 사용
2. '무형자산 및 영업권' / '무형자산과 영업권 합계' 같은 합산 계정 존재 -> 그 값 그대로 사용 (영업권 포함)
3. '영업권 이외의 무형자산' / '영업권외무형자산'처럼 영업권 제외를 명시한 계정 존재
   -> 같은 기업/연도/fs_div의 '영업권' 금액을 더함
"""

import pandas as pd

df = pd.read_csv(r'C:\Users\willo\Desktop\코딩\프로젝트4\kodex_semiconductor_statements.csv')
bs = df[df['sj_div'] == 'BS'].copy()


def norm(s):
    if pd.isna(s):
        return ''
    return str(s).replace(' ', '')


bs['norm'] = bs['account_nm'].apply(norm)

STANDALONE = {'무형자산', '3.무형자산'}
COMBINED = {'무형자산및영업권', '무형자산과영업권합계'}
EXCL_GOODWILL = {'영업권이외의무형자산', '영업권외무형자산'}
GOODWILL = {'영업권', '영업권,총액'}

results = []
issues = []

for (corp, year, fsdiv), g in bs.groupby(['corp_name', 'bsns_year', 'fs_div']):
    standalone = g[g['norm'].isin(STANDALONE)]
    combined = g[g['norm'].isin(COMBINED)]
    excl = g[g['norm'].isin(EXCL_GOODWILL)]
    goodwill = g[g['norm'].isin(GOODWILL)]

    matches = int(len(standalone) > 0) + int(len(combined) > 0) + int(len(excl) > 0)
    if matches == 0:
        continue
    if matches > 1:
        issues.append((corp, year, fsdiv, 'MULTI-CASE-MATCH', list(g['account_nm'])))
        continue

    if len(standalone) > 0:
        if len(standalone) > 1:
            issues.append((corp, year, fsdiv, 'DUP-STANDALONE', list(standalone['account_nm'])))
            continue
        val = standalone.iloc[0]['thstrm_amount']
        method = 'standalone'
    elif len(combined) > 0:
        if len(combined) > 1:
            issues.append((corp, year, fsdiv, 'DUP-COMBINED', list(combined['account_nm'])))
            continue
        val = combined.iloc[0]['thstrm_amount']
        method = 'combined'
    else:
        if len(excl) > 1:
            issues.append((corp, year, fsdiv, 'DUP-EXCL', list(excl['account_nm'])))
            continue
        if len(goodwill) == 0:
            issues.append((corp, year, fsdiv, 'EXCL-NO-GOODWILL', list(g['account_nm'])))
            val = excl.iloc[0]['thstrm_amount']
            method = 'excl_no_goodwill_found'
        elif len(goodwill) > 1:
            issues.append((corp, year, fsdiv, 'DUP-GOODWILL', list(goodwill['account_nm'])))
            val = excl.iloc[0]['thstrm_amount'] + goodwill.iloc[0]['thstrm_amount']
            method = 'excl_plus_goodwill_dup'
        else:
            val = excl.iloc[0]['thstrm_amount'] + goodwill.iloc[0]['thstrm_amount']
            method = 'excl_plus_goodwill'

    results.append({'corp_name': corp, 'bsns_year': year, 'fs_div': fsdiv, '무형자산': val, 'method': method})

res_df = pd.DataFrame(results)

report = []
report.append('총 매칭 그룹 수: ' + str(len(res_df)))
report.append('회사 수: ' + str(res_df['corp_name'].nunique()))
report.append('')
report.append('method별 카운트:')
report.append(str(res_df['method'].value_counts()))
report.append('')
report.append('이슈 목록 (' + str(len(issues)) + '개):')
for it in issues:
    report.append(str(it))

report_text = '\n'.join(report)
print(report_text)

with open(r'C:\Users\willo\Desktop\코딩\프로젝트4\무형자산추출_결과.txt', 'w', encoding='utf-8') as f:
    f.write(report_text)

res_df.to_csv(r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_무형자산.csv', index=False, encoding='utf-8-sig')
