import pandas as pd

df = pd.read_csv(r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_필요데이터.csv')

print('=' * 80)
print('기업별 행 수 분석')
print('=' * 80)

summary = df.groupby('corp_name').size().sort_values(ascending=False)
extra_companies = []

for company, count in summary.items():
    if count != 3:
        extra_companies.append((company, count))
        print(f'\n{company:<25} {count}행 (기대값: 3행)')
        sub = df[df['corp_name'] == company]
        year_count = sub.groupby('bsns_year').size()
        print(f'  연도별: ', end='')
        for year in sorted(year_count.index):
            print(f'{int(year)}년({year_count[year]}행) ', end='')
        print()

print('\n' + '=' * 80)
print(f'총 기업 수: {len(summary)}개')
print(f'3행씩인 기업: {len(summary) - len(extra_companies)}개')
print(f'3행 초과인 기업: {len(extra_companies)}개')
print(f'\n총 행 수: {len(df)}행')
print(f'기대값: {len(summary) * 3}행')
print(f'차이: {len(df) - len(summary) * 3}행')
print('=' * 80)
