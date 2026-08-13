# -*- coding: utf-8 -*-
"""CFS(연결재무제표)가 없어 1차 수집에서 실패한 회사(단독법인 - 인터넷은행/저축은행/
소형 캐피탈·증권사 등)를 OFS(별도재무제표)로 재시도해 financial_raw.csv에 추가한다."""
import csv
from pathlib import Path

import dart_fss

import importlib.util
spec = importlib.util.spec_from_file_location("collect", str(Path(__file__).parent / "03_collect_financials.py"))
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)

BASE_DIR = Path(__file__).parent
OUT_PATH = BASE_DIR / "financial_raw.csv"

RETRY_NAMES = {"카카오뱅크", "케이뱅크", "푸른저축은행", "큐캐피탈", "롯데손해보험",
               "흥국화재", "유화증권", "코리아에셋투자증권"}


def collect_company_ofs(corp_list, company):
    corp = corp_list.find_by_corp_code(company["corp_code"])
    if corp is None:
        return [], "corp not found"
    try:
        fs = corp.extract_fs(
            bgn_de=collect.BGN_DE, end_de=collect.END_DE, fs_tp=collect.FS_TP,
            dataset="web", separate=True, progressbar=False,
        )
    except Exception as e:
        return [], f"extract_fs(separate) failed: {e}"

    rows = []
    for tp in collect.FS_TP:
        try:
            sheet = fs[tp]
            rows.extend(collect.rows_from_sheet(sheet, collect.SJ_DIV_MAP[tp], company["industry_id"], company))
        except Exception as e:
            return rows, f"{tp} sheet processing failed: {e}"
    if not rows:
        return [], "no matching accounts extracted (OFS)"
    for r in rows:
        r["fs_div"] = "OFS"
    return rows, None


def main():
    dart_fss.set_api_key(collect.load_api_key())
    corp_list = dart_fss.get_corp_list()
    companies = collect.load_universe()
    targets = [c for c in companies if c["corp_name"] in RETRY_NAMES]

    with open(OUT_PATH, encoding="utf-8-sig") as f:
        existing_rows = list(csv.DictReader(f))

    fieldnames = ["corp_code", "stock_code", "corp_name", "year", "fs_div", "sj_div",
                  "account_name", "amount", "memo", "updated_at"]
    all_rows = list(existing_rows)
    results = []
    for company in targets:
        rows, err = collect_company_ofs(corp_list, company)
        results.append((company["corp_name"], len(rows), err))
        all_rows.extend(rows)
        with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_rows)

    with open(BASE_DIR / "retry_ofs_result.txt", "w", encoding="utf-8") as f:
        for name, n, err in results:
            f.write(f"{name}: {n} rows, err={err}\n")


if __name__ == "__main__":
    main()
