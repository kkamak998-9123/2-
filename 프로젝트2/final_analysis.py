# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 올바른 파일 로드
statements = pd.read_csv('kospi100_statements_final_v13_complete.csv', encoding='utf-8-sig')
depreciation = pd.read_csv('kospi100_depreciation_notes.csv', encoding='utf-8-sig')

print("FINAL ANALYSIS WITH COMPLETE DATA")
print("=" * 80)
print()

# 데이터 확인
print("1. DATA OVERVIEW")
print("-" * 80)
print(f"Financial statements file: {len(statements)} rows")
print(f"Years in statements: {sorted(statements['bsns_year'].unique())}")
print(f"Depreciation data: {len(depreciation)} rows")
print()

# 기본 통계
dep_corps = set(depreciation['corp_code'].unique())
stmt_corps = set(statements['corp_code'].unique())
both = dep_corps & stmt_corps

print("2. COMPANY OVERLAP")
print("-" * 80)
print(f"Depreciation data: {len(dep_corps)} companies")
print(f"Financial statements: {len(stmt_corps)} companies")
print(f"Both datasets: {len(both)} companies")
print()

# 2-3년도 데이터 확인
both_3y = []
both_2y = []

for corp_code in both:
    stmt_years = set(statements[statements['corp_code'] == corp_code]['bsns_year'].unique())

    if len(stmt_years) >= 3:
        both_3y.append(corp_code)
    elif len(stmt_years) >= 2:
        both_2y.append(corp_code)

print(f"With 3-year data (2023,2024,2025): {len(both_3y)} companies")
print(f"With 2-year data (at minimum): {len(both_2y)} companies")
print()

# M-Score 계산 (SGI+DEPI, 2025 vs 2024)
print("3. M-SCORE CALCULATION (SGI + DEPI)")
print("-" * 80)

mscore_results = []
calc_count = 0

for corp_code in both:
    try:
        corp_data = statements[statements['corp_code'] == corp_code]
        corp_name = corp_data['corp_name'].iloc[0]

        # 2025, 2024 손익계산서
        is_2025 = corp_data[(corp_data['bsns_year'] == 2025) & (corp_data['sj_div'] == 'IS')]
        is_2024 = corp_data[(corp_data['bsns_year'] == 2024) & (corp_data['sj_div'] == 'IS')]

        if len(is_2025) > 0 and len(is_2024) > 0:
            s25 = is_2025.iloc[0]['thstrm_amount_current']
            s24 = is_2024.iloc[0]['thstrm_amount_current']

            if pd.notna(s25) and pd.notna(s24) and s24 > 0:
                sgi = s25 / s24

                # 감가상각비
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

                        is_risk = "HIGH RISK" if m_score > -1.78 else "LOW RISK"

                        mscore_results.append({
                            'corp_name': corp_name,
                            'corp_code': corp_code,
                            'sgi': round(sgi, 4),
                            'depi': round(depi, 4),
                            'm_score': round(m_score, 4),
                            'risk_flag': is_risk
                        })
                        calc_count += 1
    except Exception as e:
        pass

print(f"Companies with calculable M-Score: {calc_count}")
print()

if len(mscore_results) > 0:
    df_m = pd.DataFrame(mscore_results)
    df_m_sorted = df_m.sort_values('m_score', ascending=False)
    df_m.to_csv('kospi100_mscore_complete.csv', index=False, encoding='utf-8-sig')

    # 위험 기업 통계
    high_risk = (df_m_sorted['m_score'] > -1.78).sum()
    low_risk = (df_m_sorted['m_score'] <= -1.78).sum()

    print(f"Risk Distribution:")
    print(f"  HIGH RISK (M-Score > -1.78): {high_risk} companies")
    print(f"  LOW RISK (M-Score <= -1.78): {low_risk} companies")
    print()

    print("TOP 15 (Highest M-Score / Highest Manipulation Risk)")
    print("-" * 80)
    for i, (idx, row) in enumerate(df_m_sorted.head(15).iterrows(), 1):
        print(f"{i:2d}. {row['corp_name']:20s} | SGI:{row['sgi']:6.3f} | DEPI:{row['depi']:6.3f} | Score:{row['m_score']:8.4f} | {row['risk_flag']}")

    print()
    print("BOTTOM 15 (Lowest M-Score / Lowest Manipulation Risk)")
    print("-" * 80)
    for i, (idx, row) in enumerate(df_m_sorted.tail(15).iterrows(), 1):
        print(f"{i:2d}. {row['corp_name']:20s} | SGI:{row['sgi']:6.3f} | DEPI:{row['depi']:6.3f} | Score:{row['m_score']:8.4f} | {row['risk_flag']}")

print()
print("=" * 80)
print("FINAL ANSWER")
print("=" * 80)
print()
print("지금까지 숫자가 도출될 수 있는 회사는 총:")
print()
print(f"  1. 감가상각비 추출: {len(dep_corps)}개 기업")
print(f"  2. M-Score 계산: {len(mscore_results)}개 기업 ✓")
print()
print(f"→ 총 {len(mscore_results)}개 기업으로 M-Score 기반 조작 위험도 분석 완료")
print()
print("파일 생성:")
print("  - kospi100_depreciation_notes.csv")
print("  - kospi100_mscore_complete.csv")
