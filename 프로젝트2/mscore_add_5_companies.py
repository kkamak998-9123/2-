# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

statements = pd.read_csv('kospi100_statements_final_v13_complete.csv', encoding='utf-8-sig')
depreciation = pd.read_csv('kospi100_depreciation_notes.csv', encoding='utf-8-sig')
mscore_existing = pd.read_csv('kospi100_mscore_final.csv', encoding='utf-8-sig')

print("ADDING 5 COMPANIES WITH DIFFERENT ACCOUNT NAMES")
print("=" * 80)
print()

# 기존 성공한 기업들
existing_corps = set(mscore_existing['corp_code'].astype(str))

# 추가할 5개 기업의 계정명 매핑
account_mapping = {
    120021: '영업수익',          # LG
    356361: '매출액 및 용역수입',  # LG화학
    139834: '기본영업수익',        # LG에너지솔루션
    231363: '기본영업이익',        # LG디스플레이
    1316245: '매출액'            # 한섬
}

additional_results = []

for corp_code, target_account in account_mapping.items():
    try:
        corp_code_str = str(corp_code)
        corp_data = statements[statements['corp_code'] == corp_code]

        if len(corp_data) == 0:
            print(f"[{corp_code_str}] No statement data")
            continue

        corp_name = corp_data['corp_name'].iloc[0]

        # 손익계산서만
        is_data = corp_data[corp_data['sj_div'] == 'IS']

        if len(is_data) == 0:
            print(f"[{corp_name}] No income statement")
            continue

        # 계정 찾기
        account_rows = is_data[is_data['account_nm'].str.contains(target_account, na=False)]

        if len(account_rows) == 0:
            # 정확한 매칭 실패시, 계정명이 약간 다를 수 있으니 첫 번째 행 사용
            account_rows = is_data.head(1)
            actual_account = account_rows.iloc[0]['account_nm'] if len(account_rows) > 0 else target_account
            print(f"[{corp_name}] Exact match not found for '{target_account}'")
            print(f"           Using first account instead: '{actual_account}'")
        else:
            actual_account = account_rows.iloc[0]['account_nm']
            print(f"[{corp_name}] Found: '{actual_account}'")

        row = account_rows.iloc[0]
        s25 = row['thstrm_amount_current']
        s24 = row['frmtrm_amount_prior']

        # 감가상각비
        d25 = depreciation[(depreciation['corp_code'] == corp_code) &
                           (depreciation['period'] == '20250101-20251231')]
        d24 = depreciation[(depreciation['corp_code'] == corp_code) &
                           (depreciation['period'] == '20240101-20241231')]

        if len(d25) == 0 or len(d24) == 0:
            print(f"   -> Missing depreciation data")
            print()
            continue

        depr25 = d25.iloc[0]['depreciation_expense']
        depr24 = d24.iloc[0]['depreciation_expense']

        if pd.isna(s25) or pd.isna(s24) or pd.isna(depr25) or pd.isna(depr24):
            print(f"   -> NaN values detected")
            print()
            continue

        if s25 <= 0 or s24 <= 0 or depr25 <= 0:
            print(f"   -> Zero or negative values")
            print()
            continue

        # M-Score 계산
        sgi = s25 / s24
        depi = depr24 / depr25
        m_score = -4.40 + (0.892 * sgi) - (0.115 * depi)
        is_risk = "HIGH" if m_score > -1.78 else "LOW"

        additional_results.append({
            'corp_name': corp_name,
            'corp_code': corp_code,
            'account_name_used': actual_account,
            'sales_2025': int(s25),
            'sales_2024': int(s24),
            'depr_2025': int(depr25),
            'depr_2024': int(depr24),
            'sgi': round(sgi, 4),
            'depi': round(depi, 4),
            'm_score': round(m_score, 4),
            'risk_flag': is_risk
        })

        print(f"   ✓ M-Score: {m_score:.4f} ({is_risk} RISK)")
        print()

    except Exception as e:
        print(f"[{corp_code}] Error: {str(e)}")
        print()

print("=" * 80)
print(f"Successfully added: {len(additional_results)} companies")
print()

if len(additional_results) > 0:
    # 기존 데이터와 병합
    additional_df = pd.DataFrame(additional_results)

    # corp_code를 문자열로 변환 (기존 데이터와 일치시키기 위해)
    mscore_existing['corp_code_str'] = mscore_existing['corp_code'].astype(str)
    additional_df['corp_code_str'] = additional_df['corp_code'].astype(str)

    # 통합
    merged = pd.concat([
        mscore_existing.drop('corp_code_str', axis=1),
        additional_df.drop('corp_code_str', axis=1)
    ], ignore_index=True)

    # 정렬
    merged_sorted = merged.sort_values('m_score', ascending=False)

    # 저장
    merged_sorted.to_csv('kospi100_mscore_complete_final.csv', index=False, encoding='utf-8-sig')

    print(f"Total companies with M-Score: {len(merged_sorted)}")
    print()

    # 통계
    high_risk = (merged_sorted['m_score'] > -1.78).sum()
    low_risk = (merged_sorted['m_score'] <= -1.78).sum()

    print(f"Risk Distribution:")
    print(f"  HIGH RISK: {high_risk}")
    print(f"  LOW RISK: {low_risk}")
    print()

    print("NEW ADDITIONS IN TOP 20:")
    print("-" * 80)
    for i, (idx, row) in enumerate(merged_sorted.head(20).iterrows(), 1):
        marker = "★ NEW" if row['corp_code'] in [120021, 356361, 139834, 231363, 1316245] else "    "
        print(f"{i:2d}. {marker} {row['corp_name']:20s} | SGI:{row['sgi']:6.3f} | DEPI:{row['depi']:6.3f} | Score:{row['m_score']:8.4f}")

    print()
    print("File saved: kospi100_mscore_complete_final.csv")
