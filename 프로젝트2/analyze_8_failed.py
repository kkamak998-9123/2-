# -*- coding: utf-8 -*-
import pandas as pd

statements = pd.read_csv('kospi100_statements_final_v13_complete.csv', encoding='utf-8-sig')
depreciation = pd.read_csv('kospi100_depreciation_notes.csv', encoding='utf-8-sig')

# 원래 성공한 62개 기업 확인
mscore_successful = []
for corp_code in depreciation['corp_code'].unique():
    try:
        corp_data = statements[statements['corp_code'] == corp_code]
        if len(corp_data) == 0:
            continue

        corp_name = corp_data['corp_name'].iloc[0]

        d25 = depreciation[(depreciation['corp_code'] == corp_code) &
                           (depreciation['period'] == '20250101-20251231')]
        d24 = depreciation[(depreciation['corp_code'] == corp_code) &
                           (depreciation['period'] == '20240101-20241231')]

        if len(d25) == 0 or len(d24) == 0:
            continue

        depr25 = d25.iloc[0]['depreciation_expense']
        depr24 = d24.iloc[0]['depreciation_expense']

        if pd.isna(depr25) or pd.isna(depr24) or depr25 <= 0:
            continue

        # 원래 패턴: 매출액 정확히
        sales_data = corp_data[corp_data['account_nm'].str.contains('매출액', na=False)]

        if len(sales_data) > 0:
            row = sales_data.iloc[0]
            s25 = row['thstrm_amount_current']
            s24 = row['frmtrm_amount_prior']

            if pd.notna(s25) and pd.notna(s24) and s24 > 0 and s25 > 0:
                mscore_successful.append(corp_code)
    except:
        pass

print(f"Originally successful M-Score companies: {len(mscore_successful)}")
print()

# 실패한 8개 확인
all_dep_corps = set(depreciation['corp_code'].unique())
failed_8 = all_dep_corps - set(mscore_successful)

print(f"Failed to calculate: {len(failed_8)} companies")
print()

for corp_code in sorted(failed_8):
    corp_data = statements[statements['corp_code'] == corp_code]

    if len(corp_data) == 0:
        print(f"[CORP {corp_code}] NO STATEMENT DATA")
        continue

    corp_name = corp_data['corp_name'].iloc[0]
    print(f"[{corp_name} ({corp_code})]")

    # 손익계산서 확인
    is_data = corp_data[corp_data['sj_div'] == 'IS']
    print(f"  Income Statement rows: {len(is_data)}")

    if len(is_data) == 0:
        print(f"  -> Reason: NO INCOME STATEMENT DATA")
        print()
        continue

    # 모든 손익계산서 계정 출력
    all_accounts = is_data['account_nm'].unique()
    print(f"  All accounts ({len(all_accounts)} unique):")
    for acc in all_accounts[:15]:
        print(f"    - {acc}")
    if len(all_accounts) > 15:
        print(f"    ... and {len(all_accounts) - 15} more")

    # 매출 관련 계정
    print(f"  Sales-related search:")
    for keyword in ['매출', '수익', 'sales', 'revenue']:
        matches = is_data[is_data['account_nm'].str.contains(keyword, case=False, na=False)]
        if len(matches) > 0:
            print(f"    '{keyword}' found: {matches.iloc[0]['account_nm']}")

    # 첫 번째 계정 (보통 매출액)
    if len(is_data) > 0:
        first_acc = is_data.iloc[0]
        print(f"  First account: {first_acc['account_nm']}")
        print(f"    2025: {first_acc['thstrm_amount_current']}")
        print(f"    2024: {first_acc['frmtrm_amount_prior']}")

    print()
