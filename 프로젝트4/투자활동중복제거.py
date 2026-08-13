import pandas as pd

# 투자활동현금흐름 파일 로드
invest_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_투자활동현금흐름.csv'
df = pd.read_csv(invest_file)

print("=" * 80)
print("투자활동현금흐름 중복 제거")
print("=" * 80)

# 주성엔지니어링 처리 (2025년 중 NaN 제거, -53.8억 유지)
print(f"\n[주성엔지니어링 처리]")
print("-" * 80)
sang = df[df['corp_name'] == '주성엔지니어링'].copy()
sang_2025 = sang[sang['bsns_year'] == 2025]
print(f"처리 전: {len(sang_2025)}행")
for idx, row in sang_2025.iterrows():
    print(f"  {row['thstrm_amount']}")

# NaN이 아닌 행만 유지
sang_filtered = []
for year in [2025, 2024, 2023]:
    year_data = sang[sang['bsns_year'] == year]
    if len(year_data) > 0:
        # NaN이 아닌 행 선택
        valid_data = year_data.dropna(subset=['thstrm_amount'])
        if len(valid_data) > 0:
            # 금액 절대값이 큰 것 선택
            max_row = valid_data.loc[valid_data['thstrm_amount'].abs().idxmax()]
            sang_filtered.append(max_row)
            if len(year_data) > 1:
                print(f"  {int(year)}년: {len(year_data)}행 -> 1행 (선택: {max_row['thstrm_amount']:,.0f})")

print(f"처리 후: {len(sang_filtered)}행")

# 이오테크닉스 처리 (2025년 중 금액이 큰 것만 유지)
print(f"\n[이오테크닉스 처리]")
print("-" * 80)
io = df[df['corp_name'] == '이오테크닉스'].copy()
io_2025 = io[io['bsns_year'] == 2025]
print(f"처리 전: {len(io_2025)}행")
for idx, row in io_2025.iterrows():
    print(f"  {row['thstrm_amount']:>15,.0f}")

# 금액이 큰 것만 유지
io_filtered = []
for year in [2025, 2024, 2023]:
    year_data = io[io['bsns_year'] == year]
    if len(year_data) > 0:
        # 금액 절대값이 큰 것 선택
        max_row = year_data.loc[year_data['thstrm_amount'].abs().idxmax()]
        io_filtered.append(max_row)
        if len(year_data) > 1:
            print(f"  {int(year)}년: {len(year_data)}행 -> 1행 (선택: {max_row['thstrm_amount']:,.0f})")

print(f"처리 후: {len(io_filtered)}행")

# 다른 기업들
other = df[(df['corp_name'] != '주성엔지니어링') & (df['corp_name'] != '이오테크닉스')].copy()

# 결합 및 정렬
result_df = pd.concat([other, pd.DataFrame(sang_filtered), pd.DataFrame(io_filtered)], ignore_index=True)
result_df = result_df.sort_values(by=['corp_name', 'bsns_year'], ascending=[True, False])
result_df = result_df.reset_index(drop=True)

print(f"\n[결과]")
print("-" * 80)
print(f"처리 전: {len(df)}행")
print(f"처리 후: {len(result_df)}행 (제거: {len(df) - len(result_df)}행)")

# 저장
output_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_투자활동현금흐름.csv'
result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"저장: {output_file}")

print("=" * 80)
