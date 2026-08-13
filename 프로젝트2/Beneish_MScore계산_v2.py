# -*- coding: utf-8 -*-
"""
Beneish M-Score 계산 (v2 - 간소화 버전)
현재 데이터로 계산 가능한 지표들만 포함

DEPI (Depreciation Index)를 중심으로 계산
감가상각비 데이터를 활용한 핵심 지표 계산
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 데이터 로드
statements = pd.read_csv('kospi100_all_statements_2025_v12.csv', encoding='utf-8-sig')
depreciation = pd.read_csv('kospi100_depreciation_notes.csv', encoding='utf-8-sig')

print("=== 데이터 로드 완료 ===")
print(f"재무제표: {len(statements)}줄")
print(f"감가상각비: {len(depreciation)}줄\n")

# 기업별 감가상각비 데이터 정리
dep_2025 = depreciation[(depreciation['period'] == '20250101-20251231')]
dep_2024 = depreciation[(depreciation['period'] == '20240101-20241231')]

dep_dict = {}
for _, row in dep_2025.iterrows():
    dep_dict[(row['corp_code'], 2025)] = row['depreciation_expense']
for _, row in dep_2024.iterrows():
    dep_dict[(row['corp_code'], 2024)] = row['depreciation_expense']

print(f"감가상각비 데이터포인트: {len(dep_dict)}개\n")

# 간단한 버전: 감가상각비 지표와 매출 증가율로 기본 스코어 계산
results = []

for corp_code in statements['corp_code'].unique()[:98]:  # KOSPI100만
    try:
        corp_data = statements[statements['corp_code'] == corp_code]
        if len(corp_data) == 0:
            continue

        corp_name = corp_data['corp_name'].iloc[0]

        # 2025년 데이터 추출 (IS: 손익계산서)
        is_2025 = corp_data[(corp_data['bsns_year'] == 2025) & (corp_data['sj_div'] == 'IS')]
        is_2024 = corp_data[(corp_data['bsns_year'] == 2024) & (corp_data['sj_div'] == 'IS')]

        if len(is_2025) == 0 or len(is_2024) == 0:
            continue

        # 매출액 (첫 번째 행 = 매출액)
        sales_2025 = is_2025.iloc[0]['thstrm_amount_current']
        sales_2024 = is_2024.iloc[0]['thstrm_amount_current']

        if pd.isna(sales_2025) or pd.isna(sales_2024) or sales_2024 == 0:
            continue

        # SGI (Sales Growth Index)
        sgi = sales_2025 / sales_2024

        # DEPI (Depreciation Index) - 감가상각비 데이터 활용
        depr_2025 = dep_dict.get((corp_code, 2025), np.nan)
        depr_2024 = dep_dict.get((corp_code, 2024), np.nan)

        depi = np.nan
        if pd.notna(depr_2025) and pd.notna(depr_2024) and depr_2024 > 0:
            # 간단한 감가상각 지표: 전년 vs 당년
            depi = depr_2024 / depr_2025 if depr_2025 > 0 else np.nan

        # 간단한 M-Score 추정 (SGI와 DEPI 기반)
        m_score = np.nan
        if pd.notna(sgi) and pd.notna(depi):
            # M-Score 근사값: 매출 급증과 감가상각비 감소는 조작 신호
            m_score = -4.40 + (0.892 * sgi) - (0.115 * depi)

        is_manipulator = m_score > -1.78 if pd.notna(m_score) else None

        results.append({
            'corp_code': corp_code,
            'corp_name': corp_name,
            'sales_2025': sales_2025,
            'sales_2024': sales_2024,
            'depr_2025': depr_2025,
            'depr_2024': depr_2024,
            'sgi': round(sgi, 4) if pd.notna(sgi) else np.nan,
            'depi': round(depi, 4) if pd.notna(depi) else np.nan,
            'm_score_estimate': round(m_score, 4) if pd.notna(m_score) else np.nan,
            'risk_flag': '⚠️ 위험' if is_manipulator else ('✓ 안전' if is_manipulator is not None else '-')
        })
    except Exception as e:
        pass

# 결과 정리
result_df = pd.DataFrame(results)
result_df = result_df.dropna(subset=['m_score_estimate'])
result_df = result_df.sort_values('m_score_estimate', ascending=False)

print(f"=== M-Score 계산 결과 ===")
print(f"계산된 기업: {len(result_df)}개\n")

print(f"위험 기업 (M-Score > -1.78): {(result_df['m_score_estimate'] > -1.78).sum()}개")
print(f"안전 기업 (M-Score <= -1.78): {(result_df['m_score_estimate'] <= -1.78).sum()}개\n")

print("=== 상위 15개 (조작 위험도 높음) ===")
top15 = result_df.head(15)[['corp_name', 'sgi', 'depi', 'm_score_estimate', 'risk_flag']]
for idx, row in top15.iterrows():
    print(f"{row['corp_name']:15} SGI:{row['sgi']:>6.2f} DEPI:{row['depi']:>6.2f} M-Score:{row['m_score_estimate']:>8.4f} {row['risk_flag']}")

print("\n=== 하위 15개 (낮은 위험도) ===")
bottom15 = result_df.tail(15)[['corp_name', 'sgi', 'depi', 'm_score_estimate', 'risk_flag']]
for idx, row in bottom15.iterrows():
    print(f"{row['corp_name']:15} SGI:{row['sgi']:>6.2f} DEPI:{row['depi']:>6.2f} M-Score:{row['m_score_estimate']:>8.4f} {row['risk_flag']}")

# 파일 저장
result_df.to_csv('kospi100_beneish_mscore_v2.csv', index=False, encoding='utf-8-sig')
print(f"\n파일 저장 완료: kospi100_beneish_mscore_v2.csv")
print(f"총 {len(result_df)}개 기업 데이터 포함")

