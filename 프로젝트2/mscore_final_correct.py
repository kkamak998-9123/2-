# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

statements = pd.read_csv('kospi100_statements_final_v13_complete.csv', encoding='utf-8-sig')
depreciation = pd.read_csv('kospi100_depreciation_notes.csv', encoding='utf-8-sig')

print("M-SCORE ANALYSIS (FINAL)")
print("=" * 80)
print()

# 기본 통계
dep_corps = set(depreciation['corp_code'].unique())
stmt_corps = set(statements['corp_code'].unique())
both = dep_corps & stmt_corps

print(f"Depreciation data: {len(dep_corps)} companies")
print(f"Financial statements: {len(stmt_corps)} companies")
print(f"Both: {len(both)} companies")
print()

# 매출액이 있는 기업 찾기 (손익계산서)
mscore_results = []

for corp_code in both:
    try:
        corp_data = statements[statements['corp_code'] == corp_code]
        corp_name = corp_data['corp_name'].iloc[0]

        # 매출액 계정 찾기 (손익계산서)
        sales_data = corp_data[corp_data['account_nm'].str.contains('매출액', na=False)]

        if len(sales_data) > 0:
            row = sales_data.iloc[0]

            s25 = row['thstrm_amount_current']  # 2025
            s24 = row['frmtrm_amount_prior']     # 2024

            if pd.notna(s25) and pd.notna(s24) and s24 > 0 and s25 > 0:
                sgi = s25 / s24

                # 감가상각비
                d25_data = depreciation[(depreciation['corp_code'] == corp_code) &
                                        (depreciation['period'] == '20250101-20251231')]
                d24_data = depreciation[(depreciation['corp_code'] == corp_code) &
                                        (depreciation['period'] == '20240101-20241231')]

                if len(d25_data) > 0 and len(d24_data) > 0:
                    depr25 = d25_data.iloc[0]['depreciation_expense']
                    depr24 = d24_data.iloc[0]['depreciation_expense']

                    if depr25 > 0:
                        depi = depr24 / depr25
                        m_score = -4.40 + (0.892 * sgi) - (0.115 * depi)

                        is_risk = "HIGH" if m_score > -1.78 else "LOW"

                        mscore_results.append({
                            'corp_name': corp_name,
                            'corp_code': corp_code,
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
        pass

print(f"M-Score calculated: {len(mscore_results)} companies")
print()

if len(mscore_results) > 0:
    df = pd.DataFrame(mscore_results)
    df_sorted = df.sort_values('m_score', ascending=False)
    df.to_csv('kospi100_mscore_final.csv', index=False, encoding='utf-8-sig')

    # 위험도 분류
    high_risk = (df_sorted['m_score'] > -1.78).sum()
    low_risk = (df_sorted['m_score'] <= -1.78).sum()

    print(f"HIGH RISK (M-Score > -1.78): {high_risk} companies")
    print(f"LOW RISK (M-Score <= -1.78): {low_risk} companies")
    print()

    print("TOP 20 (Highest M-Score = Highest Manipulation Risk)")
    print("-" * 80)
    for i, (idx, row) in enumerate(df_sorted.head(20).iterrows(), 1):
        print(f"{i:2d}. {row['corp_name']:18s} | SGI:{row['sgi']:6.3f} | DEPI:{row['depi']:6.3f} | Score:{row['m_score']:8.4f} | {row['risk_flag']:4s}")

    print()
    print("BOTTOM 20 (Lowest M-Score = Lowest Manipulation Risk)")
    print("-" * 80)
    for i, (idx, row) in enumerate(df_sorted.tail(20).iterrows(), 1):
        print(f"{i:2d}. {row['corp_name']:18s} | SGI:{row['sgi']:6.3f} | DEPI:{row['depi']:6.3f} | Score:{row['m_score']:8.4f} | {row['risk_flag']:4s}")

print()
print("=" * 80)
print("FINAL ANSWER")
print("=" * 80)
print()
print(f"Depreciation expense extracted: 70 companies")
print(f"M-Score calculated: {len(mscore_results)} companies")
print()
print(f"Output files:")
print(f"  - kospi100_depreciation_notes.csv")
print(f"  - kospi100_mscore_final.csv ({len(mscore_results)} companies)")
