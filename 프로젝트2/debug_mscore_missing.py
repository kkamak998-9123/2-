# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

statements = pd.read_csv('kospi100_statements_final_v13_complete.csv', encoding='utf-8-sig')
depreciation = pd.read_csv('kospi100_depreciation_notes.csv', encoding='utf-8-sig')

# 감가상각비 있는 기업들
dep_corps = depreciation['corp_code'].unique()

# M-Score 계산된 기업들 확인
mscore_success = []
mscore_failed = []

print("DETAILED ANALYSIS OF M-SCORE CALCULATION")
print("=" * 100)
print()

for corp_code in dep_corps:
    try:
        corp_data = statements[statements['corp_code'] == corp_code]

        if len(corp_data) == 0:
            mscore_failed.append({
                'corp_code': corp_code,
                'corp_name': 'UNKNOWN',
                'reason': 'No financial statement data'
            })
            continue

        corp_name = corp_data['corp_name'].iloc[0]

        # 감가상각비 데이터 확인
        d25 = depreciation[(depreciation['corp_code'] == corp_code) &
                           (depreciation['period'] == '20250101-20251231')]
        d24 = depreciation[(depreciation['corp_code'] == corp_code) &
                           (depreciation['period'] == '20240101-20241231')]

        if len(d25) == 0:
            mscore_failed.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': 'Missing 2025 depreciation data'
            })
            continue

        if len(d24) == 0:
            mscore_failed.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': 'Missing 2024 depreciation data'
            })
            continue

        depr25 = d25.iloc[0]['depreciation_expense']
        depr24 = d24.iloc[0]['depreciation_expense']

        if pd.isna(depr25) or pd.isna(depr24):
            mscore_failed.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': f'Depreciation value is NaN (2025: {depr25}, 2024: {depr24})'
            })
            continue

        # 매출액 데이터 확인
        sales_data = corp_data[corp_data['account_nm'].str.contains('매출액', na=False)]

        if len(sales_data) == 0:
            mscore_failed.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': 'No sales data found in statements'
            })
            continue

        row = sales_data.iloc[0]
        s25 = row['thstrm_amount_current']
        s24 = row['frmtrm_amount_prior']

        if pd.isna(s25):
            mscore_failed.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': f'2025 Sales is NaN'
            })
            continue

        if pd.isna(s24):
            mscore_failed.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': f'2024 Sales is NaN'
            })
            continue

        if s24 <= 0:
            mscore_failed.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': f'2024 Sales is zero or negative ({s24})'
            })
            continue

        if s25 <= 0:
            mscore_failed.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': f'2025 Sales is zero or negative ({s25})'
            })
            continue

        if depr25 <= 0:
            mscore_failed.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': f'2025 Depreciation is zero or negative ({depr25})'
            })
            continue

        # 모든 조건 충족
        mscore_success.append(corp_name)

    except Exception as e:
        mscore_failed.append({
            'corp_code': corp_code,
            'corp_name': corp_data['corp_name'].iloc[0] if len(corp_data) > 0 else 'UNKNOWN',
            'reason': f'Exception: {str(e)}'
        })

print(f"SUCCESS: {len(mscore_success)} companies")
print(f"FAILED: {len(mscore_failed)} companies")
print()

if len(mscore_failed) > 0:
    print("FAILED COMPANIES AND REASONS:")
    print("=" * 100)

    failed_df = pd.DataFrame(mscore_failed)

    # 이유별로 그룹화
    reason_groups = failed_df.groupby('reason')

    for reason, group in reason_groups:
        print(f"\n[{reason}] - {len(group)} companies")
        print("-" * 100)
        for idx, row in group.iterrows():
            print(f"  - {row['corp_name']} ({row['corp_code']})")

    # 파일로 저장
    failed_df.to_csv('kospi100_mscore_failed.csv', index=False, encoding='utf-8-sig')
    print()
    print("=" * 100)
    print("Failed companies saved to: kospi100_mscore_failed.csv")
