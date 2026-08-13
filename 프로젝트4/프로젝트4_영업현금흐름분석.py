import pandas as pd
import re

df = pd.read_csv(r'C:\Users\willo\Desktop\코딩\프로젝트4\kodex_semiconductor_statements.csv')
cf = df[df['sj_div'] == 'CF'].copy()

def norm(s):
    if pd.isna(s): return ''
    return s.replace(' ', '')

# 검색 조건
simple_targets = ['영업활동현금흐름', '영업활동순현금흐름']
regex_pattern = r'영업활동으로인한.*현금흐름'
simple_targets_norm = set(norm(t) for t in simple_targets)

print("=" * 80)
print("영업활동현금흐름 계정과목 검증")
print("=" * 80)

print(f"\n[검색 조건]")
print(f"1. {simple_targets[0]}")
print(f"2. {simple_targets[1]}")
print(f"3. 정규식: r'{regex_pattern}'")

print("\n[CF 계정과목 중 매칭되는 항목]")
cf_accounts = sorted(set(cf['account_nm'].unique()))
matching_accounts = []
for acc in cf_accounts:
    norm_acc = norm(acc)
    # 단순 매칭 또는 정규식 매칭
    if norm_acc in simple_targets_norm or re.search(regex_pattern, norm_acc):
        matching_accounts.append(acc)
        match_type = "정규식" if re.search(regex_pattern, norm_acc) else "정확일치"
        print(f"  [O] {acc:<50} ({match_type})")

print(f"\n매칭된 계정과목: {len(matching_accounts)}개")

print("\n[회사별 확인]")
print("-" * 80)
found_total = 0
for company in sorted(cf['corp_name'].unique()):
    accounts = cf[cf['corp_name'] == company]['account_nm'].unique()
    found = False
    found_acc = None
    for acc in accounts:
        norm_acc = norm(acc)
        if norm_acc in simple_targets_norm or re.search(regex_pattern, norm_acc):
            found = True
            found_acc = acc
            found_total += 1
            break
    status = "O" if found else "X"
    print(f"{company:<25} {status}  {found_acc or 'N/A'}")

print(f"\n[최종 결과] {found_total}/35 기업에서 영업활동현금흐름 발견 ({found_total/35*100:.1f}%)")
print("=" * 80)
