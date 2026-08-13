# -*- coding: utf-8 -*-
"""
프로젝트3: 최적화된 DART 재무제표 인터랙티브 시각화 프로그램
Description: 프로젝트2의 시각화 기능은 유지하면서,
             OpenDART API 직접 호출로 빠른 재무제표 추출 구현
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

if os.name == 'nt':  # Windows인 경우
    plt.rc('font', family='Malgun Gothic')
else:  # Mac인 경우 (AppleGothic)
    plt.rc('font', family='AppleGothic')

# 그래프에서 마이너스(-) 기호가 깨지는 현상 방지
plt.rcParams['axes.unicode_minus'] = False

# ========== 🔥 최적화된 추출 로직 (다운로드3에서 개선) ==========

def get_corp_code_from_dart_api(corp_name):
    """OpenDART API를 통해 기업명으로 고유번호 조회"""
    print(f"[INFO] OpenDART에서 '{corp_name}' 고유번호를 조회 중...")
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={DART_API_KEY}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_data = zf.read('CORPCODE.xml')

        root = ET.fromstring(xml_data)

        for list_node in root.findall('list'):
            corp_name_tag = list_node.findtext('corp_name')
            corp_code_tag = list_node.findtext('corp_code')

            if corp_name_tag and corp_name in corp_name_tag:
                return corp_code_tag.strip()

        return None
    except Exception as e:
        print(f"[ERROR] 고유번호 조회 중 오류 발생: {e}")
        return None

def fetch_single_company_statements_optimized(api_key, corp_code, corp_name):
    """⚡ 단일 회사 5개년 재무제표 고속 추출 (OpenDART API 직접 호출)"""
    print(f"[INFO] '{corp_name}' 5개년 재무제표 추출 중 (OpenDART API 이용)...")

    api_url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    all_years_data = []

    # 2025, 2024, 2023, 2022, 2021 순으로 5개년 데이터 수집
    for year in ['2025', '2024', '2023', '2022', '2021']:
        year_data = None

        for fs_div in ['CFS', 'OFS']:  # 연결재무제표 우선, 개별재무제표 폴백
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
                    print(f"[SUCCESS] '{corp_name}' {year}년 {fs_div} 데이터 추출 완료! ({len(year_data)}개 항목)")

                    # 🔥 첫 행의 키를 확인하여 데이터 구조 검증
                    if year_data and len(year_data) > 0:
                        first_row = year_data[0]
                        print(f"[DEBUG] API 응답 샘플 키: {list(first_row.keys())}")
                        print(f"[DEBUG] 첫번째 행: {first_row}")

                    break  # 첫 성공한 fs_div 사용

                elif status == '013':
                    print(f"[DEBUG] {year}년 {fs_div} - 조회 데이터 없음")
                    continue
                else:
                    print(f"[API WARNING] {year}년 {fs_div} - 상태코드: {status}")

            except Exception as e:
                print(f"[API ERROR] {corp_name} {year}년 조회 중: {e}")

            time.sleep(0.05)

        if year_data:
            # 각 연도 데이터에 연도 정보 추가
            for row in year_data:
                row['bsns_year'] = year
            all_years_data.extend(year_data)

    print(f"\n[INFO] 총 수집된 데이터: {len(all_years_data)}개 행")
    return all_years_data if all_years_data else None

def convert_api_data_to_dataframe(api_data):
    """OpenDART API 5개년 데이터를 DataFrame으로 변환"""
    if not api_data:
        print("[DEBUG] api_data가 비어있습니다.")
        return None

    # 재무제표별 분류
    bs_data = {}  # {account_nm: {year: amount}}
    is_data = {}
    cis_data = {}
    cf_data = {}

    for row in api_data:
        sj_div = row.get('sj_div')
        account = row.get('account_nm')
        year = str(row.get('bsns_year', ''))
        amount = row.get('thstrm_amount')  # 🔥 수정: thstrm_amount (올바른 키)

        if not account:
            continue

        # 금액이 None이거나 숫자가 아니면 스킵
        try:
            if amount is not None:
                amount = float(amount)
            else:
                amount = np.nan
        except (TypeError, ValueError):
            amount = np.nan

        # 연도별 데이터 딕셔너리에 저장
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

    print(f"\n[✅ 변환 완료] BS: {len(bs_data)}개, IS: {len(is_data)}개, CIS: {len(cis_data)}개, CF: {len(cf_data)}개 계정과목")

    # 데이터프레임 생성 및 정렬
    fs_dict = {}

    if bs_data:
        bs_df = pd.DataFrame(bs_data).T
        year_cols = sorted([col for col in bs_df.columns if col], reverse=True)
        bs_df = bs_df[[col for col in year_cols if col in bs_df.columns]]
        if not bs_df.empty:
            fs_dict['bs'] = bs_df
            print(f"  📊 재무상태표(BS): {bs_df.shape[0]}개 항목 × {bs_df.shape[1]}개 연도")

    if is_data:
        is_df = pd.DataFrame(is_data).T
        year_cols = sorted([col for col in is_df.columns if col], reverse=True)
        is_df = is_df[[col for col in year_cols if col in is_df.columns]]
        if not is_df.empty:
            fs_dict['is'] = is_df
            print(f"  📊 손익계산서(IS): {is_df.shape[0]}개 항목 × {is_df.shape[1]}개 연도")

    elif cis_data:
        cis_df = pd.DataFrame(cis_data).T
        year_cols = sorted([col for col in cis_df.columns if col], reverse=True)
        cis_df = cis_df[[col for col in year_cols if col in cis_df.columns]]
        if not cis_df.empty:
            fs_dict['is'] = cis_df
            print(f"  📊 포괄손익계산서(CIS): {cis_df.shape[0]}개 항목 × {cis_df.shape[1]}개 연도")

    if cf_data:
        cf_df = pd.DataFrame(cf_data).T
        year_cols = sorted([col for col in cf_df.columns if col], reverse=True)
        cf_df = cf_df[[col for col in year_cols if col in cf_df.columns]]
        if not cf_df.empty:
            fs_dict['cf'] = cf_df
            print(f"  📊 현금흐름표(CF): {cf_df.shape[0]}개 항목 × {cf_df.shape[1]}개 연도")

    if not fs_dict:
        print("[DEBUG] 변환된 DataFrame이 비어있습니다.")
        return None

    return fs_dict

# ========== 기존 프로젝트2 로직 (수정) ==========

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
        회사후보 = 모든회사목록.find_by_corp_name(두번째이름입력, exactly=True, market='YKNE')
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

    # dart_fss의 회사 고유번호 사용 (또는 API로 조회)
    회사_고유번호 = 회사.corp_code
    print(f"[DEBUG] 회사 고유번호: {회사_고유번호}")

    # OpenDART API로 재무제표 추출
    api_data = fetch_single_company_statements_optimized(
        DART_API_KEY,
        회사_고유번호,
        회사.corp_name
    )

    if api_data is None:
        print("[ERROR] API에서 데이터를 받지 못했습니다.")
        print("[TIP] dart_fss를 사용한 폴백 모드로 전환합니다...")
        try:
            재무제표 = dart.fs.extract(corp_code=회사_고유번호, bgn_de='20210101', end_de='20251231')
            print("[SUCCESS] dart_fss에서 재무제표를 추출했습니다.")
            return 재무제표
        except Exception as e:
            print(f"[ERROR] dart_fss 폴백도 실패했습니다: {e}")
            return None

    print(f"[DEBUG] API 데이터 수집 완료 (총 {len(api_data)}개 행)")

    # 데이터를 처리 가능한 형태로 변환
    재무제표 = convert_api_data_to_dataframe(api_data)

    if 재무제표 is None or not 재무제표:
        print("[ERROR] 재무제표 데이터 변환 실패")
        return None

    print(f"[DEBUG] 변환된 재무제표 키: {list(재무제표.keys())}")
    for key, df in 재무제표.items():
        if df is not None:
            print(f"  - {key}: {df.shape[0]}개 항목, {df.shape[1]}개 연도")

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
        print("❌ 재무제표가 로드되지 않았습니다.")
        결과1 = None
        return None

    손익계산서 = 재무제표.get('is')
    if 손익계산서 is None or 손익계산서.empty:
        print("⚠️ 손익계산서 항목이 없습니다.")
        결과1 = None
        return None

    결과1 = 손익계산서.copy()
    print(f"✅ 손익계산서 추출: {결과1.shape[0]}개 항목")
    return 결과1

def 재무상태표찾기():
    """재무상태표 추출"""
    global 재무상태표, 결과2

    if 재무제표 is None:
        print("❌ 재무제표가 로드되지 않았습니다.")
        결과2 = None
        return None

    재무상태표 = 재무제표.get('bs')
    if 재무상태표 is None or 재무상태표.empty:
        print("⚠️ 재무상태표 항목이 없습니다.")
        결과2 = None
        return None

    결과2 = 재무상태표.copy()
    print(f"✅ 재무상태표 추출: {결과2.shape[0]}개 항목")
    return 결과2

def 현금흐름표찾기():
    """현금흐름표 추출"""
    global 현금흐름표, 결과3

    if 재무제표 is None:
        print("❌ 재무제표가 로드되지 않았습니다.")
        결과3 = None
        return None

    현금흐름표 = 재무제표.get('cf')
    if 현금흐름표 is None or 현금흐름표.empty:
        print("⚠️ 현금흐름표 항목이 없습니다.")
        결과3 = None
        return None

    결과3 = 현금흐름표.copy()
    print(f"✅ 현금흐름표 추출: {결과3.shape[0]}개 항목")
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

    # 🔥 유동적 스케일 계산
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

    # 🔥 유동적 스케일 계산
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

    # 🔥 유동적 스케일 계산
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

def 이상변동률분석(fs_type='is'):
    """📊 24년 vs 25년 변동률 분석 - 시그마 ±2 이상 계정 탐지"""

    if 재무제표 is None:
        print("❌ 재무제표가 로드되지 않았습니다.")
        return

    # 분석 대상 재무제표 선택
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

    # 24년과 25년 컬럼 찾기
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

    # 데이터 추출
    data_2024 = df[year_2024].copy()
    data_2025 = df[year_2025].copy()

    # 1단계: 새로 생기거나 사라진 계정 식별
    new_accounts = []  # 25년에만 있는 계정
    discontinued_accounts = []  # 24년에만 있는 계정

    for account in df.index:
        val_2024 = data_2024.get(account)
        val_2025 = data_2025.get(account)

        # NaN 체크
        val_2024_nan = pd.isna(val_2024) or val_2024 == 0
        val_2025_nan = pd.isna(val_2025) or val_2025 == 0

        # 새로 생긴 계정 (24년: 0 or NaN, 25년: 값 있음)
        if val_2024_nan and not val_2025_nan:
            new_accounts.append(account)
            print(f"🟢 [{account}] 새로 사용되는 계정입니다.")

        # 사라진 계정 (24년: 값 있음, 25년: 0 or NaN)
        elif not val_2024_nan and val_2025_nan:
            discontinued_accounts.append(account)
            print(f"🔴 [{account}] 더이상 사용하지 않습니다.")

    # 2단계: 변동률 계산 (새로/사라진 계정 제외)
    valid_accounts = []
    change_rates = []

    for account in df.index:
        # 제외 대상
        if account in new_accounts or account in discontinued_accounts:
            continue

        val_2024 = data_2024.get(account)
        val_2025 = data_2025.get(account)

        # 둘 다 NaN인 경우 제외
        if pd.isna(val_2024) or pd.isna(val_2025):
            continue

        val_2024 = float(val_2024)
        val_2025 = float(val_2025)

        # 24년과 25년 모두 0인 경우 제외
        if val_2024 == 0 and val_2025 == 0:
            continue

        # 24년만 0인 경우 제외 (무한대 변동률)
        if val_2024 == 0:
            continue

        # 변동률 계산: ((25년 - 24년) / |24년|) × 100
        change_rate = ((val_2025 - val_2024) / abs(val_2024)) * 100

        valid_accounts.append(account)
        change_rates.append(change_rate)

    if not change_rates:
        print("\n⚠️ 변동률을 계산할 수 있는 계정이 없습니다.")
        return

    # 3단계: 평균과 표준편차 계산
    change_rates_array = np.array(change_rates)
    mean_rate = np.mean(change_rates_array)
    std_rate = np.std(change_rates_array)

    print(f"\n📈 변동률 통계:")
    print(f"  • 평균 변동률: {mean_rate:+.2f}%")
    print(f"  • 표준편차(σ): {std_rate:.2f}%")
    print(f"  • ±2σ 범위: {mean_rate - 2*std_rate:+.2f}% ~ {mean_rate + 2*std_rate:+.2f}%")

    # 4단계: 시그마 ±2 초과 계정 찾기
    upper_threshold = mean_rate + 2 * std_rate
    lower_threshold = mean_rate - 2 * std_rate

    outlier_accounts = []

    print(f"\n⚠️ 시그마 ±2 초과 계정 (이상 변동률):")
    print(f"{'-'*70}")

    for account, rate in zip(valid_accounts, change_rates):
        if rate > upper_threshold or rate < lower_threshold:
            outlier_accounts.append((account, rate))

            val_2024 = float(data_2024.get(account))
            val_2025 = float(data_2025.get(account))

            # 표시 형식
            sigma_count = abs(rate - mean_rate) / std_rate

            if rate > upper_threshold:
                print(f"🔺 [{account}]")
                print(f"   → 24년: {숫자줄이기(val_2024)} / 25년: {숫자줄이기(val_2025)}")
                print(f"   → 변동률: {rate:+.2f}% (σ {sigma_count:.2f}배)")
                print(f"   → 유의적입니다 (상승).\n")
            else:
                print(f"🔻 [{account}]")
                print(f"   → 24년: {숫자줄이기(val_2024)} / 25년: {숫자줄이기(val_2025)}")
                print(f"   → 변동률: {rate:+.2f}% (σ {sigma_count:.2f}배)")
                print(f"   → 유의적입니다 (하락).\n")

    if not outlier_accounts:
        print("✅ 시그마 ±2를 초과하는 계정이 없습니다.\n")

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
    print("=" * 50)
    print("📊 DART 재무제표 최적화 시각화 프로그램 시작")
    print("(OpenDART API 고속 추출 버전)")
    print("=" * 50)

    # 1단계: 회사 검색
    회사이름찾기()

    # 2단계: 재무제표 추출 (최적화됨)
    재무제표추출()
    print("✅ 재무제표 추출 완료! 데이터 파싱을 시작합니다...")

    # 3단계: 재무제표 추출 및 가공
    손익계산서찾기()
    재무상태표찾기()
    현금흐름표찾기()

    데이터가공1()
    데이터가공2()
    데이터가공3()
    print("✅ 데이터 가공 완료!\n")

    # 4단계: 재무제표 선택 및 표시
    print("=" * 50)
    print("📈 확인하고 싶은 재무제표를 선택하세요.")
    print("=" * 50)
    선택 = 재무제표선택()

    if 선택 == '1' or 선택 == '4':
        print(f"\n📊 손익계산서 분석...")
        손익계산서_그래프()

    if 선택 == '2' or 선택 == '4':
        print(f"\n📊 재무상태표 분석...")
        재무상태표_그래프()

    if 선택 == '3' or 선택 == '4':
        print(f"\n📊 현금흐름표 분석...")
        현금흐름표_그래프()

if __name__ == "__main__":
    프로그램_실행()
