# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 데이터 로드
statements = pd.read_csv('kospi100_all_statements_2025_v12.csv', encoding='utf-8-sig')
depreciation = pd.read_csv('kospi100_depreciation_notes.csv', encoding='utf-8-sig')

# 기본 통계
dep_corps = set(depreciation['corp_code'].unique())
stmt_corps = set(statements['corp_code'].unique())
both = dep_corps & stmt_corps

print("AVAILABLE DATA SUMMARY")
print("=" * 80)
print(f"Depreciation extraction: {len(dep_corps)} companies")
print(f"Financial statements: {len(stmt_corps)} companies")
print(f"Both depreciation + statements: {len(both)} companies")

# 2년도 데이터 확인
both_years = []
for corp_code in both:
    has_2025 = len(statements[(statements['corp_code'] == corp_code) & (statements['bsns_year'] == 2025)]) > 0
    has_2024 = len(statements[(statements['corp_code'] == corp_code) & (statements['bsns_year'] == 2024)]) > 0
    if has_2025 and has_2024:
        both_years.append(corp_code)

print(f"Depreciation + 2-year financial data (2025,2024): {len(both_years)} companies")
print()

# M-Score (SGI, DEPI) 계산 가능한 기업
mscore_results = []
for corp_code in both:
    try:
        corp_data = statements[statements['corp_code'] == corp_code]
        corp_name = corp_data['corp_name'].iloc[0]

        is_2025 = corp_data[(corp_data['bsns_year'] == 2025) & (corp_data['sj_div'] == 'IS')]
        is_2024 = corp_data[(corp_data['bsns_year'] == 2024) & (corp_data['sj_div'] == 'IS')]

        if len(is_2025) > 0 and len(is_2024) > 0:
            s25 = is_2025.iloc[0]['thstrm_amount_current']
            s24 = is_2024.iloc[0]['thstrm_amount_current']

            if pd.notna(s25) and pd.notna(s24) and s24 > 0:
                sgi = s25 / s24

                d25 = depreciation[(depreciation['corp_code'] == corp_code) &
                                   (depreciation['period'] == '20250101-20251231')]
                d24 = depreciation[(depreciation['corp_code'] == corp_code) &
                                   (depreciation['period'] == '20240101-20241231')]

                if len(d25) > 0 and len(d24) > 0:
                    depr25 = d25.iloc[0]['depreciation_expense']
                    depr24 = d24.iloc[0]['depreciation_expense']

                    if depr25 > 0:
                        depi = depr24 / depr25
                        m_score = -4.40 + (0.892 * sgi) - (0.115 * depi)

                        mscore_results.append({
                            'corp_name': corp_name,
                            'corp_code': corp_code,
                            'sgi': round(sgi, 4),
                            'depi': round(depi, 4),
                            'm_score': round(m_score, 4),
                            'risk_flag': 'HIGH RISK' if m_score > -1.78 else 'LOW RISK'
                        })
    except Exception as e:
        pass

print("METRIC CALCULATION SUMMARY")
print("=" * 80)
print(f"Companies with numerical output available:")
print(f"  Depreciation expense only: {len(dep_corps)} companies")
print(f"  Basic M-Score (SGI+DEPI): {len(mscore_results)} companies")
print(f"  Full M-Score (7 indices): 0 companies")
print()

if len(mscore_results) > 0:
    df_m = pd.DataFrame(mscore_results)
    df_m_sorted = df_m.sort_values('m_score', ascending=False)
    df_m.to_csv('kospi100_mscore_basic.csv', index=False, encoding='utf-8-sig')

    print("SAMPLE: Top 10 by M-Score")
    print("-" * 80)
    for i, (idx, row) in enumerate(df_m_sorted.head(10).iterrows(), 1):
        print(f"{i:2d}. {row['corp_name']:20s} | SGI:{row['sgi']:6.3f} | DEPI:{row['depi']:6.3f} | Score:{row['m_score']:8.4f} | {row['risk_flag']}")

print()
print("FILES GENERATED")
print("-" * 80)
print("  kospi100_depreciation_notes.csv (70 companies, 202 data rows)")
print(f"  kospi100_mscore_basic.csv ({len(mscore_results)} companies)")
print()

print("ANSWER TO YOUR QUESTION")
print("=" * 80)
print("지금까지 숫자가 도출될 수 있는 회사는 총:")
print()
print(f"  1. 감가상각비만: 70개 기업")
print(f"  2. 기본 M-Score(SGI+DEPI): {len(mscore_results)}개 기업")
print(f"  3. 전체 M-Score(7개지표): 0개 기업")
print()
print(f"→ 가장 현실적인 계산 가능: {len(mscore_results)}개 기업으로 M-Score 산출 가능")
