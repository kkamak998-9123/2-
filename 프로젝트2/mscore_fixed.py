# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

statements = pd.read_csv('kospi100_statements_final_v13_complete.csv', encoding='utf-8-sig')
depreciation = pd.read_csv('kospi100_depreciation_notes.csv', encoding='utf-8-sig')

print("M-SCORE CALCULATION (IMPROVED ACCOUNT MATCHING)")
print("=" * 80)
print()

dep_corps = depreciation['corp_code'].unique()

def find_sales_account(corp_data):
    """
    매출 관련 계정 찾기 (다양한 계정명 지원)
    """
    # 손익계산서 데이터만
    is_data = corp_data[corp_data['sj_div'] == 'IS']

    if len(is_data) == 0:
        return None, None

    # 계정명 패턴들 (우선순위 높은 순)
    patterns = [
        '매출액',      # 기본
        '^매출$',      # 정확히 "매출"만
        '^수익$',      # 정확히 "수익"만
        '매출',        # "매출" 포함
        '수익',        # "수익" 포함
    ]

    for pattern in patterns:
        matches = is_data[is_data['account_nm'].str.contains(pattern, regex=True, na=False)]
        if len(matches) > 0:
            return matches.iloc[0], pattern

    return None, None

# M-Score 계산
mscore_results = []
detailed_failures = []

for corp_code in dep_corps:
    try:
        corp_data = statements[statements['corp_code'] == corp_code]

        if len(corp_data) == 0:
            detailed_failures.append({
                'corp_code': corp_code,
                'corp_name': 'UNKNOWN',
                'reason': 'No statement data'
            })
            continue

        corp_name = corp_data['corp_name'].iloc[0]

        # 감가상각비 확인
        d25 = depreciation[(depreciation['corp_code'] == corp_code) &
                           (depreciation['period'] == '20250101-20251231')]
        d24 = depreciation[(depreciation['corp_code'] == corp_code) &
                           (depreciation['period'] == '20240101-20241231')]

        if len(d25) == 0 or len(d24) == 0:
            detailed_failures.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': f'Missing depreciation data (2025: {len(d25)}, 2024: {len(d24)})'
            })
            continue

        depr25 = d25.iloc[0]['depreciation_expense']
        depr24 = d24.iloc[0]['depreciation_expense']

        if pd.isna(depr25) or pd.isna(depr24) or depr25 <= 0:
            detailed_failures.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': f'Invalid depreciation values'
            })
            continue

        # 매출액 찾기 (개선된 매칭)
        sales_row, matched_pattern = find_sales_account(corp_data)

        if sales_row is None:
            detailed_failures.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': 'No income statement or sales account found'
            })
            continue

        s25 = sales_row['thstrm_amount_current']
        s24 = sales_row['frmtrm_amount_prior']

        if pd.isna(s25) or pd.isna(s24) or s25 <= 0 or s24 <= 0:
            detailed_failures.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'reason': f'Invalid sales values (2025: {s25}, 2024: {s24})'
            })
            continue

        # M-Score 계산
        sgi = s25 / s24
        depi = depr24 / depr25
        m_score = -4.40 + (0.892 * sgi) - (0.115 * depi)
        is_risk = "HIGH" if m_score > -1.78 else "LOW"

        mscore_results.append({
            'corp_name': corp_name,
            'corp_code': corp_code,
            'account_name_used': sales_row['account_nm'],
            'sales_2025': int(s25),
            'sales_2024': int(s24),
            'depr_2025': int(depr25),
            'depr_2024': int(depr24),
            'sgi': round(sgi, 4),
            'depi': round(depi, 4),
            'm_score': round(m_score, 4),
            'risk_flag': is_risk
        })

    except Exception as e:
        detailed_failures.append({
            'corp_code': corp_code,
            'corp_name': corp_data['corp_name'].iloc[0] if len(corp_data) > 0 else 'UNKNOWN',
            'reason': f'Exception: {str(e)}'
        })

print(f"SUCCESS: {len(mscore_results)} companies")
print(f"FAILED: {len(detailed_failures)} companies")
print()

if len(mscore_results) > 0:
    df = pd.DataFrame(mscore_results)
    df_sorted = df.sort_values('m_score', ascending=False)
    df.to_csv('kospi100_mscore_fixed.csv', index=False, encoding='utf-8-sig')

    high_risk = (df_sorted['m_score'] > -1.78).sum()
    low_risk = (df_sorted['m_score'] <= -1.78).sum()

    print(f"Risk Distribution:")
    print(f"  HIGH RISK: {high_risk}")
    print(f"  LOW RISK: {low_risk}")
    print()

    print("TOP 15 BY M-SCORE")
    print("-" * 80)
    for i, (idx, row) in enumerate(df_sorted.head(15).iterrows(), 1):
        print(f"{i:2d}. {row['corp_name']:20s} | SGI:{row['sgi']:6.3f} | DEPI:{row['depi']:6.3f} | Score:{row['m_score']:8.4f}")

print()
print("FAILED COMPANIES:")
print("-" * 80)

if len(detailed_failures) > 0:
    fail_df = pd.DataFrame(detailed_failures)
    fail_df.to_csv('kospi100_mscore_failed_fixed.csv', index=False, encoding='utf-8-sig')

    for idx, row in fail_df.iterrows():
        print(f"  {row['corp_name']:20s} - {row['reason']}")

    print()
    print(f"Failure details saved to: kospi100_mscore_failed_fixed.csv")
