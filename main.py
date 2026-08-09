from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import dart_fss as dart
import pandas as pd
import numpy as np

app = FastAPI(title="DART 재무제표 API 서버")

# 🔥 [수정 1] allow_origins=["*"]일 때는 allow_credentials=False로 해야 브라우저가 차단하지 않습니다!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # True -> False로 변경
    allow_methods=["*"],
    allow_headers=["*"],
)

# [본인의 DART API 키]
API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"
dart.set_api_key(api_key=API_KEY)

print("⏳ DART 회사 목록 다운로드 중... (서버 켜질 때 1번만 진행됨)")
모든회사목록 = dart.get_corp_list()
print("✅ 회사 목록 준비 완료!")

# 🔥 [수정 2] index.html이 서버가 켜져 있는지 확인할 수 있는 전용 안심 주소 추가!
@app.get("/")
def health_check():
    return {"status": "online", "message": "DART API 서버가 정상 작동 중입니다."}

def parse_statement(fs_data):
    result_dict = {}
    if fs_data is None:
        return result_dict
    
    df = fs_data.loc[:].filter(regex=r'label_ko|\d{8}')
    if df.empty or len(df.columns) < 2:
        return result_dict
        
    label_col = df.columns[0]
    years_cols = [col for col in df.columns if col != label_col][-5:]
    
    for _, row in df.iterrows():
        acc_name = str(row[label_col]).strip()
        vals = []
        for col in years_cols:
            val = row[col]
            if pd.isna(val) or (isinstance(val, (int, float, np.number)) and np.isnan(val)):
                vals.append(None)
            else:
                try:
                    vals.append(float(val))
                except (ValueError, TypeError):
                    vals.append(None)
        result_dict[acc_name] = vals
    return result_dict

@app.get("/api/finance")
def get_finance_data(name: str = Query(..., description="회사명 입력 (예: 삼성 또는 삼성전자)")):
    print(f"\n🔍 [입력값: '{name}'] 회사 검색 시작...")
    
    회사후보 = 모든회사목록.find_by_corp_name(name, exactly=True, market='YK')
    
    if not 회사후보 or len(회사후보) == 0:
        회사후보 = 모든회사목록.find_by_corp_name(name, exactly=False, market='YK')
    
    if not 회사후보 or len(회사후보) == 0:
        print("❌ 회사를 찾을 수 없습니다.")
        return {
            "status": "not_found",
            "message": f"'{name}' 회사를 찾을 수 없습니다. 다시 입력해 주세요.",
            "candidates": []
        }
        
    elif len(회사후보) > 1:
        print(f"⚠️ 검색된 기업 {len(회사후보)}개. 정확한 사명 입력 필요!")
        후보목록 = [{"corp_name": c.corp_name, "stock_code": c.stock_code} for c in 회사후보[:50]]
        return {
            "status": "multiple_candidates",
            "message": f"검색된 기업 {len(회사후보)}개. 정확한 사명 입력 필요합니다. 이 중 선택해주세요.",
            "candidates": 후보목록
        }

    회사 = 회사후보[0]
    print(f"--- [{회사.corp_name}] 데이터 추출 시작 ---")

    try:
        재무제표 = dart.fs.extract(corp_code=회사.corp_code, bgn_de='20210101', end_de='20261231')
    except Exception as e:
        raise HTTPException(status_code=500, detail="DART 서버에서 데이터를 가져오는 중 오류 발생")

    is_data = 재무제표['is'] if 재무제표['is'] is not None else 재무제표['cis']
    bs_data = 재무제표['bs']
    cf_data = 재무제표['cf'] if 재무제표['cf'] is not None else 재무제표['ccf']

    result_json = {
        "status": "success",
        "corp_name": 회사.corp_name,
        "stock_code": 회사.stock_code,
        "is": parse_statement(is_data),
        "bs": parse_statement(bs_data),
        "cf": parse_statement(cf_data)
    }
    
    print(f"✅ [{회사.corp_name}] 재무제표 추출 및 5년치 변환 완료!")
    return result_json

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)