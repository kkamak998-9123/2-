import os
import sys
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import dart_fss as dart

# =========================================================
# 0. API 설정 및 한글 폰트 설정
# =========================================================
API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"
dart.set_api_key(api_key=API_KEY)

if os.name == 'nt':  # Windows인 경우
    plt.rc('font', family='Malgun Gothic')
else:  # Mac인 경우 (AppleGothic)
    plt.rc('font', family='AppleGothic')

# 그래프에서 마이너스(-) 기호가 깨지는 현상 방지
plt.rcParams['axes.unicode_minus'] = False

# =========================================================
# [NEW] 통계청 KSIC 연계표 기반 하이브리드 분류 매핑 로직
# =========================================================
excel_path = '2. 한국표준산업분류표(제11차).xlsx'
ksic_lookup_dict = {}

if os.path.exists(excel_path):
    print("⏳ 통계청 KSIC 마스터 엑셀 파일을 불러오는 중...")
    xls = pd.ExcelFile(excel_path)
    df_ksic = pd.read_excel(xls, sheet_name='11차개정한국표준산업분류', header=1)
    
    # 컬럼명 직관적으로 변경 및 상위 분류 빈칸 채우기 (Forward Fill)
    df_ksic.columns = ['대분류코드', '대분류명', '중분류코드', '중분류명', '소분류코드', '소분류명', '세분류코드', '세분류명', '세세분류코드', '세세분류명']
    df_ksic[['대분류코드', '대분류명', '중분류코드', '중분류명', '소분류코드', '소분류명', '세분류코드', '세분류명']] = df_ksic[['대분류코드', '대분류명', '중분류코드', '중분류명', '소분류코드', '소분류명', '세분류코드', '세분류명']].ffill()
    
    # [핵심] 제조업(C)이면 -> 중분류명 선택 / 제조업이 아니면 -> 대분류명 선택
    df_ksic['타겟_분류명'] = np.where(df_ksic['대분류코드'] == 'C', df_ksic['중분류명'], df_ksic['대분류명'])
    
    # 100% 매칭을 위한 문자열 표준화 함수 (점, 띄어쓰기, 특수문자 모두 제거)
    def clean_text(s):
        if pd.isna(s): return ""
        s = str(s)
        s = re.sub(r'[ㆍ·\s;,\.~/\(\)\-]', '', s)
        s = s.replace('나', '및')  # '차체나' -> '차체및' 표준화
        return s
        
    for idx, row in df_ksic.iterrows():
        target_val = row['타겟_분류명']
        for col in ['소분류명', '중분류명', '세분류명', '세세분류명']:
            cleaned_key = clean_text(row[col])
            if cleaned_key and cleaned_key not in ksic_lookup_dict:
                ksic_lookup_dict[cleaned_key] = target_val
    print("✅ 통계청 KSIC 업종 분류 사전 구축 완료!\n")
else:
    print(f"⚠️ [{excel_path}] 파일을 찾을 수 없습니다. 기본 업종 분류를 사용합니다.\n")
    def clean_text(s):
        return str(s) if pd.notna(s) else ""

def 엑셀기준_하이브리드_분류(dart_sector):
    if not dart_sector or pd.isna(dart_sector):
        return '기타 산업'
    cleaned_sector = clean_text(dart_sector)
    return ksic_lookup_dict.get(cleaned_sector, dart_sector)

# =========================================================
# 1. DART 회사 목록 다운로드
# =========================================================
print("⏳ DART 상장사 리스트 다운로드 중...")
모든회사목록 = dart.get_corp_list()

# =========================================================
# 2. 회사 이름 찾기
# =========================================================
def 회사이름찾기():
    이름입력 = input(f"회사 명 입력 : ").strip()
    회사후보 = 모든회사목록.find_by_corp_name(이름입력, exactly=False, market='YK')
    
    if 회사후보 is None or len(회사후보) == 0:
        print("❌ 회사를 찾을 수 없습니다. 다시 입력해 주세요.")
        return 회사이름찾기()
    elif len(회사후보) > 1:
        print(f"\n🔍 검색된 기업 {len(회사후보)}개. 정확한 사명 입력이 필요합니다:")
        for i in 회사후보:
            print(f" - {i}")
        두번째이름입력 = input(f"정확한 회사명 : ").strip()
        회사후보 = 모든회사목록.find_by_corp_name(두번째이름입력, exactly=True, market='YKNE')
        if 회사후보 is None or len(회사후보) == 0:
            print("❌ 정확한 회사를 찾지 못했습니다. 처음부터 다시 시도합니다.")
            return 회사이름찾기()
            
    global 회사
    회사 = 회사후보[0]
    print(f"\n--- [{회사.corp_name}] 데이터 선택 완료 ---")
    return 회사

# =========================================================
# 3. 개별 회사 재무제표 추출 (5년치 추이용)
# =========================================================
def 재무제표추출():
    global 재무제표
    print(f"\n⏳ [{회사.corp_name}] 재무제표 추출 중 (최근 5년치)...")
    재무제표 = dart.fs.extract(corp_code=회사.corp_code, bgn_de='20210101', end_de='20251231')
    return 재무제표

def 재무제표선택():
    print("\n" + "=" * 50)
    print("📈 확인하고 싶은 분석 메뉴를 선택하세요:")
    print("=" * 50)
    print("1. 손익계산서 (포괄손익계산서) 추이 📊")
    print("2. 재무상태표 추이 📊")
    print("3. 현금흐름표 추이 📊")
    print("4. 개별회사 재무제표 모두 보기 (1+2+3) 📑")
    print("5. [NEW] 동종 업계 타사 비교 및 순위 분석 🏢 (최강 추천!)")
    선택 = input("선택 (1-5): ").strip()
    return 선택

# =========================================================
# 4. 재무제표 표별 데이터 찾기 및 가공
# =========================================================
def 손익계산서찾기():
    global 손익계산서, 결과1
    손익계산서 = 재무제표['is'] if 재무제표['is'] is not None else 재무제표['cis']
    if 손익계산서 is None:
        print(f"❌ 손익계산서/포괄손익계산서 항목이 없습니다.")
        return None
    결과1 = 손익계산서.loc[:]
    return 결과1

def 재무상태표찾기():
    global 재무상태표, 결과2
    재무상태표 = 재무제표['bs']
    if 재무상태표 is None:
        print(f"❌ 재무상태표 항목이 없습니다.")
        return None
    결과2 = 재무상태표.loc[:]
    return 결과2

def 현금흐름표찾기():
    global 현금흐름표, 결과3
    현금흐름표 = 재무제표['cf'] if 재무제표['cf'] is not None else 재무제표['ccf']
    if 현금흐름표 is None:
        print(f"❌ 현금흐름표 항목이 없습니다.")
        return None
    결과3 = 현금흐름표.loc[:]
    return 결과3

def 데이터가공1():
    global df1
    df1 = 결과1.filter(regex=r'label_ko|\d{8}-\d{8}')
    return df1

def 데이터가공2():
    global df2
    df2 = 결과2.filter(regex=r'label_ko|\d{8}')
    return df2

def 데이터가공3():
    global df3
    df3 = 결과3.filter(regex=r'label_ko|\d{8}-\d{8}')
    return df3

# =========================================================
# 5. 숫자 변환 함수
# =========================================================
def 숫자줄이기(amount):
    """숫자가 너무 크면 '조', '억' 단위로 바꿔주는 함수 (소수점 2자리)"""
    amount = float(amount)
    if abs(amount) >= 1000000000000:
        return f"{amount/1000000000000:.2f}조"
    elif abs(amount) >= 100000000:
        return f"{amount/100000000:.2f}억"
    else:
        return f"{amount:,.2f}"

def 숫자줄이기2(amount):
    amount = float(amount) * 100.0
    if abs(amount) >= 1000000000000:
        return f"{amount/1000000000000:.2f}조"
    elif abs(amount) >= 100000000:
        return f"{amount/100000000:.2f}억"
    else:
        return f"{amount:,.2f}%"

# =========================================================
# 6. 개별 회사 시각화 그래프 함수 (1~3번)
# =========================================================
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
        print("❌ 잘못된 입력입니다."); return
    if not selected_items:
        print("❌ 선택된 지표가 없습니다."); return

    label_col_name = df1.columns[0]
    filtered_df = df1[df1[label_col_name].isin(selected_items)].copy().set_index(label_col_name)

    years_columns = ['20210101-20211231', '20220101-20221231', '20230101-20231231', '20240101-20241231', '20250101-20251231']
    valid_years = [col for col in years_columns if col in filtered_df.columns]
    plot_df = filtered_df[valid_years]

    max_val = np.nanmax(np.abs(plot_df.values))
    if np.isnan(max_val) or max_val == 0 or max_val >= 1e12:
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
    ymin, ymax = plt.ylim(); plt.ylim(ymin, ymax * 1.15)

    for i, column in enumerate(plot_df.index):
        orig_values = plot_df.loc[column].values
        y_values = plot_df_scaled.loc[column].values
        for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
            if np.isnan(orig_val): continue
            kor_text = 숫자줄이기(orig_val)
            offset = 12 if i % 2 == 0 else -18
            plt.annotate(kor_text, (x_idx, y_val), textcoords="offset points", xytext=(0, offset),
                         ha='center', fontsize=9, fontweight='bold',
                         bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7))
    plt.title(f'[{회사.corp_name}] 손익계산서 주요 지표 추이', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('연도 (Year)', fontsize=12)
    plt.ylabel(f'금액 (단위: {unit_str})', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout(); plt.show()

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
        print("❌ 잘못된 입력입니다."); return
    if not selected_items:
        print("❌ 선택된 지표가 없습니다."); return

    label_col_name = df2.columns[0]
    filtered_df = df2[df2[label_col_name].isin(selected_items)].copy().set_index(label_col_name)

    years_columns = ['20211231', '20221231', '20231231', '20241231', '20251231']
    valid_years = [col for col in years_columns if col in filtered_df.columns]
    plot_df = filtered_df[valid_years]

    max_val = np.nanmax(np.abs(plot_df.values))
    if np.isnan(max_val) or max_val == 0 or max_val >= 1e12:
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
    ymin, ymax = plt.ylim(); plt.ylim(ymin, ymax * 1.15)

    for i, column in enumerate(plot_df.index):
        orig_values = plot_df.loc[column].values
        y_values = plot_df_scaled.loc[column].values
        for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
            if np.isnan(orig_val): continue
            kor_text = 숫자줄이기(orig_val)
            offset = 12 if i % 2 == 0 else -18
            plt.annotate(kor_text, (x_idx, y_val), textcoords="offset points", xytext=(0, offset),
                         ha='center', fontsize=9, fontweight='bold',
                         bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7))
    plt.title(f'[{회사.corp_name}] 재무상태표 주요 지표 추이', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('연도 (Year)', fontsize=12)
    plt.ylabel(f'금액 (단위: {unit_str})', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout(); plt.show()

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
        print("❌ 잘못된 입력입니다."); return
    if not selected_items:
        print("❌ 선택된 지표가 없습니다."); return

    label_col_name = df3.columns[0]
    filtered_df = df3[df3[label_col_name].isin(selected_items)].copy().set_index(label_col_name)

    years_columns = ['20210101-20211231', '20220101-20221231', '20230101-20231231', '20240101-20241231', '20250101-20251231']
    valid_years = [col for col in years_columns if col in filtered_df.columns]
    plot_df = filtered_df[valid_years]

    max_val = np.nanmax(np.abs(plot_df.values))
    if np.isnan(max_val) or max_val == 0 or max_val >= 1e12:
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
    ymin, ymax = plt.ylim(); plt.ylim(ymin, ymax * 1.15)

    for i, column in enumerate(plot_df.index):
        orig_values = plot_df.loc[column].values
        y_values = plot_df_scaled.loc[column].values
        for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
            if np.isnan(orig_val): continue
            kor_text = 숫자줄이기(orig_val)
            offset = 12 if i % 2 == 0 else -18
            plt.annotate(kor_text, (x_idx, y_val), textcoords="offset points", xytext=(0, offset),
                         ha='center', fontsize=9, fontweight='bold',
                         bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7))
    plt.title(f'[{회사.corp_name}] 현금흐름표 주요 지표 추이', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('연도 (Year)', fontsize=12)
    plt.ylabel(f'금액 (단위: {unit_str})', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout(); plt.show()

# =========================================================
# 7. [NEW] 동종업계 타사 비교 분석 및 순위 산출 함수 (5번 메뉴)
# =========================================================

# 🚨 [핵심] 계정_가져오기 함수를 반드시 호출(동종업계_비교분석_출력) 함수보다 먼저 정의!
def 계정_가져오기(df, keywords):
    for col in df.columns:
        if any(kw in str(col) for kw in keywords):
            return df[col]
    return pd.Series(np.nan, index=df.index)

def 동종업계_데이터_수집(기준회사):
    print(f"\n🔍 [{기준회사.corp_name}]의 동종 업계 기업 탐색 중...")
    
    # 1. 상장사 필터링 (stock_code가 아니라 corp_code 필수 확인!)
    df_corps = pd.DataFrame([c.to_dict() for c in 모든회사목록.corps]).dropna(subset=['sector', 'corp_code'])
    df_corps['macro_sector'] = df_corps['sector'].apply(엑셀기준_하이브리드_분류)
    
    # 2. 기준 회사의 대분류 찾기 (corp_code 매칭)
    my_sector = df_corps[df_corps['corp_code'] == 기준회사.corp_code]['macro_sector'].values
    if len(my_sector) == 0:
        print("❌ 기준 회사의 업종 정보를 찾을 수 없습니다."); return None, None
    
    target_sector_name = my_sector[0]
    print(f"📁 매칭된 통계청 분류 업종: [{target_sector_name}]")
    
    # 3. 동종업계 기업 고유번호(corp_code) 추출 (API 속도 고려 최대 30개 제한)
    peer_corps = df_corps[df_corps['macro_sector'] == target_sector_name]
    peer_codes = peer_corps['corp_code'].tolist()[:30]
    
    if 기준회사.corp_code not in peer_codes:
        peer_codes.append(기준회사.corp_code)
        
    print(f"📊 비교 분석 대상 기업 수: 총 {len(peer_codes)}개 사 (최고속 API 조회 중...)")
    
    # 🚨 [핵심!] 파이썬 리스트를 쉼표(,)로 연결된 하나의 문자열로 변환 (예: '00123456,00234567')
    corp_codes_str = ",".join([str(code) for code in peer_codes if pd.notna(code)])
    
    fin_list = []
    try:
        # 최근 결산연도(2025) 사업보고서(11011) 다중 조회
        res = dart.api.finance.fnltt_multi_acnt(corp_code=corp_codes_str, bsns_year='2025', reprt_code='11011')
        if res and 'list' in res:
            fin_list.extend(res['list'])
    except Exception as e:
        print(f"⚠️ 2025년 데이터 조회 실패 (2024년으로 대체 시도): {e}")
        
    # 2025년 데이터가 없거나 5개 미만일 경우 2024년 데이터 백업 조회
    if not fin_list or len(fin_list) < 5:
        try:
            res = dart.api.finance.fnltt_multi_acnt(corp_code=corp_codes_str, bsns_year='2024', reprt_code='11011')
            if res and 'list' in res:
                fin_list.extend(res['list'])
        except Exception as e:
            print(f"⚠️ 2024년 데이터 조회 실패: {e}")
            
    df_fin = pd.DataFrame(fin_list)
    if df_fin.empty:
        print("❌ 동종업계 재무 데이터를 가져오지 못했습니다."); return target_sector_name, None
        
    # 4. 연결재무제표(CFS) 우선, 없으면 별도(OFS) 적용
    df_fin = df_fin[df_fin['fs_div'].isin(['CFS', 'OFS'])].sort_values('fs_div').drop_duplicates(subset=['corp_code', 'account_nm'])
    df_fin['thstrm_amount'] = pd.to_numeric(df_fin['thstrm_amount'].str.replace(',', ''), errors='coerce')
    
    # 5. 피벗 테이블 생성 후 종목명(corp_name) 병합
    pivot_df = df_fin.pivot_table(index='corp_code', columns='account_nm', values='thstrm_amount', aggfunc='first')
    pivot_df = pivot_df.merge(df_corps[['corp_code', 'corp_name']], on='corp_code', how='inner').set_index('corp_name')
    
    return target_sector_name, pivot_df

def 업계비교_시각화(df, my_name, sector_name):
    target_col = '영업이익률(%)'
    if target_col not in df.columns or df[target_col].dropna().empty:
        return
    valid_df = df[target_col].dropna().sort_values(ascending=False)
    
    top_companies = valid_df.head(5)
    if my_name not in top_companies.index:
        plot_series = pd.concat([top_companies, pd.Series({my_name: valid_df.loc[my_name]})])
    else:
        plot_series = top_companies.copy()
    plot_series['업계 평균'] = valid_df.mean()
    
    plt.figure(figsize=(10, 6))
    colors = ['crimson' if name == my_name else ('darkorange' if name == '업계 평균' else 'gainsboro') for name in plot_series.index]
    bars = plot_series.plot(kind='bar', color=colors, edgecolor='gray', width=0.6)
    
    plt.title(f'[{my_name}] 동종업계({sector_name}) {target_col} 순위 비교', fontsize=15, fontweight='bold', pad=15)
    plt.ylabel('영업이익률 (%)', fontsize=12)
    plt.xticks(rotation=30, ha='right', fontsize=11, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    for bar in bars.patches:
        height = bar.get_height()
        if pd.isna(height): continue
        plt.annotate(f'{height:.1f}%', (bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 5 if height >= 0 else -15), textcoords="offset points",
                     ha='center', va='bottom' if height >= 0 else 'top', fontsize=10, fontweight='bold')
    ymin, ymax = plt.ylim()
    plt.ylim(ymin * 1.1 if ymin < 0 else 0, ymax * 1.15)
    plt.tight_layout(); plt.show()

def 동종업계_비교분석_출력(기준회사, target_sector_name, pivot_df):
    if pivot_df is None or pivot_df.empty:
        print("❌ 비교 분석할 재무 데이터가 부족합니다."); return

    자산총계 = 계정_가져오기(pivot_df, ['자산총계'])
    부채총계 = 계정_가져오기(pivot_df, ['부채총계'])
    자본총계 = 계정_가져오기(pivot_df, ['자본총계'])
    매출액 = 계정_가져오기(pivot_df, ['매출액', '수익(매출액)', '영업수익'])
    영업이익 = 계정_가져오기(pivot_df, ['영업이익', '영업이익(손실)'])
    당기순이익 = 계정_가져오기(pivot_df, ['당기순이익', '당기순이익(손실)', '연결당기순이익'])
    연구개발비 = 계정_가져오기(pivot_df, ['연구개발비', '경상연구개발비'])

    analysis_df = pd.DataFrame(index=pivot_df.index)
    analysis_df['영업이익률(%)'] = (영업이익 / 매출액) * 100
    analysis_df['순이익률(%)'] = (당기순이익 / 매출액) * 100
    analysis_df['부채비율(%)'] = (부채총계 / 자본총계) * 100
    analysis_df['ROE(%)'] = (당기순이익 / 자본총계) * 100
    analysis_df['자산 내 자기자본비중(%)'] = (자본총계 / 자산총계) * 100
    analysis_df['매출 대비 R&D비중(%)'] = (연구개발비 / 매출액) * 100

    analysis_df = analysis_df.replace([np.inf, -np.inf], np.nan).dropna(how='all')
    
    print("\n" + "="*68)
    print(f"🏢 [{기준회사.corp_name}] vs 동종업계 ([{target_sector_name}] {len(analysis_df)}개사) 분석 결과")
    print("="*68)
    
    my_name = 기준회사.corp_name
    if my_name not in analysis_df.index:
        matched = [name for name in analysis_df.index if my_name in name]
        my_name = matched[0] if matched else None
        
    if not my_name:
        print("❌ 업계 데이터 내에서 해당 회사의 재무치를 추출하지 못했습니다."); return

    for col in analysis_df.columns:
        valid_series = analysis_df[col].dropna()
        if valid_series.empty or my_name not in valid_series.index: continue
            
        my_val = valid_series.loc[my_name]
        ind_mean = valid_series.mean()
        ind_median = valid_series.median()
        
        ascending_flag = True if '부채' in col else False
        rank = valid_series.rank(ascending=ascending_flag, method='min').loc[my_name]
        total_count = len(valid_series)
        percentile = (rank / total_count) * 100
        
        print(f"📌 {col}")
        print(f"   ▶ {my_name}: {my_val:6.2f}%  |  업계 평균: {ind_mean:6.2f}%  |  중앙값: {ind_median:6.2f}%")
        print(f"   ▶ 업계 내 순위: {int(rank)}위 / {total_count}개 사 (상위 {percentile:.1f}%)\n")

    # 비교 바 차트 출력
    업계비교_시각화(analysis_df, my_name, target_sector_name)

# =========================================================
# 8. 메인 프로그램 실행 로직
# =========================================================
def 프로그램_실행():
    print("=" * 55)
    print("📊 DART 재무제표 인터랙티브 시각화 & 동종업계 분석기")
    print("=" * 55)

    # 1단계: 회사 검색 및 지정
    회사이름찾기()

    # 2단계: 분석 메뉴 선택
    선택 = 재무제표선택()
    
    # [5번 메뉴] 동종업계 타사 비교 분석 실행
    if 선택 == '5':
        sector_name, peer_df = 동종업계_데이터_수집(회사)
        동종업계_비교분석_출력(회사, sector_name, peer_df)
        print("\n✅ 동종 업계 비교 분석이 완료되었습니다!")
        return

    # [1~4번 메뉴] 개별회사 5년치 추이 분석 실행
    재무제표추출()
    print("✅ 재무제표 추출 완료! 데이터 파싱을 시작합니다...")
    
    손익계산서찾기()
    재무상태표찾기()
    현금흐름표찾기()

    데이터가공1()
    데이터가공2()
    데이터가공3()
    print("✅ 데이터 가공 완료!\n")
    
    if 선택 in ['1', '4']:
        print(f"\n📊 손익계산서 분석 시작...")
        손익계산서_그래프()
    if 선택 in ['2', '4']:
        print(f"\n📊 재무상태표 분석 시작...")
        재무상태표_그래프()
    if 선택 in ['3', '4']:
        print(f"\n📊 현금흐름표 분석 시작...")
        현금흐름표_그래프()
    
    print("\n✅ 모든 분석이 완료되었습니다!")

# ==========================================
# 단일 실행 명령어
# ==========================================
if __name__ == "__main__":
    프로그램_실행()