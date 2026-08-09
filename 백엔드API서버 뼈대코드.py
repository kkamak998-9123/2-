from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import dart_fss as dart
import pandas as pd
import numpy as np

# 1. FastAPI 앱 생성
app = FastAPI(title="DART 재무제표 API 서버")

# 2. CORS 설정 (Cloudflare Pages 웹사이트에서 오는 요청 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실무에서는 ["https://내홈페이지.pages.dev"] 로 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. DART API 키 설정 및 회사 목록 초기 로드
API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"  # 본인 API 키
dart.set_api_key(api_key=API_KEY)

print("⏳ DART 회사 목록 다운로드 중... (서버 켜질 때 1번만 실행됨)")
모든회사목록 = dart.get_corp_list()
print("✅ 회사 목록 준비 완료!")

# 4. 숫자 줄이기 함수 (웹 툴팁 표시용)
def 숫자줄이기(amount):
    if amount is None or np.isnan(amount):
        return "-"
    val = float(amount)
    if abs(val) >= 1000000000000:
        return f"{val/1000000000000:.2f}조"
    elif abs(val) >= 100000000:
        return f"{val/100000000:.2f}억"
    else:
        return f"{val:,.0f}원"

# 5. [핵심 엔드포인트] 웹에서 회사명을 보내면 JSON 데이터를 반환하는 API
@app.get("/api/finance")
def get_finance_data(name: str = Query(..., description="회사명 (예: 삼성전자)")):
    # 회사 검색
    회사후보 = 모든회사목록.find_by_corp_name(name, exactly=False, market='YK')
    if not 회사후보 or len(회사후보) == 0:
        raise HTTPException(status_code=404, detail="회사를 찾을 수 없습니다.")
    
    회사 = 회사후보[0]  # 첫 번째 검색 결과 사용
    
    try:
        # 5년치 재무제표 추출
        재무제표 = dart.fs.extract(corp_code=회사.corp_code, bgn_de='20210101', end_de='20251231')
    except Exception as e:
        raise HTTPException(status_code=500, detail="DART 데이터 추출 중 오류 발생")

    # 웹으로 전송할 최종 규격화 데이터 구조
    result_json = {
        "corp_name": 회사.corp_name,
        "stock_code": 회사.stock_code,
        "years": ['2021', '2022', '2023', '2024', '2025'],
        "is": {},  # 손익계산서
        "bs": {},  # 재무상태표
        "cf": {}   # 현금흐름표
    }

    # 손익계산서 가공 (원본 [ ] 대괄호 문법 사용)
    is_data = 재무제표['is'] if 재무제표['is'] is not None else 재무제표['cis']
    if is_data is not None:
        df_is = is_data.loc[:].filter(regex=r'label_ko|\d{8}-\d{8}')
        label_col = df_is.columns[0]
        years_cols = [col for col in df_is.columns if col != label_col][-5:] # 최근 5개년
        
        for _, row in df_is.iterrows():
            acc_name = str(row[label_col]).strip()
            # JSON은 NaN(결측치)을 인식 못 하므로 None으로 변환
            vals = [None if np.isnan(v) else float(v) for v in row[years_cols].values]
            result_json["is"][acc_name] = vals

    # (참고) 재무상태표와 현금흐름표도 동일한 로직으로 result_json["bs"], ["cf"]에 담아줍니다.
    
    return result_json

# 서버 실행을 위한 메인 코드
if __name__ == "__main__":
    import uvicorn
    # 노트북 터미널에서 8000번 포트로 API 서버 구동
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)