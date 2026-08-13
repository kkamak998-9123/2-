# -*- coding: utf-8 -*-
import pandas as pd

# 실패 데이터 로드
failed_df = pd.read_csv('kospi100_depreciation_notfound.csv', encoding='utf-8-sig')

# 중복 제거
failed_df = failed_df.drop_duplicates(subset=['corp_code'])

print("ANALYSIS OF 30 FAILED COMPANIES")
print("=" * 100)
print()

# 실패 원인 분류
failure_types = {
    'no_expense_by_nature_note': [],
    'no_xbrl': [],
    'note_found_but_no_depreciation_row': []
}

for idx, row in failed_df.iterrows():
    status = str(row['status'])
    corp_name = row['corp_name']

    if 'no_expense_by_nature_note' in status:
        failure_types['no_expense_by_nature_note'].append(corp_name)
    elif 'no_xbrl' in status:
        failure_types['no_xbrl'].append(corp_name)
    elif 'note_found_but_no_depreciation_row' in status:
        failure_types['note_found_but_no_depreciation_row'].append(corp_name)

print("FAILURE REASON CLASSIFICATION")
print("=" * 100)
print()

print("[1] No Expense-by-Nature Note in DART: {} companies".format(
    len(failure_types['no_expense_by_nature_note'])))
print("-" * 100)
for company in failure_types['no_expense_by_nature_note']:
    print("  - {}".format(company))

print()
print("[2] No XBRL Data (HTML fallback also failed): {} companies".format(
    len(failure_types['no_xbrl'])))
print("-" * 100)
for company in failure_types['no_xbrl']:
    print("  - {}".format(company))

print()
print("[3] Note Found but No Depreciation Row: {} companies".format(
    len(failure_types['note_found_but_no_depreciation_row'])))
print("-" * 100)
for company in failure_types['note_found_but_no_depreciation_row']:
    print("  - {}".format(company))

print()
print("=" * 100)
print("INDUSTRY ANALYSIS")
print("=" * 100)
print()

# 기업 분류
financial_companies = ['삼성생명', 'KB금융', '신한지주', '하나금융지주', '삼성화재',
                       '미래에셋증권', '우리금융지주', '기업은행', '한국금융지주',
                       'NH투자증권', '삼성증권', '삼성카드', 'BNK금융지주', '삼성에피스홀딩스']

tech_companies = ['NAVER', '카카오', '크래프톤', '카카오뱅크', '하이브', 'NC']

telecom_energy = ['KT&G', 'SK이노베이션', 'KT']

manufacturing = ['한화에어로스페이스', '삼성중공업']

insurance = ['DB손해보험']

all_failed = [company for sublist in failure_types.values() for company in sublist]

print("1. FINANCIAL INSTITUTIONS (금융회사)")
fin_count = sum(1 for c in all_failed if c in financial_companies)
fin_pct = fin_count/len(all_failed)*100
print("   Count: {}/{} = {:.1f}%".format(fin_count, len(all_failed), fin_pct))
for company in all_failed:
    if company in financial_companies:
        print("   - {}".format(company))

print()
print("2. TECH & SOFTWARE (IT/소프트웨어)")
tech_count = sum(1 for c in all_failed if c in tech_companies)
tech_pct = tech_count/len(all_failed)*100
print("   Count: {}/{} = {:.1f}%".format(tech_count, len(all_failed), tech_pct))
for company in all_failed:
    if company in tech_companies:
        print("   - {}".format(company))

print()
print("3. TELECOM & ENERGY (통신/에너지)")
telecom_count = sum(1 for c in all_failed if c in telecom_energy)
telecom_pct = telecom_count/len(all_failed)*100
print("   Count: {}/{} = {:.1f}%".format(telecom_count, len(all_failed), telecom_pct))
for company in all_failed:
    if company in telecom_energy:
        print("   - {}".format(company))

print()
print("4. MANUFACTURING (제조업)")
mfg_count = sum(1 for c in all_failed if c in manufacturing)
mfg_pct = mfg_count/len(all_failed)*100
print("   Count: {}/{} = {:.1f}%".format(mfg_count, len(all_failed), mfg_pct))
for company in all_failed:
    if company in manufacturing:
        print("   - {}".format(company))

print()
print("=" * 100)
print("KEY FINDINGS & INSIGHTS")
print("=" * 100)
print()

print("WHY FINANCIAL INSTITUTIONS (금융회사): {}".format(fin_count))
print("-" * 100)
print("""
1. 감가상각비가 주요 비용이 아님
   - 금융회사는 금리, 수수료 기반 사업
   - 감가상각비의 비중이 매우 작거나 거의 없음

2. 자산 구조의 차이
   - 금융자산(주식, 채권, 대출)에 투자
   - 물리적 고정자산(PPE)이 거의 없음
   - 따라서 감가상각비도 거의 없음

3. 공시 양식의 차이
   - 금융감독청 지정 공시 양식 사용
   - DART의 "성격별 비용분석" 노트가 없거나 다른 형태

예: 삼성생명, KB금융, 신한지주, 하나금융지주, 삼성화재 등 14개
""")

print()
print("WHY TECH/SOFTWARE (IT/소프트웨어): {}".format(tech_count))
print("-" * 100)
print("""
1. 무형자산 중심 사업
   - 소프트웨어, 알고리즘, 데이터에 투자
   - 물리적 자산이 상대적으로 적음

2. 감가상각비의 낮은 중요도
   - 성격별 비용분석에서 감가상각비 항목이 중요하지 않음
   - 노트에 감가상각비를 명시하지 않을 수 있음

3. 데이터센터 자산의 특수성
   - 물리적 서버/데이터센터 자산이 있지만
   - 연결재무제표 구조가 복잡해서 추출 어려움

예: NAVER, 카카오, 크래프톤, NC, 하이브 등 6개
""")

print()
print("WHY NO XBRL/DETAILED DATA: {}".format(len(failure_types['no_xbrl'])))
print("-" * 100)
print("""
1. DART에 상세 XBRL 정보 미공시
   - 모든 공시 회사가 XBRL을 상세하게 태그하지는 않음
   - 특히 소규모 기업이나 특수 산업의 경우

2. HTML 파싱 실패
   - 공시 양식이 비표준화
   - 테이블 구조가 복잡하거나 다양함

예: 한화에어로스페이스, 삼성화재, 메리츠금융지주 등 3개
""")

print()
print("WHY NOTE FOUND BUT NO DEPRECIATION ROW: {}".format(
    len(failure_types['note_found_but_no_depreciation_row'])))
print("-" * 100)
print("""
1. 감가상각비 항목이 따로 없음
   - 성격별 비용분석 노트는 있지만
   - 감가상각비를 "기타" 또는 다른 항목에 포함
   - 또는 감가상각비 자체가 매우 작아서 표시하지 않음

2. 노트 포맷의 특수성
   - 파싱 로직이 예상하지 못한 형태
   - 영어/한글 혼용 또는 특수 기호 사용

3. 비즈니스 특성
   - 리스 자산 중심 또는 무형자산 중심
   - 유형자산이 매우 적음

예: 삼성중공업, SK이노베이션, 카카오, 크래프톤, KT, 하이브 등 7개
""")

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)
print()
print("Total KOSPI100 companies: 100")
print("Depreciation extraction success: 70 (70%)")
print("Depreciation extraction failed: 30 (30%)")
print()
print("Failed breakdown:")
print("  - Financial institutions: {} ({:.1f}%)".format(fin_count, fin_count/30*100))
print("  - Tech/Software: {} ({:.1f}%)".format(tech_count, tech_count/30*100))
print("  - No XBRL/detailed data: {} ({:.1f}%)".format(
    len(failure_types['no_xbrl']), len(failure_types['no_xbrl'])/30*100))
print("  - Note format issues: {} ({:.1f}%)".format(
    len(failure_types['note_found_but_no_depreciation_row']),
    len(failure_types['note_found_but_no_depreciation_row'])/30*100))
