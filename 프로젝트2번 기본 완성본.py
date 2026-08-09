

import pandas as pd
import matplotlib.pyplot as plt
import dart_fss as dart
import re
import matplotlib.ticker as ticker
import numpy as np

API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"
dart.set_api_key(api_key=API_KEY)
import os
import sys
import subprocess
if os.name == 'nt':  # Windows인 경우
    plt.rc('font', family='Malgun Gothic')
else:  # Mac인 경우 (AppleGothic)
    plt.rc('font', family='AppleGothic')

# 그래프에서 마이너스(-) 기호가 깨지는 현상 방지
plt.rcParams['axes.unicode_minus'] = False

#1. corp_list 다운받기
모든회사목록 = dart.get_corp_list()

#2. 리스트에서 회사이름 찾기
def 회사이름찾기() :
    이름입력 = input(f"회사 명 입력 : ")
    회사후보 = 모든회사목록.find_by_corp_name(이름입력, exactly=False, market = 'YK')
    if 회사후보 is None or len(회사후보) == 0:
        print("회사를 찾을 수 없습니다. 다시 입력해 주세요")
        return
    elif len(회사후보) > 1: #여러 회사가 검색된 경우
        print(f"검색된 기업 {len(회사후보)}개. 정확한 사명 입력 필요합니다. 이 중 입력해주세요.")
        for i in 회사후보 :
           print(i)
        두번째이름입력 = input(f"정확한 회사명 : ")
        회사후보 = 모든회사목록.find_by_corp_name(두번째이름입력, exactly=True, market = 'YKNE')
        if 회사후보 is None:
            return 회사이름찾기()
    global 회사
    회사 = 회사후보[0]
    print(f"--- [{회사.corp_name}] 데이터 추출 시작 ---")
    return 회사

#3. 찾은 회사의 재무제표 추출
def 재무제표추출() :
    global 재무제표
    print(f"{회사} 재무제표 추출중")
    재무제표 = dart.fs.extract(corp_code=회사.corp_code, bgn_de='20240101', end_de = '20261231') #5년치 정보 추출
    return 재무제표

#3.5 재무상태표, 손익계산서, 현금흐름표 선택
def 재무제표선택() :
    print("\n📊 다음 중 하나를 선택하세요:")
    print("1. 손익계산서 (포괄손익계산서)")
    print("2. 재무상태표")
    print("3. 현금흐름표")
    print("4. 모두 보기")
    선택 = input("선택 (1-4): ").strip()
    return 선택

#4.1 손익계산서
def 손익계산서찾기() :
    global 손익계산서
    global 결과1
    손익계산서 = 재무제표['is'] #원칙적으로 손익계산서, 없으면 포괄손익계산서
    if 손익계산서 is None:
        손익계산서 = 재무제표['cis']
    if 손익계산서 is None:
        print(f"손익계산서, 포괄손익계산서 항목이 모두 없습니다.")
        return None
    first_level_header = 손익계산서.columns[0][0]
    결과1 = 손익계산서.loc[:]
    ##손익계산서 두번째 레벨에 label_ko(계정과목)가 존재
    ##모든계정추출
    return 결과1

#4.2 재무상태표찾기
def 재무상태표찾기() :
    global 재무상태표
    global 결과2
    재무상태표 = 재무제표['bs'] #원칙적으로 손익계산서, 없으면 포괄손익계산서
    if 재무상태표 is None:
        print(f"손익계산서, 포괄손익계산서 항목이 모두 없습니다.")
        return None
    first_level_header = 재무상태표.columns[0][0]
    결과2 = 재무상태표.loc[:]
    ##재무상태표 두번째 레벨에 label_ko(계정과목)가 존재
    ##모든계정추출
    return 결과2

#4.3 현금흐름표
def 현금흐름표찾기() :
    global 현금흐름표
    global 결과3
    현금흐름표 = 재무제표['cf'] #원칙적으로 손익계산서, 없으면 포괄손익계산서
    if 현금흐름표 is None:
        현금흐름표 = 재무제표['ccf']
    if 현금흐름표 is None:
        print(f"현금흐름표, 연결현금흐름표 항목이 모두 없습니다.")
        return None
    first_level_header = 현금흐름표.columns[0][0]
    결과3 = 현금흐름표.loc[:]
    ##손익계산서 두번째 레벨에 label_ko(계정과목)가 존재
    ##모든계정추출
    return 결과3

#5. 한국어 라벨과, 5년치 데이터열 추출
def 데이터가공1() :
    global df1
    df1 = 결과1.filter(regex = r'label_ko|\d{8}-\d{8}')
    return df1

def 데이터가공2() :
    global df2
    df2 = 결과2.filter(regex = r'label_ko|\d{8}')
    return df2

def 데이터가공3() :
    global df3
    df3 = 결과3.filter(regex = r'label_ko|\d{8}-\d{8}')
    return df3

# 6.1 손익계산서 뽑아서 표시하기
def 손익계산서_그래프():
    all_rows = df1.iloc[:, 0].tolist()
    print(f"\n📊 [{회사.corp_name}] 손익계산서 지표 목록:")
    for idx, row in enumerate(all_rows, 1):
        print(f"{idx}. {row}")
    
    선택_input = input("\n분석할 지표 번호를 입력하세요 (여러 개는 쉼표로 구분, 예: 1,3,5): ").strip()
    try:
        선택_idx = [int(x.strip())-1 for x in 선택_input.split(',')]
        selected_items = [all_rows[i] for i in 선택_idx if 0 <= i < len(all_rows)]
    except (ValueError, IndexError):
        print("❌ 잘못된 입력입니다.")
        return
    
    if not selected_items:
        print("❌ 선택된 지표가 없습니다.")
        return

    label_col_name = df1.columns[0]
    filtered_df = df1[df1[label_col_name].isin(selected_items)].copy()
    filtered_df = filtered_df.set_index(label_col_name)

    years_columns = ['20210101-20211231', '20220101-20221231', '20230101-20231231', '20240101-20241231', '20250101-20251231']
    valid_years = [col for col in years_columns if col in filtered_df.columns]
    plot_df = filtered_df[valid_years]

    # 🔥 [핵심] 선택된 데이터 중 최댓값을 기준으로 '조' 또는 '억' 단위 유동적 결정!
    max_val = np.nanmax(np.abs(plot_df.values))

    if np.isnan(max_val) or max_val == 0:
        scale = 1e12
        unit_str = "조 원"
    elif max_val >= 1e12:      # 1조 이상일 때
        scale = 1e12
        unit_str = "조 원"
    elif max_val >= 1e8:       # 1억 이상 ~ 1조 미만일 때
        scale = 1e8
        unit_str = "억 원"
    else:                      # 1억 미만일 때
        scale = 1
        unit_str = "원"

    # 결정된 스케일(scale)로 나누기
    plot_df_scaled = plot_df / scale

    plt.figure(figsize=(11, 7))
    display_df = plot_df_scaled.T
    display_df.index = [col[:4] for col in valid_years]

    display_df.plot(marker='o', ax=plt.gca(), linewidth=2, markersize=6)
    ymin, ymax = plt.ylim()
    plt.ylim(ymin, ymax * 1.15)

    for i, column in enumerate(plot_df.index):
        orig_values = plot_df.loc[column].values           # 말풍선 표시용 원본 금액
        y_values = plot_df_scaled.loc[column].values       # 그래프 위치용 스케일 변환 금액
        for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
            if np.isnan(orig_val):
                continue
            kor_text = 숫자줄이기(orig_val)
            offset = 12 if i % 2 == 0 else -18
            plt.annotate(
                kor_text, (x_idx, y_val),
                textcoords="offset points", xytext=(0, offset),
                ha='center', fontsize=9, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7)
            )
    plt.title(f'[{회사.corp_name}] 손익계산서 주요 지표 추이', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('연도 (Year)', fontsize=12)
    plt.ylabel(f'금액 (단위: {unit_str})', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.show()

# 6.2 재무상태표 뽑아서 표시하기
def 재무상태표_그래프():
    all_rows = df2.iloc[:, 0].tolist()
    print(f"\n📊 [{회사.corp_name}] 재무상태표 지표 목록:")
    for idx, row in enumerate(all_rows, 1):
        print(f"{idx}. {row}")
    
    선택_input = input("\n분석할 지표 번호를 입력하세요 (여러 개는 쉼표로 구분, 예: 1,3,5): ").strip()
    try:
        선택_idx = [int(x.strip())-1 for x in 선택_input.split(',')]
        selected_items = [all_rows[i] for i in 선택_idx if 0 <= i < len(all_rows)]
    except (ValueError, IndexError):
        print("❌ 잘못된 입력입니다.")
        return
    
    if not selected_items:
        print("❌ 선택된 지표가 없습니다.")
        return

    label_col_name = df2.columns[0]
    filtered_df = df2[df2[label_col_name].isin(selected_items)].copy()
    filtered_df = filtered_df.set_index(label_col_name)

    years_columns = ['20211231', '20221231', '20231231', '20241231', '20251231']
    valid_years = [col for col in years_columns if col in filtered_df.columns]
    plot_df = filtered_df[valid_years]

    # 🔥 [핵심] 유동적 스케일 계산
    max_val = np.nanmax(np.abs(plot_df.values))
    if np.isnan(max_val) or max_val == 0:
        scale = 1e12; unit_str = "조 원"
    elif max_val >= 1e12:
        scale = 1e12; unit_str = "조 원"
    elif max_val >= 1e8:
        scale = 1e8; unit_str = "억 원"
    else:
        scale = 1; unit_str = "원"

    plot_df_scaled = plot_df / scale

    plt.figure(figsize=(11, 7))
    display_df = plot_df_scaled.T
    display_df.index = [col[:4] for col in valid_years]

    display_df.plot(marker='o', ax=plt.gca(), linewidth=2, markersize=6)
    ymin, ymax = plt.ylim()
    plt.ylim(ymin, ymax * 1.15)

    for i, column in enumerate(plot_df.index):
        orig_values = plot_df.loc[column].values
        y_values = plot_df_scaled.loc[column].values
        for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
            if np.isnan(orig_val):
                continue
            kor_text = 숫자줄이기(orig_val)
            offset = 12 if i % 2 == 0 else -18
            plt.annotate(
                kor_text, (x_idx, y_val),
                textcoords="offset points", xytext=(0, offset),
                ha='center', fontsize=9, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7)
            )
    plt.title(f'[{회사.corp_name}] 재무상태표 주요 지표 추이', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('연도 (Year)', fontsize=12)
    plt.ylabel(f'금액 (단위: {unit_str})', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.show()

# 6.3 현금흐름표 뽑아서 표시하기
def 현금흐름표_그래프():
    all_rows = df3.iloc[:, 0].tolist()
    print(f"\n📊 [{회사.corp_name}] 현금흐름표 지표 목록:")
    for idx, row in enumerate(all_rows, 1):
        print(f"{idx}. {row}")
    
    선택_input = input("\n분석할 지표 번호를 입력하세요 (여러 개는 쉼표로 구분, 예: 1,3,5): ").strip()
    try:
        선택_idx = [int(x.strip())-1 for x in 선택_input.split(',')]
        selected_items = [all_rows[i] for i in 선택_idx if 0 <= i < len(all_rows)]
    except (ValueError, IndexError):
        print("❌ 잘못된 입력입니다.")
        return
    
    if not selected_items:
        print("❌ 선택된 지표가 없습니다.")
        return

    label_col_name = df3.columns[0]
    filtered_df = df3[df3[label_col_name].isin(selected_items)].copy()
    filtered_df = filtered_df.set_index(label_col_name)

    years_columns = ['20210101-20211231', '20220101-20221231', '20230101-20231231', '20240101-20241231', '20250101-20251231']
    valid_years = [col for col in years_columns if col in filtered_df.columns]
    plot_df = filtered_df[valid_years]

    # 🔥 [핵심] 유동적 스케일 계산
    max_val = np.nanmax(np.abs(plot_df.values))
    if np.isnan(max_val) or max_val == 0:
        scale = 1e12; unit_str = "조 원"
    elif max_val >= 1e12:
        scale = 1e12; unit_str = "조 원"
    elif max_val >= 1e8:
        scale = 1e8; unit_str = "억 원"
    else:
        scale = 1; unit_str = "원"

    plot_df_scaled = plot_df / scale

    plt.figure(figsize=(11, 7))
    display_df = plot_df_scaled.T
    display_df.index = [col[:4] for col in valid_years]

    display_df.plot(marker='o', ax=plt.gca(), linewidth=2, markersize=6)
    ymin, ymax = plt.ylim()
    plt.ylim(ymin, ymax * 1.15)

    for i, column in enumerate(plot_df.index):
        orig_values = plot_df.loc[column].values
        y_values = plot_df_scaled.loc[column].values
        for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
            if np.isnan(orig_val):
                continue
            kor_text = 숫자줄이기(orig_val)
            offset = 12 if i % 2 == 0 else -18
            plt.annotate(
                kor_text, (x_idx, y_val),
                textcoords="offset points", xytext=(0, offset),
                ha='center', fontsize=9, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7)
            )
    plt.title(f'[{회사.corp_name}] 현금흐름표 주요 지표 추이', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('연도 (Year)', fontsize=12)
    plt.ylabel(f'금액 (단위: {unit_str})', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.show()

#8. 숫자 줄이기
def 숫자줄이기(amount):
    """숫자가 너무 크면 '조', '억' 단위로 바꿔주는 함수 (소수점 2자리)"""
    amount = float(amount) # 확실하게 실수형으로 변환

    if abs(amount) >= 1000000000000: # 1조 이상
        # :.2f -> 소수점 둘째 자리까지 표시 (예: 12.34조)
        return f"{amount/1000000000000:.2f}조"
    elif abs(amount) >= 100000000: # 1억 이상
        return f"{amount/100000000:.2f}억"
    else:
        # 일반 숫자도 소수점 둘째 자리까지 + 콤마 (예: 12,345.00)
        return f"{amount:,.2f}"


def 숫자줄이기2(amount):

    amount = float(amount)*100.0 # 확실하게 실수형으로 변환

    if abs(amount) >= 1000000000000: # 1조 이상
        # :.2f -> 소수점 둘째 자리까지 표시 (예: 12.34조)
        return f"{amount/1000000000000:.2f}조"
    elif abs(amount) >= 100000000: # 1억 이상
        return f"{amount/100000000:.2f}억"
    else:
        # 일반 숫자도 소수점 둘째 자리까지 + 콤마 (예: 12,345.00)
        return f"{amount:,.2f}%"

def 프로그램_실행():
    print("=" * 50)
    print("📊 DART 재무제표 인터랙티브 시각화 프로그램 시작")
    print("=" * 50)

    # 1단계: 회사 검색 및 지정
    회사이름찾기()

    # 2단계: 5년치 재무제표 추출
    재무제표추출()
    print("✅ 재무제표 추출 완료! 데이터 파싱을 시작합니다...")

    # 3단계: 표별 데이터 찾기 및 가공
    손익계산서찾기()
    재무상태표찾기()
    현금흐름표찾기()

    데이터가공1()
    데이터가공2()
    데이터가공3()
    print("✅ 데이터 가공 완료!\n")

    # 4단계: 어떤 재무제표를 볼지 선택
    print("=" * 50)
    print("📈 확인하고 싶은 재무제표를 선택하세요.")
    print("=" * 50)
    선택 = 재무제표선택()
    
    if 선택 == '1' or 선택 == '4':
        print(f"\n📊 손익계산서 분석 시작...")
        손익계산서_그래프()
    
    if 선택 == '2' or 선택 == '4':
        print(f"\n📊 재무상태표 분석 시작...")
        재무상태표_그래프()
    
    if 선택 == '3' or 선택 == '4':
        print(f"\n📊 현금흐름표 분석 시작...")
        현금흐름표_그래프()

# ==========================================
# 프로그램 단일 실행 명령어
# ==========================================

if __name__ == "__main__":
    프로그램_실행()





