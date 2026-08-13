import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import dart_fss as dart
import re
import matplotlib.ticker as ticker
import numpy as np
import os
import sys

# [추가] 웹 페이지 기본 설정
st.set_page_config(page_title="DART 재무제표 대시보드", page_icon="📊", layout="wide")

API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"
dart.set_api_key(api_key=API_KEY)

if os.name == 'nt':  # Windows인 경우
    plt.rc('font', family='Malgun Gothic')
else:  # Mac인 경우 (AppleGothic)
    plt.rc('font', family='AppleGothic')

# 그래프에서 마이너스(-) 기호가 깨지는 현상 방지
plt.rcParams['axes.unicode_minus'] = False

# [수정] 1. corp_list 다운받기 (웹에서 매번 다운받지 않도록 캐싱 처리만 추가)
@st.cache_resource
def get_corp_list_cached():
    return dart.get_corp_list()

with st.spinner("DART에서 회사 목록을 불러오는 중입니다..."):
    모든회사목록 = get_corp_list_cached()

st.title("📊 DART 재무제표 인터랙티브 시각화 프로그램")
st.markdown("---")

# 8. 숫자 줄이기 (원본 함수 그대로 유지!)
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
        return f"{amount/1000000000000:.2f}조"
    elif abs(amount) >= 100000000: # 1억 이상
        return f"{amount/100000000:.2f}억"
    else:
        return f"{amount:,.2f}%"

# --- [사이드바] 2. 리스트에서 회사이름 찾기 (input -> st.text_input 변환) ---
with st.sidebar:
    st.header("🔍 회사 검색")
    이름입력 = st.text_input("회사 명 입력 :", value="")

if not 이름입력:
    st.info("👈 왼쪽 사이드바에서 분석하고 싶은 회사명을 입력해 주세요! (예: 삼성전자)")
    st.stop()

# 원본 검색 로직 그대로 적용
회사후보 = 모든회사목록.find_by_corp_name(이름입력, exactly=False, market='YK')

if 회사후보 is None or len(회사후보) == 0:
    st.sidebar.error("회사를 찾을 수 없습니다. 다시 입력해 주세요")
    st.stop()
elif len(회사후보) > 1: #여러 회사가 검색된 경우
    st.sidebar.warning(f"검색된 기업 {len(회사후보)}개. 정확한 사명 선택이 필요합니다.")
    후보목록 = [f"{c.corp_name} ({c.stock_code})" for c in 회사후보]
    선택된이름 = st.sidebar.selectbox("이 중 선택해주세요:", 후보목록)
    선택_idx = 후보목록.index(선택된이름)
    회사 = 회사후보[선택_idx]
else:
    회사 = 회사후보[0]

st.sidebar.success(f"--- [{회사.corp_name}] 데이터 추출 시작 ---")

# 3. 찾은 회사의 재무제표 추출 (속도를 위해 캐싱 적용, 로직은 원본 그대로)
@st.cache_data
def 재무제표추출_cached(corp_code):
    return dart.fs.extract(corp_code=corp_code, bgn_de='20240101', end_de='20261231') #5년치 정보 추출

with st.spinner(f"{회사.corp_name} 재무제표 추출중..."):
    재무제표 = 재무제표추출_cached(회사.corp_code)

# 4.1 손익계산서 (원본 대괄호 [] 로직 100% 복원!)
def 손익계산서찾기():
    global 손익계산서, 결과1
    손익계산서 = 재무제표['is'] #원칙적으로 손익계산서, 없으면 포괄손익계산서
    if 손익계산서 is None:
        손익계산서 = 재무제표['cis']
    if 손익계산서 is None:
        return None
    결과1 = 손익계산서.loc[:]
    return 결과1

# 4.2 재무상태표찾기 (원본 대괄호 [] 로직 100% 복원!)
def 재무상태표찾기():
    global 재무상태표, 결과2
    재무상태표 = 재무제표['bs']
    if 재무상태표 is None:
        return None
    결과2 = 재무상태표.loc[:]
    return 결과2

# 4.3 현금흐름표 (원본 대괄호 [] 로직 100% 복원!)
def 현금흐름표찾기():
    global 현금흐름표, 결과3
    현금흐름표 = 재무제표['cf']
    if 현금흐름표 is None:
        현금흐름표 = 재무제표['ccf']
    if 현금흐름표 is None:
        return None
    결과3 = 현금흐름표.loc[:]
    return 결과3

손익계산서찾기()
재무상태표찾기()
현금흐름표찾기()

# 5. 한국어 라벨과, 5년치 데이터열 추출 (원본 로직 그대로!)
def 데이터가공1():
    global df1
    df1 = 결과1.filter(regex=r'label_ko|\d{8}-\d{8}') if 결과1 is not None else None
    return df1

def 데이터가공2():
    global df2
    df2 = 결과2.filter(regex=r'label_ko|\d{8}') if 결과2 is not None else None
    return df2

def 데이터가공3():
    global df3
    df3 = 결과3.filter(regex=r'label_ko|\d{8}-\d{8}') if 결과3 is not None else None
    return df3

데이터가공1()
데이터가공2()
데이터가공3()

# 3.5 & 4. 재무제표 선택 (input -> st.tabs 로 웹 스타일로 깔끔하게 구성)
st.subheader(f"🏢 **{회사.corp_name}** 재무제표 분석")
tab1, tab2, tab3 = st.tabs(["📈 1. 손익계산서", "🏛️ 2. 재무상태표", "💸 3. 현금흐름표"])

# 6.1 손익계산서 뽑아서 표시하기 (원본 plt 그래프 그리기 로직 100% 그대로 유지)
with tab1:
    if df1 is None:
        st.warning("손익계산서, 포괄손익계산서 항목이 모두 없습니다.")
    else:
        all_rows = df1.iloc[:, 0].tolist()
        # 번호 입력(input) 대신 웹에서 마우스로 클릭할 수 있는 multiselect로 변경
        selected_items = st.multiselect(
            "📊 분석할 지표를 선택하세요 (여러 개 선택 가능):", 
            options=all_rows, 
            default=[all_rows[0]] if len(all_rows) > 0 else [],
            key="is_select"
        )
        
        if not selected_items:
            st.error("❌ 선택된 지표가 없습니다.")
        else:
            label_col_name = df1.columns[0]
            filtered_df = df1[df1[label_col_name].isin(selected_items)].copy()
            filtered_df = filtered_df.set_index(label_col_name)

            years_columns = ['20210101-20211231', '20220101-20221231', '20230101-20231231', '20240101-20241231', '20250101-20251231']
            valid_years = [col for col in years_columns if col in filtered_df.columns]
            plot_df = filtered_df[valid_years]

            # 🔥 [핵심] 원본의 유동적 스케일 및 조/억 단위 계산 로직 100% 그대로!
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

            fig, ax = plt.subplots(figsize=(11, 7))
            display_df = plot_df_scaled.T
            display_df.index = [col[:4] for col in valid_years]

            display_df.plot(marker='o', ax=ax, linewidth=2, markersize=6)
            ymin, ymax = ax.get_ylim()
            ax.set_ylim(ymin, ymax * 1.15)

            for i, column in enumerate(plot_df.index):
                orig_values = plot_df.loc[column].values           # 말풍선 표시용 원본 금액
                y_values = plot_df_scaled.loc[column].values       # 그래프 위치용 스케일 변환 금액
                for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
                    if np.isnan(orig_val):
                        continue
                    kor_text = 숫자줄이기(orig_val) # 원본 숫자줄이기 함수 호출!
                    offset = 12 if i % 2 == 0 else -18
                    ax.annotate(
                        kor_text, (x_idx, y_val),
                        textcoords="offset points", xytext=(0, offset),
                        ha='center', fontsize=9, fontweight='bold',
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7)
                    )
            ax.set_title(f'[{회사.corp_name}] 손익계산서 주요 지표 추이', fontsize=16, fontweight='bold', pad=15)
            ax.set_xlabel('연도 (Year)', fontsize=12)
            ax.set_ylabel(f'금액 (단위: {unit_str})', fontsize=12, fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()
            
            # plt.show() 대신 웹 페이지에 출력!
            st.pyplot(fig)
            st.dataframe(plot_df, use_container_width=True)

# 6.2 재무상태표 뽑아서 표시하기 (원본 로직 100% 유지)
with tab2:
    if df2 is None:
        st.warning("재무상태표 항목이 없습니다.")
    else:
        all_rows = df2.iloc[:, 0].tolist()
        selected_items = st.multiselect(
            "📊 분석할 지표를 선택하세요:", 
            options=all_rows, 
            default=[all_rows[0]] if len(all_rows) > 0 else [],
            key="bs_select"
        )
        if not selected_items:
            st.error("❌ 선택된 지표가 없습니다.")
        else:
            label_col_name = df2.columns[0]
            filtered_df = df2[df2[label_col_name].isin(selected_items)].copy()
            filtered_df = filtered_df.set_index(label_col_name)

            years_columns = ['20211231', '20221231', '20231231', '20241231', '20251231']
            valid_years = [col for col in years_columns if col in filtered_df.columns]
            plot_df = filtered_df[valid_years]

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

            fig, ax = plt.subplots(figsize=(11, 7))
            display_df = plot_df_scaled.T
            display_df.index = [col[:4] for col in valid_years]

            display_df.plot(marker='o', ax=ax, linewidth=2, markersize=6)
            ymin, ymax = ax.get_ylim()
            ax.set_ylim(ymin, ymax * 1.15)

            for i, column in enumerate(plot_df.index):
                orig_values = plot_df.loc[column].values
                y_values = plot_df_scaled.loc[column].values
                for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
                    if np.isnan(orig_val):
                        continue
                    kor_text = 숫자줄이기(orig_val)
                    offset = 12 if i % 2 == 0 else -18
                    ax.annotate(
                        kor_text, (x_idx, y_val),
                        textcoords="offset points", xytext=(0, offset),
                        ha='center', fontsize=9, fontweight='bold',
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7)
                    )
            ax.set_title(f'[{회사.corp_name}] 재무상태표 주요 지표 추이', fontsize=16, fontweight='bold', pad=15)
            ax.set_xlabel('연도 (Year)', fontsize=12)
            ax.set_ylabel(f'금액 (단위: {unit_str})', fontsize=12, fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()
            
            st.pyplot(fig)
            st.dataframe(plot_df, use_container_width=True)

# 6.3 현금흐름표 뽑아서 표시하기 (원본 로직 100% 유지)
with tab3:
    if df3 is None:
        st.warning("현금흐름표 항목이 없습니다.")
    else:
        all_rows = df3.iloc[:, 0].tolist()
        selected_items = st.multiselect(
            "📊 분석할 지표를 선택하세요:", 
            options=all_rows, 
            default=[all_rows[0]] if len(all_rows) > 0 else [],
            key="cf_select"
        )
        if not selected_items:
            st.error("❌ 선택된 지표가 없습니다.")
        else:
            label_col_name = df3.columns[0]
            filtered_df = df3[df3[label_col_name].isin(selected_items)].copy()
            filtered_df = filtered_df.set_index(label_col_name)

            years_columns = ['20210101-20211231', '20220101-20221231', '20230101-20231231', '20240101-20241231', '20250101-20251231']
            valid_years = [col for col in years_columns if col in filtered_df.columns]
            plot_df = filtered_df[valid_years]

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

            fig, ax = plt.subplots(figsize=(11, 7))
            display_df = plot_df_scaled.T
            display_df.index = [col[:4] for col in valid_years]

            display_df.plot(marker='o', ax=ax, linewidth=2, markersize=6)
            ymin, ymax = ax.get_ylim()
            ax.set_ylim(ymin, ymax * 1.15)

            for i, column in enumerate(plot_df.index):
                orig_values = plot_df.loc[column].values
                y_values = plot_df_scaled.loc[column].values
                for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
                    if np.isnan(orig_val):
                        continue
                    kor_text = 숫자줄이기(orig_val)
                    offset = 12 if i % 2 == 0 else -18
                    ax.annotate(
                        kor_text, (x_idx, y_val),
                        textcoords="offset points", xytext=(0, offset),
                        ha='center', fontsize=9, fontweight='bold',
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7)
                    )
            ax.set_title(f'[{회사.corp_name}] 현금흐름표 주요 지표 추이', fontsize=16, fontweight='bold', pad=15)
            ax.set_xlabel('연도 (Year)', fontsize=12)
            ax.set_ylabel(f'금액 (단위: {unit_str})', fontsize=12, fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()
            
            st.pyplot(fig)
            st.dataframe(plot_df, use_container_width=True)