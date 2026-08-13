# -*- coding: utf-8 -*-
"""financial_raw.csv(corp_code 기준)을 companies_universe.csv의 industry_id와 조인해
프로젝트6/webapp/data/{bank,securities,insurance,cardcapital}.csv로 분리 저장한다."""
import csv
from pathlib import Path

BASE_DIR = Path(__file__).parent
WEBAPP_DATA_DIR = BASE_DIR.parent / "webapp" / "data"

RAW_PATH = BASE_DIR / "financial_raw.csv"
UNIVERSE_PATH = BASE_DIR / "companies_universe.csv"


def main():
    with open(UNIVERSE_PATH, encoding="utf-8-sig") as f:
        universe = {r["corp_code"]: r["industry_id"] for r in csv.DictReader(f)}

    with open(RAW_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    by_industry = {"bank": [], "securities": [], "insurance": [], "cardcapital": []}
    unmatched = []
    for r in rows:
        industry_id = universe.get(r["corp_code"])
        if industry_id not in by_industry:
            unmatched.append(r["corp_name"])
            continue
        by_industry[industry_id].append(r)

    fieldnames = ["corp_code", "stock_code", "corp_name", "year", "fs_div", "sj_div",
                  "account_name", "amount", "memo", "updated_at"]

    WEBAPP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    summary = []
    for industry_id, industry_rows in by_industry.items():
        out_path = WEBAPP_DATA_DIR / f"{industry_id}.csv"
        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(industry_rows)
        n_companies = len(set(r["corp_code"] for r in industry_rows))
        summary.append(f"{industry_id}: {len(industry_rows)}행, {n_companies}개사 -> {out_path}")

    with open(BASE_DIR / "publish_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(summary))
        if unmatched:
            f.write("\n\nunmatched (industry_id 없음): " + ", ".join(unmatched))


if __name__ == "__main__":
    main()
