# -*- coding: utf-8 -*-
"""
30개 실패 기업 대체 부정행위 점수 계산 (개선판)
계정명 매칭 로직 개선
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 데이터 로드
statements = pd.read_csv('kospi100_statements_final_v13_complete.csv', encoding='utf-8-sig')

# 30개 실패 기업
failed_companies = {
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
    'IT_SOFTWARE': [
        (266961, 'NAVER'),
        (258801, '카카오'),
        (760971, '크래프톤'),
        (261443, 'NC'),
        (1204056, '하이브'),
        (1133217, '카카오뱅크'),
    ],
    'HOLDING': [
        (126478, '삼성중공업'),
        (631518, 'SK이노베이션'),
    ]
}

print("=" * 130)
print("30개 실패 기업 대체 부정행위 점수 계산 (개선판)")
print("=" * 130)
print()

all_results = []

for category, companies in failed_companies.items():
    print(f"\n{category}:")
    print("-" * 130)

    for corp_code, corp_name in companies:
        try:
            corp_data = statements[statements['corp_code'] == corp_code]

            if len(corp_data) == 0:
                continue

            # 2025년 데이터
            data_2025 = corp_data[corp_data['bsns_year'] == 2025]
            data_2024 = corp_data[corp_data['bsns_year'] == 2024]

            if len(data_2025) == 0:
                continue

            # ===== 손익계산서 데이터 =====
            is_types = ['IS', 'CIS']
            is_data_2025 = None
            is_data_2024 = None

            for sj_type in is_types:
                if is_data_2025 is None:
                    is_data_2025 = data_2025[data_2025['sj_div'] == sj_type]
                if is_data_2024 is None:
                    is_data_2024 = data_2024[data_2024['sj_div'] == sj_type]

            # 순이익 찾기
            ni_2025 = np.nan
            if is_data_2025 is not None and len(is_data_2025) > 0:
                # 여러 패턴 시도
                for pattern in ['당기순이익', '순이익']:
                    matches = is_data_2025[is_data_2025['account_nm'].str.contains(
                        pattern, na=False, regex=False)]
                    if len(matches) > 0:
                        ni_2025 = matches.iloc[0]['thstrm_amount_current']
                        break

            ni_2024 = np.nan
            if is_data_2024 is not None and len(is_data_2024) > 0:
                for pattern in ['당기순이익', '순이익']:
                    matches = is_data_2024[is_data_2024['account_nm'].str.contains(
                        pattern, na=False, regex=False)]
                    if len(matches) > 0:
                        ni_2024 = matches.iloc[0]['thstrm_amount_current']
                        break

            # 매출액 찾기
            revenue_2025 = np.nan
            if is_data_2025 is not None and len(is_data_2025) > 0:
                for pattern in ['매출액', '수익']:
                    matches = is_data_2025[is_data_2025['account_nm'].str.contains(
                        pattern, na=False, regex=False)]
                    if len(matches) > 0:
                        revenue_2025 = matches.iloc[0]['thstrm_amount_current']
                        break

            revenue_2024 = np.nan
            if is_data_2024 is not None and len(is_data_2024) > 0:
                for pattern in ['매출액', '수익']:
                    matches = is_data_2024[is_data_2024['account_nm'].str.contains(
                        pattern, na=False, regex=False)]
                    if len(matches) > 0:
                        revenue_2024 = matches.iloc[0]['thstrm_amount_current']
                        break

            # ===== 재무상태표 데이터 =====
            bs_data_2025 = data_2025[data_2025['sj_div'] == 'BS']
            bs_data_2024 = data_2024[data_2024['sj_div'] == 'BS']

            # 유동자산
            ca_2025 = np.nan
            if len(bs_data_2025) > 0:
                matches = bs_data_2025[bs_data_2025['account_nm'].str.contains(
                    '유동자산', na=False, regex=False)]
                if len(matches) > 0:
                    ca_2025 = matches.iloc[0]['thstrm_amount_current']

            # 현금
            cash_2025 = np.nan
            if len(bs_data_2025) > 0:
                for pattern in ['현금', '현금및현금성자산']:
                    matches = bs_data_2025[bs_data_2025['account_nm'].str.contains(
                        pattern, na=False, regex=False)]
                    if len(matches) > 0:
                        cash_2025 = matches.iloc[0]['thstrm_amount_current']
                        break

            # 유동부채
            cl_2025 = np.nan
            if len(bs_data_2025) > 0:
                matches = bs_data_2025[bs_data_2025['account_nm'].str.contains(
                    '유동부채', na=False, regex=False)]
                if len(matches) > 0:
                    cl_2025 = matches.iloc[0]['thstrm_amount_current']

            # 총자산
            ta_2025 = np.nan
            if len(bs_data_2025) > 0:
                for pattern in ['자산총계', '자산']:
                    matches = bs_data_2025[bs_data_2025['account_nm'].str.contains(
                        pattern, na=False, regex=False)]
                    if len(matches) > 0:
                        ta_2025 = matches.iloc[0]['thstrm_amount_current']
                        break

            # 외상매출금
            ar_2025 = np.nan
            if len(bs_data_2025) > 0:
                for pattern in ['매출채권', '외상매출금']:
                    matches = bs_data_2025[bs_data_2025['account_nm'].str.contains(
                        pattern, na=False, regex=False)]
                    if len(matches) > 0:
                        ar_2025 = matches.iloc[0]['thstrm_amount_current']
                        break

            # 전년도
            ca_2024 = np.nan
            if len(bs_data_2024) > 0:
                matches = bs_data_2024[bs_data_2024['account_nm'].str.contains(
                    '유동자산', na=False, regex=False)]
                if len(matches) > 0:
                    ca_2024 = matches.iloc[0]['frmtrm_amount_prior'] if pd.notna(matches.iloc[0]['frmtrm_amount_prior']) else matches.iloc[0]['thstrm_amount_current']

            cl_2024 = np.nan
            if len(bs_data_2024) > 0:
                matches = bs_data_2024[bs_data_2024['account_nm'].str.contains(
                    '유동부채', na=False, regex=False)]
                if len(matches) > 0:
                    cl_2024 = matches.iloc[0]['frmtrm_amount_prior'] if pd.notna(matches.iloc[0]['frmtrm_amount_prior']) else matches.iloc[0]['thstrm_amount_current']

            ta_2024 = np.nan
            if len(bs_data_2024) > 0:
                for pattern in ['자산총계', '자산']:
                    matches = bs_data_2024[bs_data_2024['account_nm'].str.contains(
                        pattern, na=False, regex=False)]
                    if len(matches) > 0:
                        ta_2024 = matches.iloc[0]['frmtrm_amount_prior'] if pd.notna(matches.iloc[0]['frmtrm_amount_prior']) else matches.iloc[0]['thstrm_amount_current']
                        break

            # ===== 현금흐름표 데이터 =====
            cf_data_2025 = data_2025[data_2025['sj_div'] == 'CF']
            ocf_2025 = np.nan

            if len(cf_data_2025) > 0:
                for pattern in ['영업활동', '영업']:
                    matches = cf_data_2025[cf_data_2025['account_nm'].str.contains(
                        pattern, na=False, regex=False)]
                    if len(matches) > 0:
                        ocf_2025 = matches.iloc[0]['thstrm_amount_current']
                        break

            # ===== OCF/NI Ratio =====
            ocf_ni_ratio = np.nan
            if pd.notna(ocf_2025) and pd.notna(ni_2025) and ni_2025 != 0:
                ocf_ni_ratio = ocf_2025 / ni_2025

            # ===== Accrual Ratio =====
            accrual_ratio = np.nan
            if pd.notna(ca_2025) and pd.notna(cl_2025) and pd.notna(ca_2024) and \
               pd.notna(cl_2024) and pd.notna(ta_2025) and ta_2025 != 0:
                total_accruals = (ca_2025 - cl_2025) - (ca_2024 - cl_2024)
                accrual_ratio = total_accruals / ta_2025

            # ===== Working Capital (DSO) =====
            dso = np.nan
            if pd.notna(ar_2025) and pd.notna(revenue_2025) and revenue_2025 > 0:
                dso = (ar_2025 / revenue_2025) * 365

            # ===== 부정행위 위험 점수 =====
            fraud_score = 0.0
            data_quality = 0

            # OCF/NI (0.35 가중치)
            if pd.notna(ocf_ni_ratio):
                data_quality += 1
                if ocf_ni_ratio < 0.8:
                    fraud_score += 0.35
                elif ocf_ni_ratio < 0.9:
                    fraud_score += 0.20
                elif ocf_ni_ratio > 1.5:
                    fraud_score += 0.10

            # Accrual Ratio (0.30 가중치)
            if pd.notna(accrual_ratio):
                data_quality += 1
                if accrual_ratio > 0.10:
                    fraud_score += 0.30
                elif accrual_ratio > 0.05:
                    fraud_score += 0.15

            # DSO (0.20 가중치)
            if pd.notna(dso):
                data_quality += 1
                if dso > 90:
                    fraud_score += 0.20
                elif dso > 60:
                    fraud_score += 0.10

            # 데이터 미흡 페널티
            if data_quality < 2:
                fraud_score = fraud_score * 0.5

            # 결과 저장
            result = {
                'corp_name': corp_name,
                'corp_code': corp_code,
                'category': category,
                'ocf_ni_ratio': round(ocf_ni_ratio, 2) if pd.notna(ocf_ni_ratio) else None,
                'accrual_ratio': round(accrual_ratio, 4) if pd.notna(accrual_ratio) else None,
                'dso': round(dso, 1) if pd.notna(dso) else None,
                'fraud_risk_score': round(fraud_score, 3),
                'risk_level': 'HIGH' if fraud_score > 0.50 else ('MEDIUM' if fraud_score > 0.25 else 'LOW'),
                'data_quality': data_quality
            }

            all_results.append(result)

            score_str = f"{fraud_score:.3f}"
            ocf_ni_str = f"{ocf_ni_ratio:.2f}" if pd.notna(ocf_ni_ratio) else "N/A"
            accrual_str = f"{accrual_ratio:.4f}" if pd.notna(accrual_ratio) else "N/A"
            dso_str = f"{dso:.1f}" if pd.notna(dso) else "N/A"

            print(f"{corp_name:20s} | OCF/NI:{ocf_ni_str:>8s} | Accrual:{accrual_str:>8s} | DSO:{dso_str:>8s} | Score:{score_str:>7s} | {result['risk_level']:>6s}")

        except Exception as e:
            print(f"{corp_name:20s} | ERROR: {str(e)[:50]}")

print()
print("=" * 130)

if len(all_results) > 0:
    results_df = pd.DataFrame(all_results)
    results_sorted = results_df.sort_values('fraud_risk_score', ascending=False)

    results_sorted.to_csv('kospi100_alternative_fraud_scores_30.csv', index=False, encoding='utf-8-sig')

    # 통계
    high_risk = (results_sorted['fraud_risk_score'] > 0.50).sum()
    medium_risk = ((results_sorted['fraud_risk_score'] > 0.25) & (results_sorted['fraud_risk_score'] <= 0.50)).sum()
    low_risk = (results_sorted['fraud_risk_score'] <= 0.25).sum()

    print(f"\n계산 완료: {len(all_results)}개 기업")
    print(f"데이터 완성도: {(results_df['data_quality'] >= 2).sum()}개 기업이 충분한 데이터 보유")
    print()
    print("위험도 분포:")
    print(f"  HIGH RISK (>0.50): {high_risk}개")
    print(f"  MEDIUM RISK (0.25-0.50): {medium_risk}개")
    print(f"  LOW RISK (<=0.25): {low_risk}개")
    print()
    print("상위 15개 (가장 높은 부정행위 위험):")
    print("-" * 130)
    for idx, row in results_sorted.head(15).iterrows():
        print(f"{row['corp_name']:20s} | OCF/NI:{str(row['ocf_ni_ratio']):>8s} | Accrual:{str(row['accrual_ratio']):>8s} | DSO:{str(row['dso']):>8s} | Score:{row['fraud_risk_score']:>7.3f} | {row['risk_level']:>6s}")

    print()
    print("파일 저장: kospi100_alternative_fraud_scores_30.csv")
