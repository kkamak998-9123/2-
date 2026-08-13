# -*- coding: utf-8 -*-
"""
프로젝트3: 최적화된 DART 재무제표 분석 프로그램
- OpenDART API를 통한 5개년 빠른 데이터 추출
- matplotlib 시각화
- 24년 vs 25년 이상 변동률 분석 (시그마 ±2)
"""

import pandas as pd
import matplotlib.pyplot as plt
import dart_fss as dart
import requests
import xml.etree.ElementTree as ET
import zipfile
import io
import numpy as np
import time
import os

API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"
DART_API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"
dart.set_api_key(api_key=API_KEY)

if os.name == 'nt':
    plt.rc('font', family='Malgun Gothic')
else:
    plt.rc('font', family='AppleGothic')

plt.rcParams['axes.unicode_minus'] = False

# ============= 계정과목 정규화 =============

def 계정정규화(account_name):
    """계정과목 정규화: 공백, 로마자, 특수문자 제거"""
    if not account_name:
        return account_name

    # 공백 제거
    normalized = account_name.replace(' ', '')

    # 로마자 제거 (Ⅰ, Ⅱ, Ⅲ, Ⅳ, Ⅴ, Ⅵ, Ⅶ, Ⅷ, Ⅸ, Ⅹ 등)
    roman_chars = ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ', 'Ⅵ', 'Ⅶ', 'Ⅷ', 'Ⅸ', 'Ⅹ', 'ⅰ', 'ⅱ', 'ⅲ', 'ⅳ', 'ⅴ']
    for roman in roman_chars:
        normalized = normalized.replace(roman, '')

    # 불필요한 괄호와 점 제거
    normalized = normalized.replace('(', '').replace(')', '')
    normalized = normalized.replace('.', '').replace('。', '')

    return normalized.strip()

# ============= OpenDART API 고속 추출 =============

def fetch_single_company_statements_optimized(api_key, corp_code, corp_name):
    """⚡ 단일 회사 5개년 재무제표 고속 추출 (OpenDART API 직접 호출)"""
    print(f"⏳ '{corp_name}' 5개년 재무제표 추출 중...")

    api_url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    all_years_data = []

    for year in ['2025', '2024', '2023', '2022', '2021']:
        year_data = None

        for fs_div in ['CFS', 'OFS']:
            params = {
                'crtfc_key': api_key,
                'corp_code': corp_code,
                'bsns_year': year,
                'reprt_code': '11011',
                'fs_div': fs_div
            }

            try:
                res = requests.get(api_url, params=params, timeout=10)
                data = res.json()
                status = data.get('status')

                if status == '000' and 'list' in data:
                    year_data = data['list']
                    break

                elif status == '013':
                    continue

            except Exception as e:
                pass

            time.sleep(0.05)

        if year_data:
            for row in year_data:
                row['bsns_year'] = year
            all_years_data.extend(year_data)

    return all_years_data if all_years_data else None

def convert_api_data_to_dataframe(api_data):
    """OpenDART API 5개년 데이터를 DataFrame으로 변환"""
    if not api_data:
        return None

    bs_data = {}
    is_data = {}
    cis_data = {}
    cf_data = {}

    for row in api_data:
        sj_div = row.get('sj_div')
        account = row.get('account_nm')
        year = str(row.get('bsns_year', ''))
        amount = row.get('thstrm_amount')

        if not account:
            continue

        try:
            if amount is not None:
                amount = float(amount)
            else:
                amount = np.nan
        except (TypeError, ValueError):
            amount = np.nan

        if sj_div == 'BS':
            if account not in bs_data:
                bs_data[account] = {}
            bs_data[account][year] = amount

        elif sj_div == 'IS':
            if account not in is_data:
                is_data[account] = {}
            is_data[account][year] = amount

        elif sj_div == 'CIS':
            if account not in cis_data:
                cis_data[account] = {}
            cis_data[account][year] = amount

        elif sj_div == 'CF':
            if account not in cf_data:
                cf_data[account] = {}
            cf_data[account][year] = amount

    fs_dict = {}

    if bs_data:
        bs_df = pd.DataFrame(bs_data).T
        year_cols = sorted([col for col in bs_df.columns if col])
        bs_df = bs_df[[col for col in year_cols if col in bs_df.columns]]
        if not bs_df.empty:
            fs_dict['bs'] = bs_df

    if is_data:
        is_df = pd.DataFrame(is_data).T
        year_cols = sorted([col for col in is_df.columns if col])
        is_df = is_df[[col for col in year_cols if col in is_df.columns]]
        if not is_df.empty:
            fs_dict['is'] = is_df

    elif cis_data:
        cis_df = pd.DataFrame(cis_data).T
        year_cols = sorted([col for col in cis_df.columns if col])
        cis_df = cis_df[[col for col in year_cols if col in cis_df.columns]]
        if not cis_df.empty:
            fs_dict['is'] = cis_df

    if cf_data:
        cf_df = pd.DataFrame(cf_data).T
        year_cols = sorted([col for col in cf_df.columns if col])
        cf_df = cf_df[[col for col in year_cols if col in cf_df.columns]]
        if not cf_df.empty:
            fs_dict['cf'] = cf_df

    if not fs_dict:
        return None

    return fs_dict

모든회사목록 = dart.get_corp_list()

def 회사이름찾기():
    """회사명으로 기업 검색"""
    이름입력 = input(f"회사 명 입력 : ")
    회사후보 = 모든회사목록.find_by_corp_name(이름입력, exactly=False, market='YK')

    if 회사후보 is None or len(회사후보) == 0:
        print("회사를 찾을 수 없습니다. 다시 입력해 주세요")
        return 회사이름찾기()
    elif len(회사후보) > 1:
        print(f"검색된 기업 {len(회사후보)}개. 정확한 사명 입력 필요합니다.")
        for i in 회사후보:
            print(i)
        두번째이름입력 = input(f"정확한 회사명 : ")
        회사후보 = 모든회사목록.find_by_corp_name(두번째이름입력, exactly=True, market='YK')
        if 회사후보 is None:
            return 회사이름찾기()

    global 회사
    회사 = 회사후보[0]
    print(f"--- [{회사.corp_name}] 데이터 추출 시작 ---")
    return 회사

def 재무제표추출():
    """⚡ 최적화된 재무제표 추출 (OpenDART API 직접 호출)"""
    global 재무제표
    global 회사_고유번호

    회사_고유번호 = 회사.corp_code

    api_data = fetch_single_company_statements_optimized(
        DART_API_KEY,
        회사_고유번호,
        회사.corp_name
    )

    if api_data is None:
        print("⚠️ API에서 데이터를 받지 못했습니다. dart_fss로 재시도 중...")
        try:
            재무제표 = dart.fs.extract(corp_code=회사_고유번호, bgn_de='20210101', end_de='20251231')
            return 재무제표
        except Exception as e:
            print(f"❌ 재무제표 추출 실패")
            return None

    재무제표 = convert_api_data_to_dataframe(api_data)

    if 재무제표 is None or not 재무제표:
        print("❌ 재무제표 데이터 변환 실패")
        return None

    return 재무제표

def 재무제표선택():
    """재무제표 선택"""
    print("\n📊 다음 중 하나를 선택하세요:")
    print("1. 손익계산서 (포괄손익계산서)")
    print("2. 재무상태표")
    print("3. 현금흐름표")
    print("4. 모두 보기")
    선택 = input("선택 (1-4): ").strip()
    return 선택

def 손익계산서찾기():
    """손익계산서 추출"""
    global 손익계산서, 결과1

    if 재무제표 is None:
        결과1 = None
        return None

    손익계산서 = 재무제표.get('is')
    if 손익계산서 is None or 손익계산서.empty:
        결과1 = None
        return None

    결과1 = 손익계산서.copy()
    return 결과1

def 재무상태표찾기():
    """재무상태표 추출"""
    global 재무상태표, 결과2

    if 재무제표 is None:
        결과2 = None
        return None

    재무상태표 = 재무제표.get('bs')
    if 재무상태표 is None or 재무상태표.empty:
        결과2 = None
        return None

    결과2 = 재무상태표.copy()
    return 결과2

def 현금흐름표찾기():
    """현금흐름표 추출"""
    global 현금흐름표, 결과3

    if 재무제표 is None:
        결과3 = None
        return None

    현금흐름표 = 재무제표.get('cf')
    if 현금흐름표 is None or 현금흐름표.empty:
        결과3 = None
        return None

    결과3 = 현금흐름표.copy()
    return 결과3

def 데이터가공1():
    """손익계산서 데이터 (이미 정렬된 상태)"""
    global df1
    df1 = 결과1.copy() if 결과1 is not None else None
    return df1

def 데이터가공2():
    """재무상태표 데이터 (이미 정렬된 상태)"""
    global df2
    df2 = 결과2.copy() if 결과2 is not None else None
    return df2

def 데이터가공3():
    """현금흐름표 데이터 (이미 정렬된 상태)"""
    global df3
    df3 = 결과3.copy() if 결과3 is not None else None
    return df3

def 손익계산서_그래프():
    """📊 손익계산서 5개년 matplotlib 시각화"""
    if df1 is None or df1.empty:
        print("❌ 손익계산서 데이터가 없습니다.")
        return

    all_rows = df1.index.tolist()
    print(f"\n📊 [{회사.corp_name}] 손익계산서 지표 목록:")
    for idx, row in enumerate(all_rows, 1):
        print(f"{idx}. {row}")

    선택_input = input("\n분석할 지표 번호를 입력하세요 (여러 개는 쉼표로 구분): ").strip()
    try:
        선택_idx = [int(x.strip())-1 for x in 선택_input.split(',')]
        selected_items = [all_rows[i] for i in 선택_idx if 0 <= i < len(all_rows)]
    except (ValueError, IndexError):
        print("❌ 잘못된 입력입니다.")
        return

    if not selected_items:
        print("❌ 선택된 지표가 없습니다.")
        return

    filtered_df = df1.loc[selected_items].copy()

    max_val = np.nanmax(np.abs(filtered_df.values))
    if np.isnan(max_val) or max_val == 0:
        scale = 1e12; unit_str = "조 원"
    elif max_val >= 1e12:
        scale = 1e12; unit_str = "조 원"
    elif max_val >= 1e8:
        scale = 1e8; unit_str = "억 원"
    else:
        scale = 1; unit_str = "원"

    plot_df_scaled = filtered_df / scale

    plt.figure(figsize=(12, 7))
    display_df = plot_df_scaled.T
    display_df.plot(marker='o', ax=plt.gca(), linewidth=2, markersize=6)

    ymin, ymax = plt.ylim()
    plt.ylim(ymin, ymax * 1.15)

    for i, column in enumerate(filtered_df.index):
        orig_values = filtered_df.loc[column].values
        y_values = plot_df_scaled.loc[column].values
        for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
            if np.isnan(orig_val):
                continue
            kor_text = 숫자줄이기(orig_val)
            offset = 12 if i % 2 == 0 else -18
            plt.annotate(
                kor_text, (x_idx, y_val),
                textcoords="offset points", xytext=(0, offset),
                ha='center', fontsize=8, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7)
            )

    plt.title(f'[{회사.corp_name}] 손익계산서 주요 지표 추이 (5개년)', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('연도 (Year)', fontsize=11)
    plt.ylabel(f'금액 (단위: {unit_str})', fontsize=11, fontweight='bold')
    plt.xticks(range(len(filtered_df.columns)), filtered_df.columns, rotation=45)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()

def 재무상태표_그래프():
    """📊 재무상태표 5개년 matplotlib 시각화"""
    if df2 is None or df2.empty:
        print("❌ 재무상태표 데이터가 없습니다.")
        return

    all_rows = df2.index.tolist()
    print(f"\n📊 [{회사.corp_name}] 재무상태표 지표 목록:")
    for idx, row in enumerate(all_rows, 1):
        print(f"{idx}. {row}")

    선택_input = input("\n분석할 지표 번호를 입력하세요 (여러 개는 쉼표로 구분): ").strip()
    try:
        선택_idx = [int(x.strip())-1 for x in 선택_input.split(',')]
        selected_items = [all_rows[i] for i in 선택_idx if 0 <= i < len(all_rows)]
    except (ValueError, IndexError):
        print("❌ 잘못된 입력입니다.")
        return

    if not selected_items:
        print("❌ 선택된 지표가 없습니다.")
        return

    filtered_df = df2.loc[selected_items].copy()

    max_val = np.nanmax(np.abs(filtered_df.values))
    if np.isnan(max_val) or max_val == 0:
        scale = 1e12; unit_str = "조 원"
    elif max_val >= 1e12:
        scale = 1e12; unit_str = "조 원"
    elif max_val >= 1e8:
        scale = 1e8; unit_str = "억 원"
    else:
        scale = 1; unit_str = "원"

    plot_df_scaled = filtered_df / scale

    plt.figure(figsize=(12, 7))
    display_df = plot_df_scaled.T
    display_df.plot(marker='o', ax=plt.gca(), linewidth=2, markersize=6)

    ymin, ymax = plt.ylim()
    plt.ylim(ymin, ymax * 1.15)

    for i, column in enumerate(filtered_df.index):
        orig_values = filtered_df.loc[column].values
        y_values = plot_df_scaled.loc[column].values
        for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
            if np.isnan(orig_val):
                continue
            kor_text = 숫자줄이기(orig_val)
            offset = 12 if i % 2 == 0 else -18
            plt.annotate(
                kor_text, (x_idx, y_val),
                textcoords="offset points", xytext=(0, offset),
                ha='center', fontsize=8, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7)
            )

    plt.title(f'[{회사.corp_name}] 재무상태표 주요 지표 추이 (5개년)', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('연도 (Year)', fontsize=11)
    plt.ylabel(f'금액 (단위: {unit_str})', fontsize=11, fontweight='bold')
    plt.xticks(range(len(filtered_df.columns)), filtered_df.columns, rotation=45)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()

def 현금흐름표_그래프():
    """📊 현금흐름표 5개년 matplotlib 시각화"""
    if df3 is None or df3.empty:
        print("❌ 현금흐름표 데이터가 없습니다.")
        return

    all_rows = df3.index.tolist()
    print(f"\n📊 [{회사.corp_name}] 현금흐름표 지표 목록:")
    for idx, row in enumerate(all_rows, 1):
        print(f"{idx}. {row}")

    선택_input = input("\n분석할 지표 번호를 입력하세요 (여러 개는 쉼표로 구분): ").strip()
    try:
        선택_idx = [int(x.strip())-1 for x in 선택_input.split(',')]
        selected_items = [all_rows[i] for i in 선택_idx if 0 <= i < len(all_rows)]
    except (ValueError, IndexError):
        print("❌ 잘못된 입력입니다.")
        return

    if not selected_items:
        print("❌ 선택된 지표가 없습니다.")
        return

    filtered_df = df3.loc[selected_items].copy()

    max_val = np.nanmax(np.abs(filtered_df.values))
    if np.isnan(max_val) or max_val == 0:
        scale = 1e12; unit_str = "조 원"
    elif max_val >= 1e12:
        scale = 1e12; unit_str = "조 원"
    elif max_val >= 1e8:
        scale = 1e8; unit_str = "억 원"
    else:
        scale = 1; unit_str = "원"

    plot_df_scaled = filtered_df / scale

    plt.figure(figsize=(12, 7))
    display_df = plot_df_scaled.T
    display_df.plot(marker='o', ax=plt.gca(), linewidth=2, markersize=6)

    ymin, ymax = plt.ylim()
    plt.ylim(ymin, ymax * 1.15)

    for i, column in enumerate(filtered_df.index):
        orig_values = filtered_df.loc[column].values
        y_values = plot_df_scaled.loc[column].values
        for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
            if np.isnan(orig_val):
                continue
            kor_text = 숫자줄이기(orig_val)
            offset = 12 if i % 2 == 0 else -18
            plt.annotate(
                kor_text, (x_idx, y_val),
                textcoords="offset points", xytext=(0, offset),
                ha='center', fontsize=8, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7)
            )

    plt.title(f'[{회사.corp_name}] 현금흐름표 주요 지표 추이 (5개년)', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('연도 (Year)', fontsize=11)
    plt.ylabel(f'금액 (단위: {unit_str})', fontsize=11, fontweight='bold')
    plt.xticks(range(len(filtered_df.columns)), filtered_df.columns, rotation=45)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()

def 계정자동매칭(계정이름):
    """해당 계정명을 IS/BS/CF에서 자동으로 찾기"""
    search_name = 계정정규화(계정이름)

    # 모든 재무제표에서 검색
    for table_name, df in [('IS', df1), ('BS', df2), ('CF', df3)]:
        if df is None or df.empty:
            continue

        for idx in df.index:
            if 계정정규화(idx) == search_name:
                return idx, table_name

    return None, None

def beneish_mscore_분석():
    """📊 Beneish M-Score 분석"""
    if 재무제표 is None:
        print("❌ 재무제표가 로드되지 않았습니다.")
        return

    print("\n" + "=" * 70)
    print("📊 Beneish M-Score 분석 (2024년 vs 2025년)")
    print("=" * 70)

    # 필요한 계정 목록
    required_accounts = {
        '매출': '2025년 매출',
        '매출원가': '2025년 매출원가',
        '판관비': '2025년 판관비',
        '당기순이익': '2025년 당기순이익',
        '매출채권': '2025년 매출채권',
        '유동자산': '2025년 유동자산',
        '유형자산': '2025년 유형자산',
        '총자산': '2025년 총자산',
        '총부채': '2025년 총부채',
        '영업활동현금흐름': '2025년 영업활동현금흐름'
    }

    print("\n🔍 필요한 계정을 매칭 중...\n")

    # 1단계: 자동 매칭 시도
    account_mapping = {}
    matched_count = 0

    for i, (req_account, description) in enumerate(required_accounts.items(), 1):
        matched_account, table_name = 계정자동매칭(req_account)

        if matched_account:
            account_mapping[req_account] = matched_account
            print(f"✅ {i}. {description}")
            print(f"   → 자동 매칭됨: [{matched_account}] ({table_name})")
            matched_count += 1
        else:
            print(f"⚠️ {i}. {description}")
            print(f"   → 자동 매칭 실패. 수동 입력 필요")

    print(f"\n✓ {matched_count}/{len(required_accounts)}개 계정 자동 매칭됨")

    # 2단계: 수동 입력 (매칭 실패한 계정)
    if matched_count < len(required_accounts):
        print("\n" + "-" * 70)
        print("📝 자동 매칭되지 않은 계정을 직접 선택해주세요")
        print("-" * 70)

        for req_account, description in required_accounts.items():
            if req_account in account_mapping:
                continue

            print(f"\n{description}를 찾아주세요:")
            print("사용 가능한 계정 목록:")

            all_accounts = []
            for table_name, df in [('IS', df1), ('BS', df2), ('CF', df3)]:
                if df is not None and not df.empty:
                    for idx in df.index:
                        all_accounts.append((idx, table_name))
                        print(f"  - [{idx}] ({table_name})")

            선택 = input(f"위 목록에서 '{req_account}' 계정명을 입력하세요: ").strip()
            if 선택 in [acc[0] for acc in all_accounts]:
                account_mapping[req_account] = 선택
                print(f"✅ 선택됨: {선택}")
            else:
                print(f"❌ 입력하신 계정을 찾을 수 없습니다.")
                return

    # 3단계: 감가상각비 직접 입력 (2024년, 2025년)
    print("\n" + "-" * 70)
    print("📝 감가상각비를 직접 입력해주세요")
    print("-" * 70)
    print("(성격별 비용 명세서에서 확인 필요)")

    try:
        감가상각비_2024 = float(input("\n2024년 감가상각비 (단위: 원): ").strip())
        감가상각비_2025 = float(input("2025년 감가상각비 (단위: 원): ").strip())
    except ValueError:
        print("❌ 올바른 숫자를 입력해주세요.")
        return

    # 4단계: M-Score 계산
    print("\n" + "=" * 70)
    print("📊 M-Score 계산 중...")
    print("=" * 70)

    try:
        # 2024년 데이터 추출
        df_2024 = df1.copy() if df1 is not None else None
        if df_2024 is None:
            df_2024 = df2.copy()

        year_2024 = '2024'
        year_2025 = '2025'

        # 필요한 값들 추출
        data_dict = {}
        for req_account, matched_account in account_mapping.items():
            # 데이터 찾기
            for df_name, df_data in [('is_data', df1), ('bs_data', df2), ('cf_data', df3)]:
                if df_data is not None and not df_data.empty:
                    if matched_account in df_data.index:
                        val_2024 = df_data.loc[matched_account, year_2024] if year_2024 in df_data.columns else np.nan
                        val_2025 = df_data.loc[matched_account, year_2025] if year_2025 in df_data.columns else np.nan
                        data_dict[req_account] = {'2024': val_2024, '2025': val_2025}
                        break

        # 각 8개 지수 계산
        print("\n📈 각 지수 계산 결과:\n")

        # 1. DSRI (Receivables Index)
        if '매출채권' in data_dict and '매출' in data_dict:
            ar_2024 = data_dict['매출채권']['2024']
            ar_2025 = data_dict['매출채권']['2025']
            sales_2024 = data_dict['매출']['2024']
            sales_2025 = data_dict['매출']['2025']

            if sales_2024 > 0 and sales_2025 > 0:
                dsri = (ar_2025 / sales_2025) / (ar_2024 / sales_2024)
                print(f"1️⃣ DSRI (Receivables Index): {dsri:.4f}")
            else:
                print(f"1️⃣ DSRI: 데이터 부족")

        # 2. GMI (Gross Margin Index)
        if '매출' in data_dict and '매출원가' in data_dict:
            sales_2024 = data_dict['매출']['2024']
            cogs_2024 = data_dict['매출원가']['2024']
            sales_2025 = data_dict['매출']['2025']
            cogs_2025 = data_dict['매출원가']['2025']

            if sales_2024 > 0 and sales_2025 > 0:
                gm_2024 = (sales_2024 - cogs_2024) / sales_2024
                gm_2025 = (sales_2025 - cogs_2025) / sales_2025

                if gm_2025 > 0:
                    gmi = gm_2024 / gm_2025
                    print(f"2️⃣ GMI (Gross Margin Index): {gmi:.4f}")
                else:
                    print(f"2️⃣ GMI: 데이터 부족")
            else:
                print(f"2️⃣ GMI: 데이터 부족")

        print("\n✅ M-Score 분석 완료!")
        print("(전체 M-Score 계산은 모든 8개 지수가 필요합니다)")

    except Exception as e:
        print(f"❌ 계산 중 오류 발생: {e}")
        return

def 이상변동률분석(fs_type='is'):
    """📊 24년 vs 25년 변동률 분석 - 시그마 ±2 이상 계정 탐지"""

    if 재무제표 is None:
        print("❌ 재무제표가 로드되지 않았습니다.")
        return

    if fs_type == 'is':
        df = 재무제표.get('is')
        table_name = "손익계산서"
    elif fs_type == 'bs':
        df = 재무제표.get('bs')
        table_name = "재무상태표"
    elif fs_type == 'cf':
        df = 재무제표.get('cf')
        table_name = "현금흐름표"
    else:
        print("❌ 잘못된 재무제표 타입입니다.")
        return

    if df is None or df.empty:
        print(f"❌ {table_name}에 데이터가 없습니다.")
        return

    cols = sorted([col for col in df.columns], reverse=True)
    year_2025 = None
    year_2024 = None

    for col in cols:
        if str(col).startswith('2025'):
            year_2025 = col
        elif str(col).startswith('2024'):
            year_2024 = col

    if year_2025 is None or year_2024 is None:
        print(f"❌ 25년 또는 24년 데이터가 없습니다. 사용 가능한 연도: {cols}")
        return

    print(f"\n{'='*70}")
    print(f"📊 {table_name} 변동률 분석 (2024년 vs 2025년)")
    print(f"{'='*70}\n")

    data_2024 = df[year_2024].copy()
    data_2025 = df[year_2025].copy()

    new_accounts = []
    discontinued_accounts = []
    seen_normalized = set()

    for account in df.index:
        normalized = 계정정규화(account)

        if normalized in seen_normalized:
            continue

        seen_normalized.add(normalized)

        val_2024 = data_2024.get(account)
        val_2025 = data_2025.get(account)

        val_2024_nan = pd.isna(val_2024) or val_2024 == 0
        val_2025_nan = pd.isna(val_2025) or val_2025 == 0

        if val_2024_nan and not val_2025_nan:
            new_accounts.append(normalized)
            print(f"🟢 [{account}] 새로 사용되는 계정입니다.")

        elif not val_2024_nan and val_2025_nan:
            discontinued_accounts.append(normalized)
            print(f"🔴 [{account}] 더이상 사용하지 않습니다.")

    valid_accounts = []
    change_rates = []
    processed_normalized = set()

    for account in df.index:
        normalized = 계정정규화(account)

        if normalized in new_accounts or normalized in discontinued_accounts:
            continue

        if normalized in processed_normalized:
            continue

        processed_normalized.add(normalized)

        val_2024 = data_2024.get(account)
        val_2025 = data_2025.get(account)

        if pd.isna(val_2024) or pd.isna(val_2025):
            continue

        val_2024 = float(val_2024)
        val_2025 = float(val_2025)

        if val_2024 == 0 and val_2025 == 0:
            continue

        if val_2024 == 0:
            continue

        change_rate = ((val_2025 - val_2024) / abs(val_2024)) * 100

        valid_accounts.append(account)
        change_rates.append(change_rate)

    if not change_rates:
        print("\n⚠️ 변동률을 계산할 수 있는 계정이 없습니다.")
        return

    change_rates_array = np.array(change_rates)
    mean_rate = np.mean(change_rates_array)
    std_rate = np.std(change_rates_array)

    print(f"\n📈 변동률 통계:")
    print(f"  • 평균 변동률: {mean_rate:+.2f}%")
    print(f"  • 표준편차(sigma): {std_rate:.2f}%")
    print(f"  • ±2 sigma 범위: {mean_rate - 2*std_rate:+.2f}% ~ {mean_rate + 2*std_rate:+.2f}%")

    upper_threshold = mean_rate + 2 * std_rate
    lower_threshold = mean_rate - 2 * std_rate

    outlier_accounts = []

    print(f"\n⚠️ Sigma ±2 초과 계정 (이상 변동률):")
    print(f"{'-'*70}")

    for account, rate in zip(valid_accounts, change_rates):
        if rate > upper_threshold or rate < lower_threshold:
            outlier_accounts.append((account, rate))

            val_2024 = float(data_2024.get(account))
            val_2025 = float(data_2025.get(account))

            sigma_count = abs(rate - mean_rate) / std_rate

            if rate > upper_threshold:
                print(f"🔺 [{account}]")
                print(f"   → 24년: {숫자줄이기(val_2024)} / 25년: {숫자줄이기(val_2025)}")
                print(f"   → 변동률: {rate:+.2f}% (sigma {sigma_count:.2f}배)")
                print(f"   → {account} 계정과목이 sigma 2를 초과하여 유의적입니다 (상승).\n")
            else:
                print(f"🔻 [{account}]")
                print(f"   → 24년: {숫자줄이기(val_2024)} / 25년: {숫자줄이기(val_2025)}")
                print(f"   → 변동률: {rate:+.2f}% (sigma {sigma_count:.2f}배)")
                print(f"   → {account} 계정과목이 sigma 2를 초과하여 유의적입니다 (하락).\n")

    if not outlier_accounts:
        print("✅ Sigma ±2를 초과하는 계정이 없습니다.\n")

    return {
        'mean': mean_rate,
        'std': std_rate,
        'outliers': outlier_accounts,
        'new_accounts': new_accounts,
        'discontinued_accounts': discontinued_accounts,
        'total_valid_accounts': len(valid_accounts)
    }

def 숫자줄이기(amount):
    """숫자를 한글 단위로 표시"""
    amount = float(amount)

    if abs(amount) >= 1000000000000:
        return f"{amount/1000000000000:.2f}조"
    elif abs(amount) >= 100000000:
        return f"{amount/100000000:.2f}억"
    else:
        return f"{amount:,.2f}"

def 프로그램_실행():
    """메인 프로그램"""
    print("=" * 60)
    print("📊 DART 재무제표 분석 프로그램")
    print("=" * 60)

    회사이름찾기()

    print("\n⏳ 재무제표 추출 중...")
    재무제표추출()
    print("✅ 완료!\n")

    손익계산서찾기()
    재무상태표찾기()
    현금흐름표찾기()

    데이터가공1()
    데이터가공2()
    데이터가공3()

    while True:
        print("\n" + "=" * 60)
        print("📋 원하는 기능을 선택하세요:")
        print("=" * 60)
        print("1. 재무제표 시각화 (라인 차트)")
        print("2. 이상 변동률 분석 - IS, BS, CF 자동 분석")
        print("3. Beneish M-Score 분석 (조정가능이익 판단)")
        print("4. 종료")
        기능선택 = input("선택 (1-4): ").strip()

        if 기능선택 == '1':
            print("\n" + "=" * 60)
            print("📈 확인하고 싶은 재무제표를 선택하세요.")
            print("=" * 60)
            선택 = 재무제표선택()

            if 선택 == '1' or 선택 == '4':
                print(f"\n📊 손익계산서 시각화...")
                손익계산서_그래프()

            if 선택 == '2' or 선택 == '4':
                print(f"\n📊 재무상태표 시각화...")
                재무상태표_그래프()

            if 선택 == '3' or 선택 == '4':
                print(f"\n📊 현금흐름표 시각화...")
                현금흐름표_그래프()

        elif 기능선택 == '2':
            print("\n" + "=" * 70)
            print("📊 모든 재무제표 변동률 분석 (24년 vs 25년)")
            print("=" * 70)

            print("\n" + "█" * 70)
            print("▶️ 1. 손익계산서 (IS)")
            print("█" * 70)
            이상변동률분석(fs_type='is')

            print("\n" + "█" * 70)
            print("▶️ 2. 재무상태표 (BS)")
            print("█" * 70)
            이상변동률분석(fs_type='bs')

            print("\n" + "█" * 70)
            print("▶️ 3. 현금흐름표 (CF)")
            print("█" * 70)
            이상변동률분석(fs_type='cf')

            print("\n" + "=" * 70)
            print("✅ 모든 분석이 완료되었습니다!")
            print("=" * 70)

        elif 기능선택 == '3':
            beneish_mscore_분석()

        elif 기능선택 == '4':
            print("\n프로그램을 종료합니다. 👋")
            break

        else:
            print("❌ 잘못된 선택입니다.")

if __name__ == "__main__":
    프로그램_실행()
