# -*- coding: utf-8 -*-
import pandas as pd

statements = pd.read_csv('kospi100_statements_final_v13_complete.csv', encoding='utf-8-sig')

# 샘플 회사 확인
sample_corps = [266961, 126256, 126478]  # NAVER, 삼성생명, 삼성중공업

for corp_code in sample_corps:
    corp_data = statements[statements['corp_code'] == corp_code]

    if len(corp_data) == 0:
        print(f"Corp {corp_code}: NO DATA")
        continue

    corp_name = corp_data['corp_name'].iloc[0]
    print(f"\n{'='*80}")
    print(f"[{corp_name} ({corp_code})]")
    print(f"{'='*80}")

    # 사용 가능한 재무제표 종류 (sj_div)
    print(f"\nAvailable Statement Types (sj_div):")
    for sj_type in corp_data['sj_div'].unique():
        count = len(corp_data[corp_data['sj_div'] == sj_type])
        print(f"  - {sj_type}: {count} rows")

    # 손익계산서 계정명 샘플
    is_data = corp_data[corp_data['sj_div'] == 'IS']
    if len(is_data) > 0:
        print(f"\nIncome Statement (IS) - Sample Accounts:")
        for acc in is_data['account_nm'].unique()[:10]:
            print(f"  - {acc}")

    # 재무상태표 계정명 샘플
    bs_data = corp_data[corp_data['sj_div'] == 'BS']
    if len(bs_data) > 0:
        print(f"\nBalance Sheet (BS) - Sample Accounts:")
        for acc in bs_data['account_nm'].unique()[:15]:
            print(f"  - {acc}")

    # 현금흐름표 계정명 샘플
    cf_data = corp_data[corp_data['sj_div'] == 'CF']
    if len(cf_data) > 0:
        print(f"\nCash Flow (CF) - Sample Accounts:")
        for acc in cf_data['account_nm'].unique()[:10]:
            print(f"  - {acc}")
    else:
        print(f"\nCash Flow (CF): NO DATA")
