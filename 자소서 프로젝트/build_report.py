"""
auditor_raw_results.json을 읽어 4대회계법인별 감사 대상 상장기업 현황을
엑셀 파일(시트별: 요약, 삼일PwC, 삼정KPMG, 한영EY, 안진Deloitte, 기타/미확인)로 정리한다.
"""
import json
import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_PATH = os.path.join(BASE_DIR, "auditor_raw_results.json")
OUT_PATH = os.path.join(BASE_DIR, "4대회계법인_상장기업_감사현황.xlsx")

BIG4_MAP = {
    "삼일회계법인": "삼일PwC",
    "삼정회계법인": "삼정KPMG",
    "한영회계법인": "한영EY",
    "안진회계법인": "안진Deloitte",
}


def main():
    with open(RAW_PATH, encoding="utf-8") as f:
        results = json.load(f)

    df = pd.DataFrame(results)
    df["big4_group"] = df["adtor"].map(BIG4_MAP)

    found = df[df["adtor"].notna()].copy()
    no_data = df[df["adtor"].isna()].copy()

    # 감사인명 표기 흔들림(공백 등) 방지를 위해 그대로 사용, 상위 감사인 랭킹도 별도 생성
    auditor_counts = (
        found.groupby("adtor").size().sort_values(ascending=False).reset_index(name="기업수")
    )

    summary_rows = []
    total_found = len(found)
    for kr_name, en_name in BIG4_MAP.items():
        n = int((found["adtor"] == kr_name).sum())
        pct = round(n / total_found * 100, 1) if total_found else 0
        summary_rows.append({"회계법인": f"{kr_name}({en_name})", "감사기업수": n, "비중(%)": pct})
    big4_total = found["adtor"].isin(BIG4_MAP.keys()).sum()
    others_total = total_found - big4_total
    summary_rows.append(
        {
            "회계법인": "기타(4대회계법인 외)",
            "감사기업수": int(others_total),
            "비중(%)": round(others_total / total_found * 100, 1) if total_found else 0,
        }
    )
    summary_rows.append(
        {"회계법인": "합계(감사인 확인됨)", "감사기업수": int(total_found), "비중(%)": 100.0}
    )
    summary_rows.append(
        {"회계법인": "데이터 미확인(미상장전환/최근상장 등)", "감사기업수": int(len(no_data)), "비중(%)": None}
    )
    summary_df = pd.DataFrame(summary_rows)

    cols = [
        "corp_name",
        "stock_code",
        "market",
        "adtor",
        "adt_opinion",
        "bsns_year_label",
        "stlm_dt",
    ]
    col_names = {
        "corp_name": "기업명",
        "stock_code": "종목코드",
        "market": "시장구분",
        "adtor": "감사인",
        "adt_opinion": "감사의견",
        "bsns_year_label": "사업연도",
        "stlm_dt": "결산일",
    }

    with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="요약", index=False)
        auditor_counts.to_excel(writer, sheet_name="전체감사인랭킹", index=False)

        for kr_name, en_name in BIG4_MAP.items():
            sub = found[found["adtor"] == kr_name][cols].rename(columns=col_names)
            sub = sub.sort_values("종목코드")
            writer_sheet = f"{en_name}"
            sub.to_excel(writer, sheet_name=writer_sheet, index=False)

        others = found[~found["adtor"].isin(BIG4_MAP.keys())][cols].rename(columns=col_names)
        others = others.sort_values(["감사인", "종목코드"])
        others.to_excel(writer, sheet_name="기타회계법인", index=False)

        no_data_out = no_data[["corp_name", "stock_code", "status"]].rename(
            columns={"corp_name": "기업명", "stock_code": "종목코드", "status": "DART상태코드"}
        )
        no_data_out.to_excel(writer, sheet_name="데이터미확인", index=False)

    print("저장 완료:", OUT_PATH)
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
