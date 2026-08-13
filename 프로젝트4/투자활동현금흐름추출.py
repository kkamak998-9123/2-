# -*- coding: utf-8 -*-
"""
투자활동현금흐름 계정과목 검증 및 추출
"""

import pandas as pd
import re

csv_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\kodex_semiconductor_statements.csv'
df = pd.read_csv(csv_file)

def norm(s):
    if pd.isna(s): return ''
    return s.replace(' ', '')

# 현금흐름표(CF) 필터링
cf_df = df[df['sj_div'] == 'CF'].copy()

# 정규식 패턴
regex_pattern = r'투자활동.*현금흐름'

print("=" * 80)
print("투자활동현금흐름 계정과목 검증")
print("=" * 80)

print(f"\n[검색 패턴]")
print(f"  정규식: r'{regex_pattern}'")
print(f"  의미: 투자활동 + (아무글자 0개 이상) + 현금흐름")

# CF 계정과목 중 매칭되는 것 찾기
cf_accounts = sorted(set(cf_df['account_nm'].unique()))
matching_accounts = []

print(f"\n[CF 계정과목 중 매칭 항목]")
print("-" * 80)
for acc in cf_accounts:
    norm_acc = norm(acc)
    if re.search(regex_pattern, norm_acc):
        matching_accounts.append(acc)
        print(f"  [O] {acc}")

print(f"\n매칭된 계정과목: {len(matching_accounts)}개")

# 회사별 확인
print(f"\n[회사별 검증]")
print("-" * 80)

companies = sorted(cf_df['corp_name'].unique())
results = []
found_total = 0

for company in companies:
    company_cf = cf_df[cf_df['corp_name'] == company]
    found = False
    found_acc = None

    for acc in company_cf['account_nm'].unique():
        norm_acc = norm(acc)
        if re.search(regex_pattern, norm_acc):
            found = True
            found_acc = acc
            found_total += 1
            break

    status = "O" if found else "X"
    results.append({'기업명': company, '상태': status, '계정과목': found_acc or 'N/A'})
    print(f"{company:<25} {status}  {found_acc or 'N/A'}")

# 요약
print(f"\n[검증 결과]")
print("-" * 80)
print(f"검출 기업: {found_total}/35 ({found_total/35*100:.1f}%)")

if found_total < 35:
    print(f"\n⚠️ 투자활동현금흐름이 없는 기업:")
    for r in results:
        if r['상태'] == 'X':
            print(f"  - {r['기업명']}")

# 추출 및 저장
if found_total > 0:
    print(f"\n[데이터 추출 중...]")

    extracted_rows = []
    for idx, row in cf_df.iterrows():
        norm_acc = norm(row['account_nm'])
        if re.search(regex_pattern, norm_acc):
            extracted_rows.append(row)

    result_df = pd.DataFrame(extracted_rows)
    result_df = result_df.sort_values(by=['corp_name', 'bsns_year'], ascending=[True, False])
    result_df = result_df.reset_index(drop=True)

    # 계정과목명 통일
    result_df['account_nm'] = '투자활동현금흐름'

    output_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_투자활동현금흐름.csv'
    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"[OK] 추출 완료: {len(result_df)}행")
    print(f"[OK] 저장: {output_file}")

    print(f"\n[샘플 데이터]")
    print("-" * 80)
    print(result_df[['corp_name', 'bsns_year', 'account_nm', 'thstrm_amount']].head(10).to_string())

print("\n" + "=" * 80)
