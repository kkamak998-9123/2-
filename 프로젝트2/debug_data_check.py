# -*- coding: utf-8 -*-
import pandas as pd

statements = pd.read_csv('kospi100_all_statements_2025_v12.csv', encoding='utf-8-sig')
depreciation = pd.read_csv('kospi100_depreciation_notes.csv', encoding='utf-8-sig')

# 어떤 연도 데이터가 있는지 확인
print("Years in financial statements:")
print(statements['bsns_year'].value_counts().sort_index())
print()

print("Years in depreciation data:")
print(depreciation['period'].value_counts().sort_index())
print()

# 감가상각비 있는 기업들 중 첫 5개 확인
dep_corps = list(depreciation['corp_code'].unique())[:5]
print("First 5 companies with depreciation data:")
for corp in dep_corps:
    years_in_stmt = statements[statements['corp_code'] == corp]['bsns_year'].unique()
    years_in_depr = depreciation[depreciation['corp_code'] == corp]['period'].unique()

    corp_name = statements[statements['corp_code'] == corp]['corp_name'].iloc[0]
    print(f"{corp_name} ({corp})")
    print(f"  Statements: {sorted(years_in_stmt)}")
    print(f"  Depreciation: {sorted(years_in_depr)}")
    print()

# 전체 회사별 2025, 2024 데이터 확인
print("=" * 60)
print("Companies with 2025 and 2024 financial statements:")
print()

both_years_count = 0
for corp_code in depreciation['corp_code'].unique():
    stmt_data = statements[statements['corp_code'] == corp_code]
    has_2025 = 2025 in stmt_data['bsns_year'].values
    has_2024 = 2024 in stmt_data['bsns_year'].values

    if has_2025 and has_2024:
        both_years_count += 1
        corp_name = stmt_data['corp_name'].iloc[0]
        print(f"✓ {corp_name}")

print()
print(f"Total: {both_years_count} companies with both years")
