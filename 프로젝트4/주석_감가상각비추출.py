# -*- coding: utf-8 -*-
"""
DART 사업보고서 XBRL 주석(Notes)에서 "비용의 성격별 분류" 표를 찾아
감가상각비를 추출하는 스크립트.

배경
----
OpenDART의 단일회사 전체 재무제표 API(fnlttSinglAcntAll)는 재무상태표/손익계산서/
현금흐름표 "본문"만 제공하고 주석은 제공하지 않는다. 감가상각비는 많은 기업에서
손익계산서 본문에 별도 표시되지 않고, 주석 "비용의 성격별 분류"(Expenses by Nature)
에서만 확인 가능하다. 이 스크립트는 dart-fss의 저수준 XBRL 파서(report.xbrl)를 이용해
사업보고서에 첨부된 XBRL 인스턴스 문서 전체(본문+주석)를 로드하고, 그 안에서
"성격별" 주석 표를 찾아 label_ko(계정명)에 "감가상각"이 포함된 행을 추출한다.

핵심 이슈와 처리 방식
----------------------
1. concept_id(계정 태그)는 회사마다 다르다.
   - 표준 IFRS 태그: ifrs-full_DepreciationExpense (예: 삼성전자)
   - 회사별 확장 태그: entity00164779_DeprecationAndOthers... (예: SK하이닉스, label_ko="감가상각비 등")
   - 감가상각+무형자산상각 합산 태그: ifrs-full_DepreciationAndAmortisationExpense (예: LG화학)
   => concept_id로 찾지 않고 label_ko 텍스트에 "감가상각" 포함 여부로 찾는다.
   => label_ko에 "무형"이 함께 포함되면 감가상각비+무형자산상각비 합산치일 수 있으므로
      is_combined 플래그를 남긴다.

2. 사업부문(segment)별 컬럼이 섞여 있다 (예: LG화학의 석유화학/생명과학/... 컬럼).
   전사 합계만 남기기 위해, 컬럼의 dimension label 집합이
   {'연결재무제표','별도재무제표','연결','별도','공시금액'} 의 부분집합인 경우만 채택한다.

3. 일부 기업(특히 금융지주/은행/보험 등)은 "성격별 비용분류" 주석 자체를 XBRL에
   태깅하지 않는다 (기능별 표시만 하고 성격별 주석을 생략). 이 경우는 파싱 실패가
   아니라 원천 데이터 부재이므로 not_found로 기록하고 건너뛴다.

출력
----
kospi100_depreciation_notes.csv : 기간별 감가상각비 추출 결과
kospi100_depreciation_notfound.csv : 추출 실패(주석 부재 등) 기업 목록과 사유
"""

import os
import re
import time
import traceback
import pandas as pd
from tqdm import tqdm

import dart_fss as dart
from dart_fss.fs.extract import search_annual_report

API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"

SOURCE_CSV = "kospi100_all_statements_2025_v12.csv"
OUTPUT_CSV = "kospi100_depreciation_notes.csv"
NOTFOUND_CSV = "kospi100_depreciation_notfound.csv"

# 전사 합계로 인정할 dimension label 집합 (이 밖의 라벨이 하나라도 섞이면 사업부문 등 세부항목으로 간주해 제외)
TOTAL_LABELS = {'연결재무제표', '별도재무제표', '연결', '별도', '공시금액'}

NOTE_TITLE_REGEX = re.compile(r'성격별')
DEPRECIATION_LABEL_REGEX = re.compile(r'감가상각')
INTANGIBLE_HINT_REGEX = re.compile(r'무형')


def load_target_companies(source_csv: str) -> pd.DataFrame:
    """기존에 추출된 kospi100 재무제표 CSV에서 기업 목록/연도/연결개별 구분을 재사용"""
    df = pd.read_csv(source_csv, encoding='utf-8-sig')
    cols = ['market_cap_rank', 'stock_code', 'corp_name', 'corp_code', 'bsns_year', 'fs_div']
    targets = df[cols].drop_duplicates().sort_values('market_cap_rank').reset_index(drop=True)
    targets['corp_code'] = targets['corp_code'].astype(str).str.zfill(8)
    targets['stock_code'] = targets['stock_code'].astype(str).str.zfill(6)
    return targets


def find_note_tables(xbrl):
    """XBRL 전체 테이블 중 '성격별 비용분류' 주석 표를 찾는다 (연결/별도 두 개가 있을 수 있음)"""
    return [t for t in xbrl.tables if NOTE_TITLE_REGEX.search(t.definition)]


def is_total_column(cls_key) -> bool:
    """컬럼의 dimension label 조합이 사업부문 등 세부항목이 아닌 전사 합계인지 판별"""
    if isinstance(cls_key, str):
        cls_key = (cls_key,)
    return all(label in TOTAL_LABELS for label in cls_key)


def extract_depreciation_rows(table, fs_div: str):
    """
    주석 표 하나에서 label_ko에 '감가상각'이 포함된 행을 찾아
    (period, value) 쌍의 리스트를 반환한다. 연결/별도(fs_div)에 맞는 컬럼만 채택.
    """
    fs_label = '별도재무제표' if fs_div == 'OFS' else '연결재무제표'

    try:
        df = table.to_DataFrame(lang='ko', show_concept=True, show_class=False)
    except Exception:
        return []

    label_cols = [c for c in df.columns if c[1] == 'label_ko']
    concept_cols = [c for c in df.columns if c[1] == 'concept_id']
    if not label_cols:
        return []
    label_col = label_cols[0]
    concept_col = concept_cols[0] if concept_cols else None

    date_cols = [c for c in df.columns if re.search(r'\d{8}', str(c[0]))]

    results = []
    for idx, row in df.iterrows():
        label = str(row[label_col]) if pd.notna(row[label_col]) else ''
        if not DEPRECIATION_LABEL_REGEX.search(label):
            continue

        concept_id = str(row[concept_col]) if concept_col is not None and pd.notna(row[concept_col]) else None
        is_combined = bool(INTANGIBLE_HINT_REGEX.search(label))

        for col in date_cols:
            period = col[0]
            cls_key = col[1]
            if isinstance(cls_key, str):
                cls_key_tuple = (cls_key,)
            else:
                cls_key_tuple = tuple(cls_key)

            if fs_label not in cls_key_tuple:
                continue
            if not is_total_column(cls_key_tuple):
                continue

            value = row[col]
            if pd.isna(value) or value == '':
                continue
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            results.append({
                'period': period,
                'value': value,
                'label_ko': label,
                'concept_id': concept_id,
                'is_combined_with_intangible': is_combined,
                'note_table_code': table.code,
            })

    return results


def dedupe_by_period(rows):
    """같은 period에 여러 컬럼 변형(예: (연결재무제표,) vs (연결재무제표,공시금액))이 잡힐 수 있어 period당 하나만 남긴다"""
    best = {}
    for r in rows:
        key = (r['period'], r['label_ko'])
        if key not in best:
            best[key] = r
    return list(best.values())


def process_company(row) -> dict:
    """기업 1개에 대해 연간보고서 XBRL을 로드하고 감가상각비 주석 데이터를 추출"""
    corp_code = row['corp_code']
    fs_div = row['fs_div']
    bsns_year = int(row['bsns_year'])
    separate = (fs_div == 'OFS')

    bgn_de = f'{bsns_year}0101'
    end_de = f'{bsns_year + 1}1231'

    result = {
        'market_cap_rank': row['market_cap_rank'],
        'stock_code': row['stock_code'],
        'corp_name': row['corp_name'],
        'corp_code': corp_code,
        'fs_div': fs_div,
        'bsns_year': bsns_year,
        'status': None,
        'rows': [],
    }

    try:
        reports = search_annual_report(
            corp_code=corp_code, bgn_de=bgn_de, end_de=end_de, separate=separate)
    except Exception as e:
        result['status'] = f'annual_report_not_found: {e}'
        return result

    if len(reports) == 0:
        result['status'] = 'annual_report_not_found'
        return result

    report = reports[0]

    try:
        xbrl = report.xbrl
    except Exception as e:
        result['status'] = f'xbrl_load_error: {e}'
        return result

    if xbrl is None:
        result['status'] = 'no_xbrl'
        return result

    note_tables = find_note_tables(xbrl)
    if not note_tables:
        result['status'] = 'no_expense_by_nature_note'
        return result

    all_rows = []
    for table in note_tables:
        try:
            all_rows.extend(extract_depreciation_rows(table, fs_div))
        except Exception:
            continue

    all_rows = dedupe_by_period(all_rows)

    if not all_rows:
        result['status'] = 'note_found_but_no_depreciation_row'
        return result

    result['status'] = 'ok'
    result['rows'] = all_rows
    return result


def main():
    dart.set_api_key(api_key=API_KEY)
    dart.utils.spinner.spinner_enable = False

    if not os.path.exists(SOURCE_CSV):
        raise FileNotFoundError(
            f"'{SOURCE_CSV}' 파일이 없습니다. 먼저 다운로드3.py를 실행해 KOSPI100 재무제표를 추출하세요.")

    targets = load_target_companies(SOURCE_CSV)
    print(f"[INFO] 대상 기업 수: {len(targets)}개")

    # 이미 처리된 기업은 건너뛰기 (재실행 시 이어하기)
    done_corp_codes = set()
    if os.path.exists(OUTPUT_CSV):
        prev = pd.read_csv(OUTPUT_CSV, encoding='utf-8-sig', dtype={'corp_code': str})
        done_corp_codes |= set(prev['corp_code'])
    if os.path.exists(NOTFOUND_CSV):
        prev_nf = pd.read_csv(NOTFOUND_CSV, encoding='utf-8-sig', dtype={'corp_code': str})
        done_corp_codes |= set(prev_nf['corp_code'])

    output_rows = []
    notfound_rows = []

    remaining = targets[~targets['corp_code'].isin(done_corp_codes)]
    print(f"[INFO] 이미 처리됨: {len(targets) - len(remaining)}개, 남은 대상: {len(remaining)}개")

    for _, row in tqdm(remaining.iterrows(), total=len(remaining), desc='감가상각비 주석 추출'):
        try:
            result = process_company(row)
        except Exception as e:
            result = {
                'market_cap_rank': row['market_cap_rank'],
                'stock_code': row['stock_code'],
                'corp_name': row['corp_name'],
                'corp_code': row['corp_code'],
                'fs_div': row['fs_div'],
                'bsns_year': row['bsns_year'],
                'status': f'unexpected_error: {e}',
                'rows': [],
            }
            traceback.print_exc()

        if result['status'] == 'ok':
            for r in result['rows']:
                output_rows.append({
                    'market_cap_rank': result['market_cap_rank'],
                    'stock_code': result['stock_code'],
                    'corp_name': result['corp_name'],
                    'corp_code': result['corp_code'],
                    'fs_div': result['fs_div'],
                    'bsns_year': result['bsns_year'],
                    'period': r['period'],
                    'depreciation_expense': r['value'],
                    'label_ko': r['label_ko'],
                    'concept_id': r['concept_id'],
                    'is_combined_with_intangible': r['is_combined_with_intangible'],
                    'note_table_code': r['note_table_code'],
                })
        else:
            notfound_rows.append({
                'market_cap_rank': result['market_cap_rank'],
                'stock_code': result['stock_code'],
                'corp_name': result['corp_name'],
                'corp_code': result['corp_code'],
                'fs_div': result['fs_div'],
                'bsns_year': result['bsns_year'],
                'status': result['status'],
            })

        # 체크포인트 저장 (중간에 끊겨도 이어할 수 있도록 매 기업마다 append)
        if output_rows:
            pd.DataFrame(output_rows).to_csv(
                OUTPUT_CSV, mode='a' if os.path.exists(OUTPUT_CSV) else 'w',
                header=not os.path.exists(OUTPUT_CSV), index=False, encoding='utf-8-sig')
            output_rows = []
        if notfound_rows:
            pd.DataFrame(notfound_rows).to_csv(
                NOTFOUND_CSV, mode='a' if os.path.exists(NOTFOUND_CSV) else 'w',
                header=not os.path.exists(NOTFOUND_CSV), index=False, encoding='utf-8-sig')
            notfound_rows = []

        time.sleep(0.1)

    # 최종 요약
    ok_df = pd.read_csv(OUTPUT_CSV, encoding='utf-8-sig') if os.path.exists(OUTPUT_CSV) else pd.DataFrame()
    nf_df = pd.read_csv(NOTFOUND_CSV, encoding='utf-8-sig') if os.path.exists(NOTFOUND_CSV) else pd.DataFrame()
    ok_companies = ok_df['corp_code'].nunique() if len(ok_df) else 0
    print(f"\n[SUCCESS] 감가상각비 추출 성공: {ok_companies}개 기업 / 실패(주석 부재 등): {len(nf_df)}개 기업")
    if len(nf_df):
        print("[INFO] 실패 사유별 집계:")
        print(nf_df['status'].value_counts().to_string())


if __name__ == "__main__":
    main()
1