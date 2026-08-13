# -*- coding: utf-8 -*-
"""비상장주식 보충적 평가방법 계산 로직 (상속세및증여세법 시행령 제54~56조 기준).

용어 정리
- 순손익가치: 최근 3개 사업연도 순손익액의 가중평균액(3:2:1) ÷ 순손익가치환원율
- 순자산가치: (자산총액 - 부채총액) ÷ 발행주식총수, 음수면 0
- 가중평균: 일반법인 순손익가치:순자산가치 = 3:2, 부동산과다보유법인 = 2:3
- 하한: 가중평균액이 순자산가치의 80%에 미달하면 순자산가치의 80%를 평가액으로 함(시행령 §54①)
- 순자산가치로만 평가: 부동산 80%이상 보유법인, 주식등 보유비율 80%이상 법인,
  사업개시전/3년미만 법인, 휴폐업법인, 청산법인 등(시행령 §54④)
- 최대주주 등 할증: 평가액에 할증률(기본 20%)을 가산. 중소기업 등은 면제(조특법 §101)
"""

from dataclasses import dataclass, field

WEIGHTS = (3, 2, 1)  # 1년전(직전 사업연도), 2년전, 3년전
WEIGHT_SUM = sum(WEIGHTS)

SPECIAL_CORP_TYPES = {
    "normal": "일반법인 (순손익가치:순자산가치 = 3:2)",
    "realestate_over50": "부동산과다보유법인 (부동산비율 50%이상~80%미만, 2:3)",
    "net_asset_only": "순자산가치로만 평가 (부동산·주식 80%이상 보유, 사업개시전/3년미만, 휴폐업, 청산 등)",
}


class ValuationError(ValueError):
    pass


@dataclass
class YearAdjustment:
    label: str
    net_income: float
    additions: list = field(default_factory=list)   # [{"name":..,"amount":..}] 익금산입/손금불산입(가산)
    subtractions: list = field(default_factory=list)  # 손금산입/익금불산입(차감)

    @property
    def adjusted_net_income(self) -> float:
        add = sum(item.get("amount", 0) for item in self.additions)
        sub = sum(item.get("amount", 0) for item in self.subtractions)
        return self.net_income + add - sub


def compute_profit_value(years: list[YearAdjustment], shares_outstanding: float, capitalization_rate: float):
    if shares_outstanding <= 0:
        raise ValuationError("발행주식총수는 0보다 커야 합니다.")
    if capitalization_rate <= 0:
        raise ValuationError("순손익가치환원율은 0보다 커야 합니다.")
    if len(years) != 3:
        raise ValuationError("순손익액은 최근 3개 사업연도를 입력해야 합니다.")

    adjusted = [y.adjusted_net_income for y in years]
    weighted_total = sum(v * w for v, w in zip(adjusted, WEIGHTS)) / WEIGHT_SUM
    weighted_per_share = weighted_total / shares_outstanding
    profit_value_per_share = weighted_per_share / (capitalization_rate / 100)

    return {
        "adjusted_net_incomes": adjusted,
        "weighted_total_net_income": weighted_total,
        "weighted_net_income_per_share": weighted_per_share,
        "profit_value_per_share": profit_value_per_share,
    }


def compute_net_asset_value(total_assets: float, total_liabilities: float, shares_outstanding: float, goodwill: float = 0.0):
    if shares_outstanding <= 0:
        raise ValuationError("발행주식총수는 0보다 커야 합니다.")
    net_asset_amount = total_assets - total_liabilities + goodwill
    if net_asset_amount < 0:
        net_asset_amount = 0.0
    net_asset_value_per_share = net_asset_amount / shares_outstanding
    return {
        "net_asset_amount": net_asset_amount,
        "net_asset_value_per_share": net_asset_value_per_share,
    }


def compute_weighted_value(profit_value: float, net_asset_value: float, special_corp_type: str):
    if special_corp_type not in SPECIAL_CORP_TYPES:
        raise ValuationError(f"알 수 없는 법인 유형입니다: {special_corp_type}")

    if special_corp_type == "net_asset_only":
        weighted = net_asset_value
        ratio = (0, 1)
    elif special_corp_type == "realestate_over50":
        weighted = (profit_value * 2 + net_asset_value * 3) / 5
        ratio = (2, 3)
    else:
        weighted = (profit_value * 3 + net_asset_value * 2) / 5
        ratio = (3, 2)

    floor = net_asset_value * 0.8
    final_before_premium = max(weighted, floor)
    floor_applied = final_before_premium == floor and floor > weighted

    return {
        "ratio": ratio,
        "weighted_value": weighted,
        "floor_value": floor,
        "floor_applied": floor_applied,
        "value_before_premium": final_before_premium,
    }


def apply_major_shareholder_premium(value: float, is_major_shareholder: bool, is_exempt: bool, premium_rate: float):
    applied = is_major_shareholder and not is_exempt and premium_rate > 0
    final_value = value * (1 + premium_rate / 100) if applied else value
    return {
        "premium_applied": applied,
        "premium_rate": premium_rate if applied else 0,
        "final_value_per_share": final_value,
    }


def run_valuation(payload: dict) -> dict:
    years = [
        YearAdjustment(
            label=y["label"],
            net_income=y["net_income"],
            additions=y.get("additions", []),
            subtractions=y.get("subtractions", []),
        )
        for y in payload["years"]
    ]

    shares_outstanding = payload["shares_outstanding"]
    capitalization_rate = payload["capitalization_rate"]

    profit = compute_profit_value(years, shares_outstanding, capitalization_rate)

    net_asset_input = payload["net_asset"]
    net_asset = compute_net_asset_value(
        total_assets=net_asset_input["total_assets"],
        total_liabilities=net_asset_input["total_liabilities"],
        shares_outstanding=shares_outstanding,
        goodwill=net_asset_input.get("goodwill", 0.0),
    )

    weighted = compute_weighted_value(
        profit_value=profit["profit_value_per_share"],
        net_asset_value=net_asset["net_asset_value_per_share"],
        special_corp_type=payload["special_corp_type"],
    )

    major = payload.get("major_shareholder", {})
    premium = apply_major_shareholder_premium(
        value=weighted["value_before_premium"],
        is_major_shareholder=major.get("is_major_shareholder", False),
        is_exempt=major.get("is_exempt", False),
        premium_rate=major.get("premium_rate", 20),
    )

    return {
        "profit": profit,
        "net_asset": net_asset,
        "weighted": weighted,
        "premium": premium,
        "special_corp_type": payload["special_corp_type"],
        "special_corp_label": SPECIAL_CORP_TYPES[payload["special_corp_type"]],
    }
