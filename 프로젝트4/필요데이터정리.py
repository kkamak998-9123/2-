import pandas as pd

# 현재 파일 로드
current_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
df = pd.read_csv(current_file)

print("=" * 80)
print("필요데이터 정리")
print("=" * 80)

print(f"\n[현재 파일 현황]")
print(f"  총 행: {len(df)}행")

# 계정과목별 분포
print(f"\n[계정과목별]")
for account in sorted(df['account_nm'].unique()):
    count = len(df[df['account_nm'] == account])
    print(f"  {account:<25} {count:>3}행")

# 영업활동현금흐름만 추출
operating_only = df[df['account_nm'] == '영업활동현금흐름'].copy()
invest_only = df[df['account_nm'] == '투자활동현금흐름'].copy()

print(f"\n[분리 결과]")
print(f"  영업활동현금흐름: {len(operating_only)}행")
print(f"  투자활동현금흐름: {len(invest_only)}행")

# 정렬 및 저장
result_df = pd.concat([operating_only, invest_only], ignore_index=True)
result_df = result_df.sort_values(by=['corp_name', 'bsns_year', 'account_nm'],
                                  ascending=[True, False, True])
result_df = result_df.reset_index(drop=True)

# 저장
output_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv'
result_df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n[저장 완료]")
print(f"  파일: {output_file}")
print(f"  총 {len(result_df)}행 × {len(result_df.columns)}컬럼")
print("=" * 80)
