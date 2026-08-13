import pandas as pd

# 투자활동현금흐름 파일 로드
invest_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_투자활동현금흐름.csv'
df = pd.read_csv(invest_file)

print("=" * 80)
print("투자활동현금흐름 중복 행 분석")
print("=" * 80)

# 기업별 행 수
company_counts = df.groupby('corp_name').size().sort_values(ascending=False)

print(f"\n[기업별 행 수]")
print("-" * 80)

duplicates = []
for company, count in company_counts.items():
    status = "중복있음" if count > 3 else "정상" if count == 3 else "부족"
    if count != 3:
        duplicates.append((company, count))
        print(f"{company:<25} {count}행  [!]  {status}")
    else:
        print(f"{company:<25} {count}행")

# 중복된 기업 상세 분석
if duplicates:
    print(f"\n[중복된 기업 상세]")
    print("-" * 80)

    for company, total_count in duplicates:
        print(f"\n{company} ({total_count}행)")
        company_data = df[df['corp_name'] == company].sort_values('bsns_year', ascending=False)

        year_counts = company_data.groupby('bsns_year').size()
        for year in sorted(year_counts.index, reverse=True):
            year_data = company_data[company_data['bsns_year'] == year]
            count = len(year_data)

            if count > 1:
                print(f"  {int(year)}년: {count}행 (중복)")
                for idx, (_, row) in enumerate(year_data.iterrows(), 1):
                    print(f"    {idx}. {row['account_nm']:<50} {row['thstrm_amount']:>15,.0f}")
            else:
                print(f"  {int(year)}년: {count}행")
                row = year_data.iloc[0]
                print(f"    {row['account_nm']:<50} {row['thstrm_amount']:>15,.0f}")
else:
    print(f"\n✓ 중복된 기업 없음")

print(f"\n[요약]")
print("-" * 80)
print(f"총 기업: {len(company_counts)}개")
print(f"정상 (3행): {sum(1 for c in company_counts.values() if c == 3)}개")
print(f"중복있음: {len(duplicates)}개")
print("=" * 80)
