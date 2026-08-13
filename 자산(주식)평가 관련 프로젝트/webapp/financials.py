# -*- coding: utf-8 -*-
"""재무상태표·손익계산서·소득금액조정합계표 CSV 파싱.

세 CSV는 고정 서식을 따른다 (SPEC.md 참고):
- 재무상태표: 항목,금액 (자산총계/부채총계 행 포함)
- 손익계산서_3개년: 연도,당기순이익 (3행)
- 소득금액조정합계표_3개년: 연도,구분,과목,금액 (구분: 가산/차감)
"""
import io

import pandas as pd

REQUIRED_YEARS = 3


class FinancialsParseError(ValueError):
    pass


def _read_csv(file_bytes: bytes, filename: str) -> pd.DataFrame:
    try:
        return pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8-sig")
    except Exception as e:
        raise FinancialsParseError(f"'{filename}' 파일을 읽을 수 없습니다: {e}")


def _require_columns(df: pd.DataFrame, columns: list[str], filename: str):
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise FinancialsParseError(
            f"'{filename}'에 필요한 컬럼이 없습니다: {', '.join(missing)} "
            f"(현재 컬럼: {', '.join(df.columns)})"
        )


def parse_balance_sheet(file_bytes: bytes, filename: str = "재무상태표.csv") -> dict:
    df = _read_csv(file_bytes, filename)
    _require_columns(df, ["항목", "금액"], filename)

    def _get(item_name: str) -> float:
        rows = df[df["항목"].astype(str).str.strip() == item_name]
        if rows.empty:
            raise FinancialsParseError(f"'{filename}'에 '{item_name}' 항목이 없습니다.")
        return float(rows.iloc[0]["금액"])

    return {
        "total_assets": _get("자산총계"),
        "total_liabilities": _get("부채총계"),
    }


def parse_income_statements(file_bytes: bytes, filename: str = "손익계산서_3개년.csv") -> list[dict]:
    df = _read_csv(file_bytes, filename)
    _require_columns(df, ["연도", "당기순이익"], filename)

    if len(df) != REQUIRED_YEARS:
        raise FinancialsParseError(
            f"'{filename}'에는 최근 {REQUIRED_YEARS}개 사업연도가 있어야 합니다. (현재 {len(df)}개)"
        )

    df = df.sort_values("연도", ascending=False).reset_index(drop=True)
    labels = ["1년전 (가중치 3)", "2년전 (가중치 2)", "3년전 (가중치 1)"]

    years = []
    for i, row in df.iterrows():
        years.append(
            {
                "year": int(row["연도"]),
                "label": labels[i],
                "net_income": float(row["당기순이익"]),
            }
        )
    return years


def parse_adjustments(file_bytes: bytes, filename: str = "소득금액조정합계표_3개년.csv") -> dict:
    df = _read_csv(file_bytes, filename)
    _require_columns(df, ["연도", "구분", "과목", "금액"], filename)

    valid_types = {"가산", "차감"}
    invalid = set(df["구분"].astype(str).str.strip()) - valid_types
    if invalid:
        raise FinancialsParseError(
            f"'{filename}'의 '구분' 값은 '가산' 또는 '차감'이어야 합니다. 잘못된 값: {', '.join(invalid)}"
        )

    by_year: dict[int, dict] = {}
    for _, row in df.iterrows():
        year = int(row["연도"])
        entry = by_year.setdefault(year, {"additions": [], "subtractions": []})
        item = {"name": str(row["과목"]).strip(), "amount": float(row["금액"])}
        if str(row["구분"]).strip() == "가산":
            entry["additions"].append(item)
        else:
            entry["subtractions"].append(item)
    return by_year


def build_years_payload(income_statements: list[dict], adjustments_by_year: dict) -> list[dict]:
    years = []
    for entry in income_statements:
        adj = adjustments_by_year.get(entry["year"], {"additions": [], "subtractions": []})
        years.append(
            {
                "label": entry["label"],
                "year": entry["year"],
                "net_income": entry["net_income"],
                "additions": adj["additions"],
                "subtractions": adj["subtractions"],
            }
        )
    return years


def parse_all(balance_sheet_bytes: bytes, income_bytes: bytes, adjustments_bytes: bytes) -> dict:
    net_asset = parse_balance_sheet(balance_sheet_bytes)
    income_statements = parse_income_statements(income_bytes)
    adjustments_by_year = parse_adjustments(adjustments_bytes)
    years = build_years_payload(income_statements, adjustments_by_year)

    unmatched = set(adjustments_by_year) - {y["year"] for y in years}
    if unmatched:
        raise FinancialsParseError(
            f"소득금액조정합계표에 손익계산서와 매칭되지 않는 연도가 있습니다: {sorted(unmatched)}"
        )

    return {"net_asset": net_asset, "years": years}
