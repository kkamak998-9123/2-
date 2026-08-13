# -*- coding: utf-8 -*-
"""
반도체_재무비율_대시보드.html 의 embedded DATA 배열에
'fixedAssetRatio' 필드(고정자산비율 %) 를 추가
"""

import json
import re
import pandas as pd

html_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\반도체_재무비율_대시보드.html'
ratio_file = r'C:\Users\willo\Desktop\코딩\프로젝트4\프로젝트4_재무비율분석.csv'

ratio_df = pd.read_csv(ratio_file, dtype={'corp_code': str})
ratio_df['code8'] = ratio_df['corp_code'].str.zfill(8)

lookup = {}
for _, row in ratio_df.iterrows():
    key = (row['code8'], int(row['year']))
    lookup[key] = row['고정자산비율(%)']

with open(html_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

data_line_idx = None
for i, line in enumerate(lines):
    if line.startswith('const DATA = ['):
        data_line_idx = i
        break

if data_line_idx is None:
    raise RuntimeError('DATA 라인을 찾지 못했습니다')

line = lines[data_line_idx]
m = re.match(r'^const DATA = (\[.*\]);\s*$', line)
if not m:
    raise RuntimeError('DATA 라인 형식이 예상과 다릅니다')

data = json.loads(m.group(1))

missing = []
for row in data:
    key = (row['code'], int(row['year']))
    if key in lookup:
        val = lookup[key]
        row['fixedAssetRatio'] = None if pd.isna(val) else round(float(val), 2)
    else:
        missing.append(key)
        row['fixedAssetRatio'] = None

new_json = json.dumps(data, ensure_ascii=False, separators=(', ', ': '))
lines[data_line_idx] = 'const DATA = ' + new_json + ';\n'

with open(html_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

report = []
report.append('전체 레코드 수: ' + str(len(data)))
report.append('매칭 안 된 레코드 수: ' + str(len(missing)))
if missing:
    report.append(str(missing))
print('\n'.join(report))
