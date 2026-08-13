import pandas as pd

# 원본 영업활동현금흐름 로드 (이미 정규화된 파일)
operating_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_영업활동현금흐름.csv'
operating_df = pd.read_csv(operating_file)

# 투자활동현금흐름 로드 (중복 제거된 파일)
invest_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_투자활동현금흐름.csv'
invest_df = pd.read_csv(invest_file)

print("=" * 80)
print("필요데이터 재구성")
print("=" * 80)

print(f"\n[각 파일 현황]")
print(f"  영업활동현금흐름: {len(operating_df)}행")
print(f"  투자활동현금흐름: {len(invest_df)}행")

# 합병
result_df = pd.concat([operating_df, invest_df], ignore_index=True)
result_df = result_df.sort_values(by=['corp_name', 'bsns_year', 'account_nm'],
                                  ascending=[True, False, True])
result_df = result_df.reset_index(drop=True)

print(f"\n[병합 결과]")
print(f"  합계: {len(result_df)}행 × {len(result_df.columns)}컬럼")

# 계정과목별 분포
print(f"\n[계정과목별 분포]")
print("-" * 80)
for account in sorted(result_df['account_nm'].unique()):
    count = len(result_df[result_df['account_nm'] == account])
    print(f"  {account:<25} {count:>3}행")

# 저장
output_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
result_df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n[완료]")
print(f"  저장: {output_file}")
print(f"  총 {len(result_df)}행")
print("=" * 80)
