# -*- coding: utf-8 -*-
"""
Beneish M-Score 계산 스크립트
M-Score > -1.78이면 조작 위험 기업

공식:
M-Score = -4.40 - (0.920 × DSRI) + (0.528 × GMI) - (0.404 × AQI)
          + (0.892 × SGI) - (0.115 × DEPI)

7개 지표:
1. DSRI (Day Sales in Receivables Index) = (AR_t/Sales_t) / (AR_t-1/Sales_t-1)
2. GMI (Gross Margin Index) = ((Sales_t-1 - COGS_t-1) / Sales_t-1) / ((Sales_t - COGS_t) / Sales_t)
3. AQI (Asset Quality Index) = (1 - (CA_t + PPE_t) / TA_t) / (1 - (CA_t-1 + PPE_t-1) / TA_t-1)
4. SGI (Sales Growth Index) = Sales_t / Sales_t-1
5. DEPI (Depreciation Index) = Depr_t-1 / (Depr_t-1 + PPE_t-1) / (Depr_t / (Depr_t + PPE_t))
6. SGAI (SG&A Index) = (SGA_t / Sales_t) / (SGA_t-1 / Sales_t-1)
7. LVGI (Leverage Index) = ((CL_t + LTD_t) / TA_t) / ((CL_t-1 + LTD_t-1) / TA_t-1)

"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 데이터 로드
statements = pd.read_csv('kospi100_all_statements_2025_v12.csv', encoding='utf-8-sig')
depreciation = pd.read_csv('kospi100_depreciation_notes.csv', encoding='utf-8-sig')

# 감가상각비 데이터 정리 (연도별, 기업별)
dep_pivot = depreciation.pivot_table(
    index='corp_code',
    columns='period',
    values='depreciation_expense',
    aggfunc='sum'
)
print(f"감가상각비 데이터: {len(dep_pivot)}개 기업")

def get_account_value(df, corp_code, year, account_pattern, fs_div='CFS'):
    """특정 기업의 특정 연도 계정 값 추출"""
    mask = (
        (df['corp_code'] == corp_code) &
        (df['bsns_year'] == year) &
        (df['fs_div'] == fs_div) &
        (df['account_nm'].str.contains(account_pattern, regex=False, na=False))
    )
    values = df[mask]['thstrm_amount_current'].dropna()
    if len(values) > 0:
        return values.iloc[0]
    return np.nan

# 계산 함수들
def calc_dsri(corp_code, year):
    """Day Sales in Receivables Index"""
    ar_t = get_account_value(statements, corp_code, year, '매출채권')
    sales_t = get_account_value(statements, corp_code, year, '매출액')

    ar_t1 = get_account_value(statements, corp_code, year-1, '매출채권')
    sales_t1 = get_account_value(statements, corp_code, year-1, '매출액')

    if pd.notna(ar_t) and pd.notna(sales_t) and pd.notna(ar_t1) and pd.notna(sales_t1) and sales_t1 != 0:
        return (ar_t / sales_t) / (ar_t1 / sales_t1)
    return np.nan

def calc_gmi(corp_code, year):
    """Gross Margin Index"""
    sales_t = get_account_value(statements, corp_code, year, '매출액')
    cogs_t = get_account_value(statements, corp_code, year, '매출원가')

    sales_t1 = get_account_value(statements, corp_code, year-1, '매출액')
    cogs_t1 = get_account_value(statements, corp_code, year-1, '매출원가')

    if all(pd.notna(x) for x in [sales_t, cogs_t, sales_t1, cogs_t1]) and sales_t > 0 and sales_t1 > 0:
        gm_t1 = (sales_t1 - cogs_t1) / sales_t1
        gm_t = (sales_t - cogs_t) / sales_t
        if gm_t > 0:
            return gm_t1 / gm_t
    return np.nan

def calc_aqi(corp_code, year):
    """Asset Quality Index"""
    ca_t = get_account_value(statements, corp_code, year, '유동자산')
    ppe_t = get_account_value(statements, corp_code, year, '유형자산')
    ta_t = get_account_value(statements, corp_code, year, '자산')

    ca_t1 = get_account_value(statements, corp_code, year-1, '유동자산')
    ppe_t1 = get_account_value(statements, corp_code, year-1, '유형자산')
    ta_t1 = get_account_value(statements, corp_code, year-1, '자산')

    if all(pd.notna(x) for x in [ca_t, ppe_t, ta_t, ca_t1, ppe_t1, ta_t1]) and ta_t > 0 and ta_t1 > 0:
        aqi = (1 - (ca_t + ppe_t) / ta_t) / (1 - (ca_t1 + ppe_t1) / ta_t1)
        if aqi > 0:
            return aqi
    return np.nan

def calc_sgi(corp_code, year):
    """Sales Growth Index"""
    sales_t = get_account_value(statements, corp_code, year, '매출액')
    sales_t1 = get_account_value(statements, corp_code, year-1, '매출액')

    if pd.notna(sales_t) and pd.notna(sales_t1) and sales_t1 > 0:
        return sales_t / sales_t1
    return np.nan

def calc_depi(corp_code, year, dep_data):
    """Depreciation Index"""
    depr_t = dep_data.get((corp_code, f'{year}0101-{year}1231'), np.nan)
    depr_t1 = dep_data.get((corp_code, f'{year-1}0101-{year-1}1231'), np.nan)

    ppe_t = get_account_value(statements, corp_code, year, '유형자산')
    ppe_t1 = get_account_value(statements, corp_code, year-1, '유형자산')

    if all(pd.notna(x) for x in [depr_t, depr_t1, ppe_t, ppe_t1]):
        denom_t1 = depr_t1 + ppe_t1
        denom_t = depr_t + ppe_t
        if denom_t1 > 0 and denom_t > 0:
            return (depr_t1 / denom_t1) / (depr_t / denom_t)
    return np.nan

def calc_sgai(corp_code, year):
    """SG&A Index"""
    sga_t = get_account_value(statements, corp_code, year, '판매비')
    sales_t = get_account_value(statements, corp_code, year, '매출액')

    sga_t1 = get_account_value(statements, corp_code, year-1, '판매비')
    sales_t1 = get_account_value(statements, corp_code, year-1, '매출액')

    if all(pd.notna(x) for x in [sga_t, sales_t, sga_t1, sales_t1]) and sales_t > 0 and sales_t1 > 0:
        return (sga_t / sales_t) / (sga_t1 / sales_t1)
    return np.nan

def calc_lvgi(corp_code, year):
    """Leverage Index"""
    cl_t = get_account_value(statements, corp_code, year, '유동부채')
    ltd_t = get_account_value(statements, corp_code, year, '비유동부채')
    ta_t = get_account_value(statements, corp_code, year, '자산')

    cl_t1 = get_account_value(statements, corp_code, year-1, '유동부채')
    ltd_t1 = get_account_value(statements, corp_code, year-1, '비유동부채')
    ta_t1 = get_account_value(statements, corp_code, year-1, '자산')

    if all(pd.notna(x) for x in [cl_t, ltd_t, ta_t, cl_t1, ltd_t1, ta_t1]) and ta_t > 0 and ta_t1 > 0:
        return ((cl_t + ltd_t) / ta_t) / ((cl_t1 + ltd_t1) / ta_t1)
    return np.nan

# M-Score 계산
results = []
dep_dict = {}

for _, row in depreciation.iterrows():
    key = (row['corp_code'], row['period'])
    dep_dict[key] = row['depreciation_expense']

for corp_code in statements['corp_code'].unique():
    try:
        corp_name = statements[statements['corp_code'] == corp_code]['corp_name'].iloc[0]

        # 2025년 기준 (당기: 2025, 전기: 2024)
        dsri = calc_dsri(corp_code, 2025)
        gmi = calc_gmi(corp_code, 2025)
        aqi = calc_aqi(corp_code, 2025)
        sgi = calc_sgi(corp_code, 2025)
        depi = calc_depi(corp_code, 2025, dep_dict)
        sgai = calc_sgai(corp_code, 2025)
        lvgi = calc_lvgi(corp_code, 2025)

        # M-Score 계산
        if all(pd.notna(x) for x in [dsri, gmi, aqi, sgi, depi, sgai, lvgi]):
            m_score = -4.40 - (0.920 * dsri) + (0.528 * gmi) - (0.404 * aqi) + (0.892 * sgi) - (0.115 * depi)

            # SGAI와 LVGI는 선택적 (일부 연구에서만 포함)
            # m_score += (0.020 * sgai) - (0.172 * lvgi)  # 필요시 활성화

            is_manipulator = m_score > -1.78

            results.append({
                'corp_code': corp_code,
                'corp_name': corp_name,
                'm_score': round(m_score, 4),
                'dsri': round(dsri, 4),
                'gmi': round(gmi, 4),
                'aqi': round(aqi, 4),
                'sgi': round(sgi, 4),
                'depi': round(depi, 4),
                'sgai': round(sgai, 4),
                'lvgi': round(lvgi, 4),
                'is_manipulator': is_manipulator
            })
    except Exception as e:
        pass

# 결과 저장
result_df = pd.DataFrame(results)
result_df = result_df.sort_values('m_score', ascending=False)
result_df.to_csv('kospi100_beneish_mscore.csv', index=False, encoding='utf-8-sig')

print(f"\n=== M-Score 계산 완료 ===")
print(f"계산된 기업: {len(result_df)}개")
print(f"\n위험 기업 (M-Score > -1.78): {result_df['is_manipulator'].sum()}개")
print(f"안전 기업 (M-Score <= -1.78): {(~result_df['is_manipulator']).sum()}개")

print(f"\n=== 상위 10개 (조작 위험도 높음) ===")
top10 = result_df.head(10)[['corp_name', 'm_score', 'is_manipulator']]
for idx, row in top10.iterrows():
    status = '⚠️ 위험' if row['is_manipulator'] else '✓ 안전'
    print(f"{row['corp_name']:15} {row['m_score']:>8.4f} {status}")

print(f"\n파일 저장: kospi100_beneish_mscore.csv")
