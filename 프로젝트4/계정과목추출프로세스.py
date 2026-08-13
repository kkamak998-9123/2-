# -*- coding: utf-8 -*-
"""
계정과목 자동 추출 프로세스
"""

import pandas as pd
import re
from datetime import datetime

csv_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\kodex_semiconductor_statements.csv'
df = pd.read_csv(csv_file)

def norm(s):
    if pd.isna(s): return ''
    return s.replace(' ', '')

# ============================================================================
# 설정: 여기서 추출할 계정과목을 정의
# ============================================================================

TARGET_ACCOUNT = {
    'name': '매출액',
    'patterns': [
        r'매출액',  # 정확 일치
    ],
    'regex': True
}

# ============================================================================

print("=" * 100)
print(f"계정과목 추출: {TARGET_ACCOUNT['name']}")
print("=" * 100)

# 손익계산서(IS) 필터링
is_df = df[df['sj_div'] == 'IS'].copy()

def norm(s):
    if pd.isna(s): return ''
    return s.replace(' ', '')

# 매칭되는 계정과목 찾기
print(f"\n[Step 1] 계정과목 검색")
print("-" * 100)

matching_accounts = []
for acc in sorted(set(is_df['account_nm'].unique())):
    norm_acc = norm(acc)
    found = False

    for pattern in TARGET_ACCOUNT['patterns']:
        if TARGET_ACCOUNT['regex']:
            if re.search(pattern, norm_acc):
                found = True
                break
        else:
            if norm_acc == pattern:
                found = True
                break

    if found:
        matching_accounts.append(acc)
        print(f"  [O] {acc}")

print(f"\n매칭된 계정과목: {len(matching_accounts)}개")

# 회사별 확인
print(f"\n[Step 2] 회사별 추출 검증")
print("-" * 100)

companies = sorted(is_df['corp_name'].unique())
extraction_log = []
found_count = 0

for company in companies:
    company_is = is_df[is_df['corp_name'] == company]
    found = False
    found_acc = None

    for acc in company_is['account_nm'].unique():
        norm_acc = norm(acc)
        for pattern in TARGET_ACCOUNT['patterns']:
            if TARGET_ACCOUNT['regex']:
                if re.search(pattern, norm_acc):
                    found = True
                    found_acc = acc
                    found_count += 1
                    break
            else:
                if norm_acc == pattern:
                    found = True
                    found_acc = acc
                    found_count += 1
                    break
        if found:
            break

    status = "O" if found else "X"
    extraction_log.append({
        '기업명': company,
        '상태': status,
        '계정과목': found_acc or 'N/A'
    })

    marker = "" if found else " [미추출]"
    print(f"{company:<25} {status}{marker}")

# 요약
extraction_rate = (found_count / len(companies)) * 100
print(f"\n[Step 3] 추출률 검증")
print("-" * 100)
print(f"추출 기업: {found_count}/{len(companies)} ({extraction_rate:.1f}%)")

if extraction_rate >= 90:
    print(f"[OK] 90% 이상 추출됨 (진행)")

    # 미추출 기업 기록
    missing = [r for r in extraction_log if r['상태'] == 'X']
    if missing:
        print(f"\n⚠️  미추출 기업 ({len(missing)}개):")
        for r in missing:
            print(f"  - {r['기업명']}")
else:
    print(f"✗ 90% 미만 (중단)")
    exit(1)

# 데이터 추출 및 저장
print(f"\n[Step 4] 데이터 추출")
print("-" * 100)

extracted_rows = []
for idx, row in is_df.iterrows():
    norm_acc = norm(row['account_nm'])
    for pattern in TARGET_ACCOUNT['patterns']:
        if TARGET_ACCOUNT['regex']:
            if re.search(pattern, norm_acc):
                extracted_rows.append(row)
                break
        else:
            if norm_acc == pattern:
                extracted_rows.append(row)
                break

result_df = pd.DataFrame(extracted_rows)
result_df = result_df.sort_values(by=['corp_name', 'bsns_year'], ascending=[True, False])
result_df = result_df.reset_index(drop=True)

# 계정과목명 통일
result_df['account_nm'] = TARGET_ACCOUNT['name']

print(f"추출된 행: {len(result_df)}행")

# 중복 확인
print(f"\n[Step 5] 중복 검증")
print("-" * 100)

dup_companies = []
for company in companies:
    company_data = result_df[result_df['corp_name'] == company]
    if len(company_data) != 3:
        dup_companies.append((company, len(company_data)))
        print(f"{company:<25} {len(company_data)}행 [!]")

if not dup_companies:
    print(f"✓ 모든 기업이 정확히 3행씩 추출됨")

# 임시 파일로 저장
temp_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_' + TARGET_ACCOUNT['name'] + '.csv'
result_df.to_csv(temp_file, index=False, encoding='utf-8-sig')

print(f"\n[결과]")
print("-" * 100)
print(f"임시 파일: {temp_file}")
print(f"추출: {len(result_df)}행 | 추출률: {extraction_rate:.1f}%")
if dup_companies:
    print(f"중복: {len(dup_companies)}개 기업")
if missing:
    print(f"미추출: {len(missing)}개 기업")

print("\n" + "=" * 100)
