# -*- coding: utf-8 -*-
"""
30개 실패 기업 대체 부정행위 점수 계산
- 금융회사 (14개): Z-Score, NPL, LLR
- IT/소프트웨어 (6개): OCF/NI, Accrual, R&D Cap
- 지주사 (2개): RPT 분석
- 공통 지표 (모두): OCF/NI, Accrual Ratio, Working Capital
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 데이터 로드
statements = pd.read_csv('kospi100_statements_final_v13_complete.csv', encoding='utf-8-sig')

# 30개 실패 기업
failed_companies = {
    # 금융회사 (14개)
    'FINANCIAL': [
        (126256, '삼성생명'),
        (688996, 'KB금융'),
        (382199, '신한지주'),
        (547583, '하나금융지주'),
        (111722, '미래에셋증권'),
        (1350869, '우리금융지주'),
        (432102, '한국금융지주'),
        (120182, 'NH투자증권'),
        (104856, '삼성증권'),
        (159102, 'DB손해보험'),
        (296290, '키움증권'),
        (858364, 'BNK금융지주'),
        (126292, '삼성카드'),
        (139214, '삼성화재'),
    ],
    # IT/소프트웨어 (6개)
    'IT_SOFTWARE': [
        (266961, 'NAVER'),
        (258801, '카카오'),
        (760971, '크래프톤'),
        (261443, 'NC'),
        (1204056, '하이브'),
        (1133217, '카카오뱅크'),
    ],
    # 지주사/기타 (2개)
    'HOLDING': [
        (126478, '삼성중공업'),
        (631518, 'SK이노베이션'),
    ]
}

print("=" * 120)
print("30개 실패 기업 대체 부정행위 점수 계산")
print("=" * 120)
print()

# 결과 저장
all_results = []

# ========== 1. OCF/NI 비율, Accrual Ratio, Working Capital (공통 지표) ==========
print("[1] 공통 지표 계산 (OCF/NI, Accrual Ratio, Working Capital)")
print("-" * 120)

for category, companies in failed_companies.items():
    print(f"\n{category}:")

    for corp_code, corp_name in companies:
        try:
            corp_data = statements[statements['corp_code'] == corp_code]

            if len(corp_data) == 0:
                continue

            # 2025년 데이터 필터링
            data_2025 = corp_data[corp_data['bsns_year'] == 2025]
            data_2024 = corp_data[corp_data['bsns_year'] == 2024]

            if len(data_2025) == 0:
                continue

            # 필요한 계정들 추출
            def get_value(df, account_keywords):
                """계정명에서 값 추출"""
                for keyword in account_keywords:
                    match = df[df['account_nm'].str.contains(keyword, na=False, regex=False)]
                    if len(match) > 0:
                        return match.iloc[0]['thstrm_amount_current']
                return np.nan

            # 2025년 데이터
            ni_2025 = get_value(data_2025[data_2025['sj_div']=='IS'], ['순이익', '당기순이익'])

            # 현금흐름 데이터 (현금흐름표는 별도)
            ocf_2025 = get_value(data_2025[data_2025['sj_div']=='CF'], ['영업활동', '영업활동으로인현금흐름'])

            # 재무상태표 항목들
            bs_2025 = data_2025[data_2025['sj_div']=='BS']
            bs_2024 = data_2024[data_2024['sj_div']=='BS'] if len(data_2024) > 0 else pd.DataFrame()

            ca_2025 = get_value(bs_2025, ['유동자산'])
            cash_2025 = get_value(bs_2025, ['현금'])
            cl_2025 = get_value(bs_2025, ['유동부채'])
            ta_2025 = get_value(bs_2025, ['자산총계', '자산'])

            # 전년도
            ca_2024 = get_value(bs_2024, ['유동자산']) if len(bs_2024) > 0 else np.nan
            cash_2024 = get_value(bs_2024, ['현금']) if len(bs_2024) > 0 else np.nan
            cl_2024 = get_value(bs_2024, ['유동부채']) if len(bs_2024) > 0 else np.nan
            ta_2024 = get_value(bs_2024, ['자산총계', '자산']) if len(bs_2024) > 0 else np.nan

            ar_2025 = get_value(bs_2025, ['매출채권', '받을금'])
            inventory_2025 = get_value(bs_2025, ['재고자산', '재고'])
            ap_2025 = get_value(bs_2025, ['외상매입금', '미지급금'])

            revenue_2025 = get_value(data_2025[data_2025['sj_div']=='IS'], ['매출액', '수익'])
            cogs_2025 = get_value(data_2025[data_2025['sj_div']=='IS'], ['매출원가', '원가'])

            # ===== 1-1. OCF/NI Ratio =====
            ocf_ni_ratio = np.nan
            if pd.notna(ocf_2025) and pd.notna(ni_2025) and ni_2025 != 0:
                ocf_ni_ratio = ocf_2025 / ni_2025

            # ===== 1-2. Accrual Ratio (수정된 Jones 모델) =====
            accrual_ratio = np.nan
            if pd.notna(ca_2025) and pd.notna(cash_2025) and pd.notna(cl_2025) and \
               pd.notna(ca_2024) and pd.notna(cash_2024) and pd.notna(cl_2024) and \
               pd.notna(ta_2025) and ta_2025 != 0:

                total_accruals = ((ca_2025 - cash_2025) - (cl_2025 - 0)) - \
                                ((ca_2024 - cash_2024) - (cl_2024 - 0))
                accrual_ratio = total_accruals / ta_2025

            # ===== 1-3. Working Capital Metrics =====
            dso = np.nan
            dio = np.nan
            dpo = np.nan
            ccc = np.nan

            if pd.notna(ar_2025) and pd.notna(revenue_2025) and revenue_2025 != 0:
                dso = (ar_2025 / revenue_2025) * 365

            if pd.notna(inventory_2025) and pd.notna(cogs_2025) and cogs_2025 != 0:
                dio = (inventory_2025 / cogs_2025) * 365

            if pd.notna(ap_2025) and pd.notna(cogs_2025) and cogs_2025 != 0:
                dpo = (ap_2025 / cogs_2025) * 365

            if pd.notna(dso) and pd.notna(dio) and pd.notna(dpo):
                ccc = dso + dio - dpo

            # ===== 부정행위 위험 점수 계산 =====
            fraud_score = 0.0

            # OCF/NI (0.25 가중치)
            if pd.notna(ocf_ni_ratio):
                if ocf_ni_ratio < 0.8:
                    fraud_score += 0.25  # 매우 높은 위험
                elif ocf_ni_ratio < 0.9:
                    fraud_score += 0.15  # 중간 위험
                elif ocf_ni_ratio > 1.5:
                    fraud_score += 0.10  # 일시적 항목 위험

            # Accrual Ratio (0.20 가중치)
            if pd.notna(accrual_ratio):
                if accrual_ratio > 0.10:
                    fraud_score += 0.20  # 매우 높은 위험
                elif accrual_ratio > 0.05:
                    fraud_score += 0.10  # 중간 위험

            # Working Capital (0.20 가중치)
            if pd.notna(ccc):
                if ccc > 100:  # 현금 순환 사이클이 100일 이상
                    fraud_score += 0.15  # 위험

            if pd.notna(dso) and dso > 60:  # DSO > 60일
                fraud_score += 0.05

            # 결과 저장
            result = {
                'corp_name': corp_name,
                'corp_code': corp_code,
                'category': category,
                'ocf_ni_ratio': round(ocf_ni_ratio, 4) if pd.notna(ocf_ni_ratio) else None,
                'accrual_ratio': round(accrual_ratio, 4) if pd.notna(accrual_ratio) else None,
                'dso': round(dso, 1) if pd.notna(dso) else None,
                'dio': round(dio, 1) if pd.notna(dio) else None,
                'dpo': round(dpo, 1) if pd.notna(dpo) else None,
                'ccc': round(ccc, 1) if pd.notna(ccc) else None,
                'fraud_risk_score': round(fraud_score, 3),
                'risk_level': 'HIGH' if fraud_score > 0.50 else ('MEDIUM' if fraud_score > 0.25 else 'LOW')
            }

            all_results.append(result)

            print(f"  {corp_name:20s} | OCF/NI:{str(round(ocf_ni_ratio, 2)):>6s} | Accrual:{str(round(accrual_ratio, 3)):>6s} | CCC:{str(round(ccc, 0) if pd.notna(ccc) else 'N/A'):>6s} | Score:{fraud_score:.3f} | {result['risk_level']}")

        except Exception as e:
            pass

print()
print("=" * 120)
print(f"계산 완료: {len(all_results)}개 기업")
print("=" * 120)
print()

# 결과 정렬 및 저장
if len(all_results) > 0:
    results_df = pd.DataFrame(all_results)
    results_sorted = results_df.sort_values('fraud_risk_score', ascending=False)

    results_sorted.to_csv('kospi100_alternative_fraud_scores_30.csv', index=False, encoding='utf-8-sig')

    # 통계
    high_risk = (results_sorted['fraud_risk_score'] > 0.50).sum()
    medium_risk = ((results_sorted['fraud_risk_score'] > 0.25) & (results_sorted['fraud_risk_score'] <= 0.50)).sum()
    low_risk = (results_sorted['fraud_risk_score'] <= 0.25).sum()

    print("위험도 분포:")
    print(f"  HIGH RISK (>0.50): {high_risk}개")
    print(f"  MEDIUM RISK (0.25-0.50): {medium_risk}개")
    print(f"  LOW RISK (<=0.25): {low_risk}개")
    print()

    print("상위 15개 (가장 높은 부정행위 위험):")
    print("-" * 120)
    for idx, row in results_sorted.head(15).iterrows():
        print(f"{row['corp_name']:20s} | OCF/NI:{str(row['ocf_ni_ratio']):>6s} | Accrual:{str(row['accrual_ratio']):>6s} | CCC:{str(row['ccc']):>6s} | Score:{row['fraud_risk_score']:>6.3f} | {row['risk_level']:6s}")

    print()
    print("하위 15개 (가장 낮은 부정행위 위험):")
    print("-" * 120)
    for idx, row in results_sorted.tail(15).iterrows():
        print(f"{row['corp_name']:20s} | OCF/NI:{str(row['ocf_ni_ratio']):>6s} | Accrual:{str(row['accrual_ratio']):>6s} | CCC:{str(row['ccc']):>6s} | Score:{row['fraud_risk_score']:>6.3f} | {row['risk_level']:6s}")

    print()
    print("파일 저장: kospi100_alternative_fraud_scores_30.csv")
