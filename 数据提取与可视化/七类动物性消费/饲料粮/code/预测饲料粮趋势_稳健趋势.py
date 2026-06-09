from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BASE_DIR.parents[3]
TABLE_DIR = BASE_DIR / "table"
FIGURE_DIR = BASE_DIR / "figure"

PROVINCIAL_FEED_CSV = TABLE_DIR / "省级饲料粮长表数据.csv"
GROUP_CSV = TABLE_DIR / "省级饲料粮均值排序分组.csv"
NATIONAL_HISTORY_CSV = ROOT_DIR / "trend_prediction" / "table" / "historical_cleaned.csv"
NATIONAL_CALIBRATED_CSV = ROOT_DIR / "Forecast_adjustment" / "table" / "national_calibrated_forecast_long.csv"
FONT_PATH = ROOT_DIR / "Forecast_adjustment" / "assets" / "fonts" / "NotoSansCJKsc-Regular.otf"

FORECAST_START_YEAR = 2025
FORECAST_END_YEAR = 2035
PLOT_START_YEAR = 2013
PLOT_END_YEAR = 2035
MODEL_NAMES = ["robust_linear", "exponential_decline", "local_trend"]


@dataclass(frozen=True)
class TrendState:
    overall_slope: float
    recent_slope: float
    selected_slope: float
    direction: str


def configure_chinese_font() -> None:
    if FONT_PATH.exists():
        font_manager.fontManager.addfont(str(FONT_PATH))
        font_name = font_manager.FontProperties(fname=str(FONT_PATH)).get_name()
        plt.rcParams["font.family"] = [font_name]
        plt.rcParams["font.sans-serif"] = [font_name, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"缺少输入文件: {path}")


def pairwise_median_slope(years: np.ndarray, values: np.ndarray) -> float:
    slopes: list[float] = []
    for i in range(len(years)):
        for j in range(i + 1, len(years)):
            dx = years[j] - years[i]
            if dx:
                slopes.append((values[j] - values[i]) / dx)
    if not slopes:
        return 0.0
    return float(np.median(slopes))


def recent_median_slope(years: np.ndarray, values: np.ndarray, max_intervals: int = 5) -> float:
    if len(values) < 2:
        return 0.0
    years_tail = years[-(max_intervals + 1) :]
    values_tail = values[-(max_intervals + 1) :]
    slopes = np.diff(values_tail) / np.diff(years_tail)
    return float(np.median(slopes))


def infer_trend(years: np.ndarray, values: np.ndarray) -> TrendState:
    overall = pairwise_median_slope(years, values)
    recent = recent_median_slope(years, values)
    if len(values) >= 4:
        endpoint_recent = float((values[-1] - values[-4]) / (years[-1] - years[-4]))
        if endpoint_recent < 0:
            recent = min(recent, endpoint_recent)
    tail = values[-min(5, len(values)) :]
    peak_idx = int(np.argmax(values))
    peak_year = float(years[peak_idx])
    peak_value = float(values[peak_idx])
    post_peak_slope = 0.0
    peak_drop_ratio = 0.0
    if years[-1] > peak_year:
        post_peak_slope = float((values[-1] - peak_value) / (years[-1] - peak_year))
        peak_drop_ratio = float((peak_value - values[-1]) / peak_value) if peak_value else 0.0
    score = 0
    if overall < -0.25:
        score -= 1
    elif overall > 0.25:
        score += 1
    if recent < -0.25:
        score -= 2
    elif recent > 0.25:
        score += 1
    if len(tail) >= 3 and values[-1] < values[-3]:
        score -= 1
    if len(tail) >= 4 and values[-1] <= np.max(tail) - 5.0:
        score -= 1
    if years[-1] - peak_year <= 5 and peak_drop_ratio >= 0.08 and post_peak_slope < -1.0:
        score -= 3

    if score <= -1:
        direction = "declining"
        slope_candidates = [0.35 * overall + 0.65 * recent]
        if post_peak_slope < 0 and peak_drop_ratio >= 0.08:
            slope_candidates.append(0.55 * post_peak_slope + 0.30 * recent + 0.15 * overall)
        selected = min(-0.15, float(np.median(slope_candidates)))
    elif score >= 2:
        direction = "rising"
        selected = max(0.0, 0.45 * overall + 0.55 * recent)
    else:
        direction = "platform"
        selected = 0.30 * overall + 0.70 * recent

    selected = float(np.clip(selected, -8.0, 3.0))
    return TrendState(overall_slope=overall, recent_slope=recent, selected_slope=selected, direction=direction)


def clip_predictions(values: np.ndarray) -> np.ndarray:
    return np.where(np.asarray(values, dtype=float) < 0, 0.0, values)


def robust_linear_predict(last_value: float, trend: TrendState, steps: np.ndarray) -> np.ndarray:
    if trend.direction == "declining":
        slope = min(-0.15, trend.selected_slope)
    elif trend.direction == "rising":
        slope = min(1.5, trend.selected_slope)
    else:
        slope = float(np.clip(trend.selected_slope, -1.2, 0.8))
    return last_value + slope * steps


def local_trend_predict(last_value: float, trend: TrendState, steps: np.ndarray) -> np.ndarray:
    if trend.direction == "declining":
        slope = min(-0.15, trend.recent_slope, trend.selected_slope)
    elif trend.direction == "rising":
        slope = min(1.2, trend.recent_slope)
    else:
        slope = float(np.clip(trend.recent_slope, -0.8, 0.5))
    slope = float(np.clip(slope, -8.0, 2.0))
    cumulative = np.cumsum(0.86 ** (steps - 1))
    return last_value + slope * cumulative


def exponential_decline_predict(last_value: float, values: np.ndarray, trend: TrendState, steps: np.ndarray) -> np.ndarray:
    if trend.direction == "declining":
        recent_floor = float(np.nanmin(values[-min(5, len(values)) :]))
        floor = max(0.0, min(last_value * 0.72, recent_floor * 0.82))
        distance = max(last_value - floor, 1.0)
        rate = float(np.clip(abs(trend.selected_slope) / distance, 0.025, 0.18))
        return floor + (last_value - floor) * np.exp(-rate * steps)

    if trend.direction == "rising":
        ceiling = max(last_value * 1.04, float(np.nanmax(values[-min(5, len(values)) :])))
        rate = 0.10
        return ceiling - (ceiling - last_value) * np.exp(-rate * steps)

    target = 0.5 * last_value + 0.5 * float(np.nanmedian(values[-min(5, len(values)) :]))
    rate = 0.10
    return target + (last_value - target) * np.exp(-rate * steps)


def fit_and_predict_province(province: str, history_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    clean = history_df[["年份", "饲料粮折算值（千克/人）"]].dropna().sort_values("年份").copy()
    if len(clean) < 4:
        raise ValueError(f"{province} 有效样本少于4，无法预测。")

    years = clean["年份"].to_numpy(dtype=float)
    values = clean["饲料粮折算值（千克/人）"].to_numpy(dtype=float)
    trend = infer_trend(years, values)
    forecast_years = np.arange(FORECAST_START_YEAR, FORECAST_END_YEAR + 1, dtype=int)
    steps = forecast_years - int(years[-1])
    last_value = float(values[-1])

    predictions = {
        "robust_linear": robust_linear_predict(last_value, trend, steps),
        "exponential_decline": exponential_decline_predict(last_value, values, trend, steps),
        "local_trend": local_trend_predict(last_value, trend, steps),
    }
    rows: list[pd.DataFrame] = []
    for model, values_pred in predictions.items():
        rows.append(
            pd.DataFrame(
                {
                    "省份": province,
                    "year": forecast_years,
                    "indicator": "饲料粮",
                    "indicator_code": "feed_grain_pc_kg",
                    "model": model,
                    "value_kg_per_capita": clip_predictions(values_pred),
                }
            )
        )

    summary = {
        "省份": province,
        "train_start_year": int(years[0]),
        "train_end_year": int(years[-1]),
        "sample_count": int(len(clean)),
        "overall_slope": trend.overall_slope,
        "recent_slope": trend.recent_slope,
        "selected_slope": trend.selected_slope,
        "trend_direction": trend.direction,
        "last_observed_value": last_value,
    }
    return pd.concat(rows, ignore_index=True), summary


def build_forecast(food_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []
    for province, province_df in food_df.groupby("省份", sort=True):
        forecast, summary = fit_and_predict_province(province, province_df)
        frames.append(forecast)
        summary_rows.append(summary)

    long_df = pd.concat(frames, ignore_index=True)
    wide_df = (
        long_df.pivot_table(index=["省份", "year"], columns="model", values="value_kg_per_capita", aggfunc="first")
        .reset_index()
        .sort_values(["省份", "year"])
    )
    wide_df["median_robust_trend"] = wide_df[MODEL_NAMES].median(axis=1, skipna=True)
    wide_df["indicator"] = "饲料粮"
    wide_df["indicator_code"] = "feed_grain_pc_kg"
    wide_df["forecast_method"] = "median_of_robust_provincial_trend_models"
    summary_df = pd.DataFrame(summary_rows).sort_values("省份").reset_index(drop=True)
    return long_df, wide_df, summary_df


def load_national_feed_grain_pc_kg_reference() -> pd.DataFrame:
    history = pd.read_csv(NATIONAL_HISTORY_CSV, encoding="utf-8-sig")
    calibrated = pd.read_csv(NATIONAL_CALIBRATED_CSV, encoding="utf-8-sig")
    history_part = (
        history[(history["indicator_code"] == "feed_grain_pc_kg") & history["year"].between(PLOT_START_YEAR, 2024)][
            ["year", "value_kg_per_capita"]
        ]
        .rename(columns={"value_kg_per_capita": "national_reference"})
        .copy()
    )
    forecast_part = (
        calibrated[(calibrated["indicator_code"] == "feed_grain_pc_kg") & calibrated["year"].between(FORECAST_START_YEAR, PLOT_END_YEAR)][
            ["year", "calibrated_value"]
        ]
        .rename(columns={"calibrated_value": "national_reference"})
        .copy()
    )
    reference = pd.concat([history_part, forecast_part], ignore_index=True).sort_values("year")
    reference["series"] = np.where(reference["year"] <= 2024, "全国历史", "全国校准主序列")
    return reference


def plot_group(
    food_df: pd.DataFrame,
    forecast_wide: pd.DataFrame,
    group_df: pd.DataFrame,
    national_ref: pd.DataFrame,
    group_no: int,
) -> Path:
    provinces = group_df["省份"].tolist()
    n = len(provinces)
    ncols = 2 if n <= 10 else 3
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 3.0 * nrows), sharex=False)
    axes = list(axes.flatten()) if hasattr(axes, "flatten") else [axes]

    for ax, province in zip(axes, provinces):
        history = (
            food_df[(food_df["省份"] == province) & food_df["年份"].between(PLOT_START_YEAR, 2024)]
            .dropna(subset=["饲料粮折算值（千克/人）"])
            .sort_values("年份")
        )
        forecast = forecast_wide[forecast_wide["省份"] == province].sort_values("year")
        mean_value = float(group_df.loc[group_df["省份"] == province, "均值（千克/人）"].iloc[0])

        ax.plot(
            history["年份"],
            history["饲料粮折算值（千克/人）"],
            color="#dc2626",
            linewidth=1.9,
            marker="o",
            markersize=3.6,
            label="本省历史",
        )
        ax.plot(
            forecast["year"],
            forecast["median_robust_trend"],
            color="#d98f00",
            linewidth=2.0,
            marker="o",
            markersize=3.4,
            linestyle="--",
            label="本省稳健趋势预测",
        )
        ax.plot(
            national_ref["year"],
            national_ref["national_reference"],
            color="#111827",
            linewidth=1.55,
            linestyle=":",
            label="全国饲料粮历史+校准",
        )

        ax.set_xlim(PLOT_START_YEAR, PLOT_END_YEAR)
        y_values = pd.concat(
            [
                history["饲料粮折算值（千克/人）"],
                forecast["median_robust_trend"],
                national_ref["national_reference"],
            ],
            ignore_index=True,
        ).dropna()
        if not y_values.empty:
            ymin = float(y_values.min())
            ymax = float(y_values.max())
            pad = (ymax - ymin) * 0.12 if ymax > ymin else 5.0
            ax.set_ylim(max(0.0, ymin - pad), ymax + pad)

        ax.set_title(f"{province}｜历史均值 {mean_value:.1f}", fontsize=10.5, pad=7)
        ax.grid(True, axis="y", linestyle="--", linewidth=0.55, alpha=0.35)
        ax.grid(True, axis="x", linestyle=":", linewidth=0.45, alpha=0.2)
        ax.set_xticks([2013, 2020, 2025, 2030, 2035])
        ax.tick_params(axis="both", labelsize=8.5)
        ax.set_xlabel("年份", fontsize=9)
        ax.set_ylabel("kg/人", fontsize=9)
        ax.legend(loc="best", fontsize=7.3, frameon=False)

    for ax in axes[n:]:
        ax.axis("off")

    start = (group_no - 1) * 10 + 1
    end = start + n - 1
    fig.suptitle(
        f"31省饲料粮消费分省子图：第{group_no}组（按饲料粮均值降序，第{start}-{end}位；2025-2035为省级稳健趋势预测）",
        fontsize=14.5,
        y=0.995,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    out_path = FIGURE_DIR / f"31省饲料粮消费分省子图_第{group_no}组_{n}省.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    configure_chinese_font()
    for path in [PROVINCIAL_FEED_CSV, GROUP_CSV, NATIONAL_HISTORY_CSV, NATIONAL_CALIBRATED_CSV]:
        require_file(path)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    food_df = pd.read_csv(PROVINCIAL_FEED_CSV, encoding="utf-8-sig")
    food_df["年份"] = pd.to_numeric(food_df["年份"], errors="coerce").astype("Int64")
    food_df["饲料粮折算值（千克/人）"] = pd.to_numeric(food_df["饲料粮折算值（千克/人）"], errors="coerce")
    group_df = pd.read_csv(GROUP_CSV, encoding="utf-8-sig")

    forecast_long, forecast_wide, summary = build_forecast(food_df)
    forecast_long.to_csv(TABLE_DIR / "省级饲料粮稳健趋势预测模型分项_2025-2035.csv", index=False, encoding="utf-8-sig")
    forecast_wide.to_csv(TABLE_DIR / "省级饲料粮稳健趋势预测宽表_2025-2035.csv", index=False, encoding="utf-8-sig")
    forecast_wide[
        ["省份", "year", "indicator", "indicator_code", "forecast_method", "median_robust_trend"]
    ].to_csv(TABLE_DIR / "省级饲料粮稳健趋势预测_2025-2035.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(TABLE_DIR / "省级饲料粮稳健趋势预测诊断_2025-2035.csv", index=False, encoding="utf-8-sig")

    national_ref = load_national_feed_grain_pc_kg_reference()
    national_ref.to_csv(TABLE_DIR / "全国饲料粮历史与校准参考线_2013-2035.csv", index=False, encoding="utf-8-sig")

    for group_no, size in [(1, 10), (2, 10), (3, 11)]:
        lo, hi = (1, 10) if group_no == 1 else ((11, 20) if group_no == 2 else (21, 31))
        sub_group = group_df[(group_df["排序"] >= lo) & (group_df["排序"] <= hi)].sort_values("排序")
        print(plot_group(food_df, forecast_wide, sub_group, national_ref, group_no))

    print(TABLE_DIR / "省级饲料粮稳健趋势预测_2025-2035.csv")
    print(TABLE_DIR / "省级饲料粮稳健趋势预测模型分项_2025-2035.csv")
    print(TABLE_DIR / "省级饲料粮稳健趋势预测宽表_2025-2035.csv")
    print(TABLE_DIR / "省级饲料粮稳健趋势预测诊断_2025-2035.csv")


if __name__ == "__main__":
    main()
