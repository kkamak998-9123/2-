# build_full_db.py : 2,500여개 상장사 전 과목 3~5년치 수집기 (자동 이어받기 기능 탑재)
import time
import pandas as pd
import numpy as np
import dart_fss as dart
import os
import re
import sqlite3

# 1. API 설정
API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"
dart.set_api_key(api_key=API_KEY)

# 2. 통계청 KSIC 엑셀 분류 사전 준비
excel_path = '2. 한국표준산업분류표(제11차).xlsx'
ksic_lookup_dict = {}
if os.path.exists(excel_path):
    xls = pd.ExcelFile(excel_path)
    df_ksic = pd.read_excel(xls, sheet_name='11차개정한국표준산업분류', header=1)
    df_ksic.columns = ['대분류코드', '대분류명', '중분류코드', '중분류명', '소분류코드', '소분류명', '세분류코드', '세분류명', '세세분류코드', '세세분류명']
    df_ksic[['대분류코드', '대분류명', '중분류코드', '중분류명', '소분류코드', '소분류명', '세분류코드', '세분류명']] = df_ksic[['대분류코드', '대분류명', '중분류코드', '중분류명', '소분류코드', '소분류명', '세분류코드', '세분류명']].ffill()
    df_ksic['타겟_분류명'] = np.where(df_ksic['대분류코드'] == 'C', df_ksic['중분류명'], df_ksic['대분류명'])
    
    def clean_text(s):
        if pd.isna(s): return ""
        return re.sub(r'[ㆍ·\s;,\.~/\(\)\-]', '', str(s)).replace('나', '및')
        
    for idx, row in df_ksic.iterrows():
        target_val = row['타겟_분류명']
        for col in ['소분류명', '중분류명', '세분류명', '세세분류명']:
            cleaned_key = clean_text(row[col])
            if cleaned_key and cleaned_key not in ksic_lookup_dict:
                ksic_lookup_dict[cleaned_key] = target_val

def 엑셀기준_하이브리드_분류(dart_sector):
    if not dart_sector or pd.isna(dart_sector): return '기타 산업'
    cleaned = re.sub(r'[ㆍ·\s;,\.~/\(\)\-]', '', str(dart_sector)).replace('나', '및')
    return ksic_lookup_dict.get(cleaned, dart_sector)

# 3. 자동 저장 및 이어받기를 위한 SQLite DB 연결
db_filename = "master_full_fs.db"
conn = sqlite3.connect(db_filename)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS financials (
    corp_code TEXT, corp_name TEXT, stock_code TEXT, macro_sector TEXT,
    fs_type TEXT, account_nm TEXT, period TEXT, bsns_year INTEGER, amount REAL
)
""")
conn.commit()

# 현재 DB에 이미 저장 완료된 기업 목록 확인 (이어받기 핵심!)
existing_df = pd.read_sql("SELECT DISTINCT corp_code FROM financials", conn)
completed_codes = set(existing_df['corp_code'].tolist())
print(f"📌 현재 DB에 이미 저장 완료된 기업 수: {len(completed_codes)}개 사")

# 4. 상장사(KOSPI/KOSDAQ) 필터링
print("⏳ DART 상장 기업 목록 불러오는 중...")
corp_list = dart.get_corp_list()
corps_data = []
for c in corp_list.corps:
    d = c.to_dict()
    if d.get('stock_code') and d.get('sector') and d.get('corp_cls') in ['Y', 'K']:
        d['macro_sector'] = 엑셀기준_하이브리드_분류(d.get('sector'))
        corps_data.append(d)

total_corps = len(corps_data)
print(f"🏢 수집 목표 상장기업: 총 {total_corps:,}개 사")

# 테이블 데이터를 표준 규격으로 가공하는 함수
def parse_table(table_df, fs_type, c_info):
    if table_df is None or table_df.empty: return []
    filtered = table_df.filter(regex=r'label_ko|\d{8}-\d{8}|\d{8}')
    if filtered.empty or len(filtered.columns) < 2: return []
    
    label_col = filtered.columns[0]
    period_cols = filtered.columns[1:]
    rows = []
    
    for idx, row in filtered.iterrows():
        acc_nm = str(row[label_col]).strip()
        if not acc_nm or pd.isna(acc_nm) or acc_nm == 'nan': continue
        
        for p_col in period_cols:
            val = row[p_col]
            if pd.isna(val) or val == '': continue
            years_found = re.findall(r'(20\d{2})', str(p_col))
            if not years_found: continue
            bsns_year = int(max(years_found))
            
            try:
                val_num = float(str(val).replace(',', ''))
            except: continue
                
            rows.append({
                'corp_code': c_info['corp_code'], 'corp_name': c_info['corp_name'],
                'stock_code': c_info['stock_code'], 'macro_sector': c_info['macro_sector'],
                'fs_type': fs_type, 'account_nm': acc_nm,
                'period': str(p_col), 'bsns_year': bsns_year, 'amount': val_num
            })
    return rows

# 5. 전 과목 1시간 반 수집 루프 시작!
print("\n🚀 전 과목 재무제표 수집 시작! (중간에 멈춰도 언제든 다시 켜면 이어서 작업합니다)")
for idx, corp in enumerate(corps_data, 1):
    c_code = corp['corp_code']
    if c_code in completed_codes:
        continue  # 이미 다운받은 기업은 0초 만에 패스!
        
    print(f"[{idx}/{total_corps}] {corp['corp_name']} ({c_code}) 전체 재무제표 다운로드 중...")
    try:
        # 최근 3개년 (원하시면 bgn_de를 '20210101'로 5년치로 변경 가능)
        fs = dart.fs.extract(corp_code=c_code, bgn_de='20230101', end_de='20251231')
        
        comp_rows = []
        comp_rows.extend(parse_table(fs['is'] if fs['is'] is not None else fs['cis'], 'IS', corp))
        comp_rows.extend(parse_table(fs['bs'], 'BS', corp))
        comp_rows.extend(parse_table(fs['cf'] if fs['cf'] is not None else fs['ccf'], 'CF', corp))
        
        if comp_rows:
            df_comp = pd.DataFrame(comp_rows)
            df_comp.to_sql('financials', conn, if_exists='append', index=False)
            conn.commit()
            completed_codes.add(c_code)
        time.sleep(0.5)  # DART 서버 보호 및 제한 회피
    except Exception as e:
        print(f"⚠️ {corp['corp_name']} 다운로드 실패 (건너뜀): {e}")

# 6. 최종 CSV 마스터 파일로 내보내기
print("\n⏳ 모든 기업 수집 완료! 웹 배포용 단일 CSV 파일로 내보내는 중...")
df_all = pd.read_sql("SELECT * FROM financials", conn)
output_csv = "master_full_fs.csv"
df_all.to_csv(output_csv, index=False, encoding='utf-8-sig')
print(f"🎉 대성공! 총 {len(df_all):,}줄의 완벽한 전 과목 재무 데이터가 [{output_csv}] 로 생성되었습니다!")