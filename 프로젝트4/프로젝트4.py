import pandas as pd
import requests
import xml.etree.ElementTree as ET
import zipfile
import io
import time

# KODEX 반도체 ETF 구성 기업명 (검증 대상)
target_companies = [
    "SK하이닉스",
    "삼성전자",
    "한미반도체",
    "주성엔지니어링",
    "리노공업",
    "DB하이텍",
    "원익IPS",
    "피에스케이",
    "이오테크닉스",
    "심텍",
    "HPSP",
    "파두",
    "제주반도체",
    "유진테크",
    "하나마이크론",
    "ISC",
    "고영",
    "티씨케이",
    "두산테스나",
    "테크윙",
    "피에스케이홀딩스",
    "RFHIC",
    "코미코",
    "태성",
    "에스앤에스텍",
    "케이씨텍",
    "HD현대에너지솔루션",
    "하나머티리얼즈",
    "필옵틱스",
    "LX세미콘",
    "와이씨",
    "SFA반도체",
    "덕산네오룩스",
    "넥스틴",
    "가온칩스",
]

API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"

def get_kospi100():
    try:
        import FinanceDataReader as fdr
        print("[1단계] KOSPI 상위 100개 종목 조회 중...\n")
        df_kospi = fdr.StockListing('KOSPI')

        marcap_col = None
        for col in df_kospi.columns:
            if col.lower() in ['marcap', 'marketcap'] or '시가총액' in str(col):
                marcap_col = col
                break

        if marcap_col is None:
            print("경고: 시가총액 컬럼 미발견, KRX 조회로 재시도...")
            df_krx = fdr.StockListing('KRX')
            df_kospi = df_krx[df_krx['Market'] == 'KOSPI'].copy()
            for col in df_kospi.columns:
                if col.lower() in ['marcap', 'marketcap'] or '시가총액' in str(col):
                    marcap_col = col
                    break

        df_kospi[marcap_col] = pd.to_numeric(df_kospi[marcap_col], errors='coerce')
        df_sorted = df_kospi.sort_values(by=marcap_col, ascending=False)
        df_top100 = df_sorted.head(100).copy()

        code_col = 'Code' if 'Code' in df_top100.columns else df_top100.columns[0]
        name_col = 'Name' if 'Name' in df_top100.columns else df_top100.columns[1]

        df_top100['Code'] = df_top100[code_col].astype(str).str.zfill(6)
        df_top100['Name'] = df_top100[name_col]

        print(f"성공: KOSPI 상위 100개 종목 로드 완료\n")
        return df_top100[['Code', 'Name']]
    except Exception as e:
        print(f"오류: FinanceDataReader 로드 실패 - {e}\n")
        return None

def get_corp_code_map():
    try:
        print("[2단계] OpenDART 전체 기업 고유번호 조회 중...\n")
        url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={API_KEY}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"오류: HTTP {response.status_code}\n")
            return None

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_data = zf.read('CORPCODE.xml')

        root = ET.fromstring(xml_data)
        corp_map = {}  # {corp_name: corp_code}

        for list_node in root.findall('list'):
            corp_name = list_node.findtext('corp_name')
            corp_code = list_node.findtext('corp_code')
            if corp_name and corp_code:
                corp_map[corp_name.strip()] = corp_code.strip()

        print(f"성공: {len(corp_map)}개 기업 고유번호 로드 완료\n")
        return corp_map
    except Exception as e:
        print(f"오류: OpenDART 조회 실패 - {e}\n")
        return None

def test_dart_api(corp_code, corp_name):
    try:
        api_url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

        # 2023, 2024, 2025 연도 모두 시도
        for year in ['2025', '2024', '2023']:
            for fs_div in ['CFS', 'OFS']:
                params = {
                    'crtfc_key': API_KEY,
                    'corp_code': corp_code,
                    'bsns_year': year,
                    'reprt_code': '11011',
                    'fs_div': fs_div
                }

                res = requests.get(api_url, params=params, timeout=10)
                data = res.json()
                status = data.get('status')

                if status == '000' and 'list' in data and len(data['list']) > 0:
                    return "성공", len(data['list']), f"{fs_div}({year})"

        return "실패", 0, "23~25년 데이터 없음"
    except Exception as e:
        return "오류", 0, str(e)

def validate_companies():
    print("=" * 80)
    print("KODEX 반도체 ETF 구성 기업 - DART 추출 가능 검증 (기업명 직접 검색)")
    print("=" * 80)
    print(f"\n검증 대상: {len(target_companies)}개 기업\n")

    # 1단계: DART 전체 기업 고유번호 로드 (KOSPI 상관없이)
    corp_code_map = get_corp_code_map()
    if corp_code_map is None:
        print("[실패] DART 고유번호 조회 불가\n")
        return

    # 2단계: 각 종목별 검증
    print("[2단계] 각 종목별 DART 재무제표 추출 가능 검증\n")
    print(f"{'순번':<4} {'기업명':<25} {'DART고유번호':<15} {'재무제표':<20}")
    print("-" * 80)

    results = []
    found_count = 0
    api_count = 0

    for idx, comp_name in enumerate(target_companies, 1):
        corp_code = "없음"
        api_result = "검색 불가"

        # DART에서 기업명으로 검색
        if comp_name in corp_code_map:
            corp_code = corp_code_map[comp_name]
            found_count += 1

            # DART API 테스트
            status, rows, fs_type = test_dart_api(corp_code, comp_name)
            if status == "성공":
                api_result = f"O ({fs_type}: {rows}행)"
                api_count += 1
            else:
                api_result = f"X ({fs_type})"

            time.sleep(0.1)

        results.append({
            '순번': idx,
            '기업명': comp_name,
            'DART고유번호': corp_code,
            '재무제표': api_result
        })

        print(f"{idx:<4} {comp_name:<25} {corp_code:<15} {api_result:<20}")

    # 요약
    print("\n" + "=" * 80)
    print("검증 결과 요약")
    print("=" * 80)
    print(f"DART 등록:         {found_count}/{len(target_companies)} ({found_count/len(target_companies)*100:.1f}%)")
    print(f"재무제표 추출 가능: {api_count}/{len(target_companies)} ({api_count/len(target_companies)*100:.1f}%)")
    print("=" * 80)

    # CSV 저장
    df_result = pd.DataFrame(results)
    csv_path = r'C:\Users\willo\Desktop\코딩\프로젝트4\dart_validation_result.csv'
    df_result.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n[OK] 검증 결과 저장: {csv_path}\n")

if __name__ == "__main__":
    validate_companies()
