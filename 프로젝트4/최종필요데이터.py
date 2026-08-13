import pandas as pd

# 파일 로드
main = pd.read_csv(r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv')
invest = pd.read_csv(r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_투자활동현금흐름.csv')

print("=" * 80)
print("최종 필요데이터 재구성")
print("=" * 80)

print(f"\n[현황]")
print(f"  메인 파일: {len(main)}행")
print(f"  투자 파일: {len(invest)}행")

# 메인 파일에서 영업활동만 추출
operating = main[main['account_nm'] == '영업활동현금흐름'].copy()
print(f"\n[영업활동현금흐름 추출]")
print(f"  {len(operating)}행")

# 새로 병합
result = pd.concat([operating, invest], ignore_index=True)
result = result.sort_values(by=['corp_name', 'bsns_year', 'account_nm'],
                            ascending=[True, False, True])
result = result.reset_index(drop=True)

print(f"\n[병합 결과]")
print(f"  총 행: {len(result)}행")

# 계정과목별
for account in sorted(result['account_nm'].unique()):
    count = len(result[result['account_nm'] == account])
    print(f"  {account:<25} {count:>3}행")

# 저장
output_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
result.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n[완료]")
print(f"  저장: {output_file}")
print(f"  총 {len(result)}행 × {len(result.columns)}컬럼")
print("=" * 80)
