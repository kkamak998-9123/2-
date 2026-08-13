# -*- coding: utf-8 -*-
"""
개선된 계정과목 추출 프로세스 v2
- IS, CIS 폴백 지원
- 광범위 패턴 → 점진적 좁혀가기
"""

import pandas as pd
import re

csv_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\kodex_semiconductor_statements.csv'
df = pd.read_csv(csv_file)

def norm(s):
    if pd.isna(s): return ''
    return s.replace(' ', '')

# ============================================================================
# 설정: 추출할 계정과목
# ============================================================================

TARGET = {
    'name': '매출액',
    'patterns': [
        r'^매출$',            # 정확히 "매출" (가장 좁음)
        r'^매출액',           # "매출액"으로 시작
        r'^매출',             # "매출"로 시작
        r'매출',              # "매출" 포함 (가장 넓음)
    ],
    'sj_divs': ['IS', 'CIS']  # 손익계산서, 포괄손익계산서
}

# ============================================================================

print("=" * 100)
print(f"계정과목 추출: {TARGET['name']} (v2 - 유연한 접근)")
print("=" * 100)

# Step 1: 데이터 로드
print(f"\n[Step 0] 데이터 로드")
print("-" * 100)

# IS 또는 CIS 데이터
data_df = df[df['sj_div'].isin(TARGET['sj_divs'])].copy()
print(f"손익계산서 데이터: {len(data_df)}행")
print(f"포함 기업: {data_df['corp_name'].nunique()}개")
print(f"분류: IS={len(df[df['sj_div']=='IS'])}행, CIS={len(df[df['sj_div']=='CIS'])}행")

# Step 2: 광범위 → 좁혀가기
print(f"\n[Step 1] 패턴별 매칭 시도 (광범위 → 좁음)")
print("-" * 100)

best_pattern = None
best_accounts = []
best_count = 0

for pattern_idx, pattern in enumerate(TARGET['patterns'], 1):
    matching = []
    for acc in sorted(set(data_df['account_nm'].unique())):
        norm_acc = norm(acc)
        if re.search(pattern, norm_acc):
            matching.append(acc)

    coverage = len(matching)
    print(f"\n패턴 {pattern_idx}: r'{pattern}'")
    print(f"  매칭 계정: {len(matching)}개")
    for acc in matching[:5]:  # 최대 5개만 표시
        print(f"    - {acc}")
    if len(matching) > 5:
        print(f"    ... 외 {len(matching) - 5}개")

    if len(matching) > 0:
        best_pattern = pattern
        best_accounts = matching
        best_count = len(matching)
        break  # 첫 번째로 매칭된 패턴 사용

print(f"\n최종 선택 패턴: r'{best_pattern}'")
print(f"최종 계정과목: {best_count}개")

# Step 3: 회사별 확인
print(f"\n[Step 2] 회사별 추출 검증")
print("-" * 100)

companies = sorted(data_df['corp_name'].unique())
found_count = 0
missing_companies = []

for company in companies:
    company_data = data_df[data_df['corp_name'] == company]
    found = False

    for acc in company_data['account_nm'].unique():
        norm_acc = norm(acc)
        if re.search(best_pattern, norm_acc):
            found = True
            found_count += 1
            break

    status = "O" if found else "X"
    if not found:
        missing_companies.append(company)

    marker = "" if found else " [미추출]"
    if not found:  # 미추출만 표시
        print(f"{company:<25} {status}{marker}")

if not missing_companies:
    print(f"전체 기업: 모두 추출 [O]")

# Step 4: 추출률 검증
extraction_rate = (found_count / len(companies)) * 100
print(f"\n[Step 3] 추출률 검증")
print("-" * 100)
print(f"추출 기업: {found_count}/{len(companies)} ({extraction_rate:.1f}%)")

if extraction_rate >= 90:
    print(f"[OK] 90% 이상 추출됨 (진행)")

    if missing_companies:
        print(f"\n미추출 기업 ({len(missing_companies)}개):")
        for comp in missing_companies:
            print(f"  - {comp}")
else:
    print(f"[NO] 90% 미만 (중단)")
    exit(1)

# Step 5: 데이터 추출
print(f"\n[Step 4] 데이터 추출")
print("-" * 100)

extracted_rows = []
for idx, row in data_df.iterrows():
    norm_acc = norm(row['account_nm'])
    if re.search(best_pattern, norm_acc):
        extracted_rows.append(row)

result_df = pd.DataFrame(extracted_rows)
result_df = result_df.sort_values(by=['corp_name', 'bsns_year'], ascending=[True, False])
result_df = result_df.reset_index(drop=True)

# 계정과목명 통일
result_df['account_nm'] = TARGET['name']

print(f"추출된 행: {len(result_df)}행")

# Step 6: 중복 검증
print(f"\n[Step 5] 중복 및 누락 검증")
print("-" * 100)

issues = []
for company in companies:
    company_data = result_df[result_df['corp_name'] == company]
    count = len(company_data)

    if count != 3:
        issues.append((company, count))
        print(f"{company:<25} {count}행 [!]")

if not issues:
    print(f"모든 기업이 정확히 3행씩 추출됨 [OK]")

# 결과 저장
temp_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_' + TARGET['name'] + '.csv'
result_df.to_csv(temp_file, index=False, encoding='utf-8-sig')

print(f"\n[결과]")
print("-" * 100)
print(f"임시 파일: {temp_file}")
print(f"추출: {len(result_df)}행 | 추출률: {extraction_rate:.1f}%")
if issues:
    print(f"중복/누락: {len(issues)}개 기업")
if missing_companies:
    print(f"미추출: {len(missing_companies)}개 기업")
else:
    print(f"미추출: 없음")

print("\n" + "=" * 100)
