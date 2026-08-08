"""그래프 관련 공통 함수 (원본 지표 그래프 + 비율 추이 그래프)"""

import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from utils import 숫자줄이기, 입력받기_예아니오, 연도_라벨, 연결여부

if os.name == "nt":
    plt.rc("font", family="Malgun Gothic")
else:
    plt.rc("font", family="AppleGothic")
plt.rcParams["axes.unicode_minus"] = False

_SAVE_DIR = os.path.join(os.path.dirname(__file__), "output")


def _스케일_결정(values: np.ndarray):
    max_val = np.nanmax(np.abs(values)) if values.size else np.nan
    if np.isnan(max_val) or max_val == 0:
        return 1e12, "조 원"
    if max_val >= 1e12:
        return 1e12, "조 원"
    if max_val >= 1e8:
        return 1e8, "억 원"
    return 1, "원"


def _저장(fig, 기본이름: str):
    if not 입력받기_예아니오("그래프를 이미지로 저장할까요?"):
        return
    os.makedirs(_SAVE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    안전한이름 = "".join(c for c in 기본이름 if c not in '\\/:*?"<>|')
    파일경로 = os.path.join(_SAVE_DIR, f"{안전한이름}_{timestamp}.png")
    fig.savefig(파일경로, dpi=150, bbox_inches="tight")
    print(f"✅ 저장됨: {파일경로}")


def 연도프레임_만들기(df: pd.DataFrame, 선택된_라벨목록: list) -> pd.DataFrame:
    """원본 재무제표 df(label_col + 연도컬럼)에서 선택된 행만 추려 index=지표명,
    columns=연도(YYYY) 형태의 숫자 DataFrame으로 변환.

    같은 연도에 연결/별도 재무제표가 동시에 존재하면 연결재무제표 컬럼을 우선한다.
    """
    label_col = df.columns[0]
    filtered = df[df[label_col].isin(선택된_라벨목록)].copy()
    filtered = filtered.set_index(label_col)

    연도별_컬럼: dict[str, tuple] = {}
    for col in filtered.columns:
        연도 = 연도_라벨(col)
        연결 = 연결여부(col)
        if 연도 not in 연도별_컬럼 or (연결 and not 연도별_컬럼[연도][1]):
            연도별_컬럼[연도] = (col, 연결)

    정렬된_연도 = sorted(연도별_컬럼)
    결과 = pd.DataFrame(
        {연도: filtered[연도별_컬럼[연도][0]] for 연도 in 정렬된_연도},
        index=filtered.index,
    )
    return 결과.apply(pd.to_numeric, errors="coerce")


def 지표_그래프(plot_df: pd.DataFrame, title: str, 회사명: str):
    """plot_df: index=지표명, columns=연도, values=원 단위 금액"""
    if plot_df.empty:
        print("❌ 표시할 데이터가 없습니다.")
        return

    scale, unit_str = _스케일_결정(plot_df.values)
    plot_df_scaled = plot_df / scale

    fig = plt.figure(figsize=(11, 7))
    display_df = plot_df_scaled.T
    display_df.plot(marker="o", ax=plt.gca(), linewidth=2, markersize=6)
    ymin, ymax = plt.ylim()
    plt.ylim(ymin, ymax * 1.15)

    for i, row_label in enumerate(plot_df.index):
        orig_values = plot_df.loc[row_label].values
        y_values = plot_df_scaled.loc[row_label].values
        for x_idx, (orig_val, y_val) in enumerate(zip(orig_values, y_values)):
            if np.isnan(orig_val):
                continue
            offset = 12 if i % 2 == 0 else -18
            plt.annotate(
                숫자줄이기(orig_val), (x_idx, y_val),
                textcoords="offset points", xytext=(0, offset),
                ha="center", fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", edgecolor="gray", alpha=0.7),
            )

    plt.title(f"[{회사명}] {title}", fontsize=16, fontweight="bold", pad=15)
    plt.xlabel("연도 (Year)", fontsize=12)
    plt.ylabel(f"금액 (단위: {unit_str})", fontsize=12, fontweight="bold")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()

    _저장(fig, f"{회사명}_{title}")
    plt.show()


def 비율_그래프(비율결과: dict, title: str, 회사명: str):
    """비율결과: {비율이름(단위 포함 라벨): {연도: 값}}"""
    비율결과 = {k: v for k, v in 비율결과.items() if v}
    if not 비율결과:
        print("❌ 표시할 비율 데이터가 없습니다.")
        return

    fig = plt.figure(figsize=(11, 7))
    for 이름, 연도값 in 비율결과.items():
        연도목록 = sorted(연도값)
        값목록 = [연도값[y] for y in 연도목록]
        plt.plot(연도목록, 값목록, marker="o", linewidth=2, markersize=6, label=이름)
        for x, y in zip(연도목록, 값목록):
            plt.annotate(
                f"{y:,.2f}", (x, y),
                textcoords="offset points", xytext=(0, 10),
                ha="center", fontsize=8,
            )

    plt.title(f"[{회사명}] {title}", fontsize=16, fontweight="bold", pad=15)
    plt.xlabel("연도 (Year)", fontsize=12)
    plt.ylabel("비율 값 (% 또는 배, 범례 참조)", fontsize=12, fontweight="bold")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()

    _저장(fig, f"{회사명}_{title}")
    plt.show()
