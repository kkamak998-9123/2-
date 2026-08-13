# -*- coding: utf-8 -*-
import pandas as pd

statements = pd.read_csv('kospi100_statements_final_v13_complete.csv', encoding='utf-8-sig')

# 실패한 기업들
failed_corps = [1316245, 356361, 120021, 113526, 105952, 139834, 231363, 105873]

print("CHECKING ACCOUNT NAMES IN FAILED COMPANIES")
print("=" * 100)
print()

for corp_code in failed_corps:
    corp_data = statements[statements['corp_code'] == corp_code]

    if len(corp_data) == 0:
        print(f"Corp {corp_code}: NO DATA")
        continue

    corp_name = corp_data['corp_name'].iloc[0]

    # 손익계산서 (IS) 데이터만
    is_data = corp_data[corp_data['sj_div'] == 'IS']

    if len(is_data) == 0:
        print(f"{corp_name} ({corp_code}): NO INCOME STATEMENT DATA")
        print()
        continue

    print(f"[{corp_name} ({corp_code})]")
    print("-" * 100)

    # 모든 계정명 출력 (상위 30개)
    accounts = is_data['account_nm'].unique()[:30]
    for i, acc in enumerate(accounts, 1):
        print(f"  {i:2d}. {acc}")

    # 매출 관련 계정 찾기
    print()
    print("  Searching for sales-related accounts...")
    sales_keywords = ['매출', '수익', 'revenue', 'sales']
    for keyword in sales_keywords:
        matches = corp_data[corp_data['account_nm'].str.contains(keyword, case=False, na=False)]
        if len(matches) > 0:
            print(f"    Found with '{keyword}': {matches['account_nm'].iloc[0]}")

    print()
    print()
