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
ROOT_DIR = BASE_DIR.parents[2]
TABLE_DIR = BASE_DIR / "table"
FIGURE_DIR = BASE_DIR / "figure"

PROVINCIAL_FOOD_CSV = TABLE_DIR / "省级口粮长表数据.csv"
GROUP_CSV = TABLE_DIR / "省级口粮均值排序分组.csv"
NATIONAL_HISTORY_CSV = ROOT_DIR / "trend_prediction" / "table" / "historical_cleaned.csv"
NATIONAL_CALIBRATED_CSV = ROOT_DIR / "Forecast_adjustment" / "table" / "national_calibrated_forecast_long.csv"
FONT_PATH = ROOT_DIR / "Forecast_adjustment" / "assets" / "fonts" / "NotoSansCJKsc-Regular.otf"

FORECAST_START_YEAR = 2025
FORECAST_END_YEAR = 2035
PLOT_START_YEAR = 2013
PLOT_END_YEAR = 2035
MODEL_NAMES = ["arima", "linear_regression", "logistic_curve", "mlp"]


@dataclass(frozen=True)
class ForecastResult:
    model: str
    prediction: pd.DataFrame | None
    train_start_year: int | None
    train_end_year: int | None
    sample_count: int
    status: str
    detail: str


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


def normalized_years(years: np.ndarray, origin_year: float, scale: float) -> np.ndarray:
    return (np.asarray(years, dtype=float) - origin_year) / scale


def clip_predictions(values: np.ndarray) -> np.ndarray:
    return np.where(np.asarray(values, dtype=float) < 0, 0.0, values)


def linear_predict(years: np.ndarray, values: np.ndarray, forecast_years: np.ndarray) -> np.ndarray:
    coef = np.polyfit(years, values, deg=1)
    return np.polyval(coef, forecast_years)


def arima_like_predict(years: np.ndarray, values: np.ndarray, forecast_years: np.ndarray) -> np.ndarray:
    del years
    diffs = np.diff(values)
    if len(diffs) == 0:
        return np.repeat(values[-1], len(forecast_years))
    recent = diffs[-min(4, len(diffs)) :]
    drift = float(np.median(recent))
    long_drift = float(np.mean(diffs))
    drift = 0.7 * drift + 0.3 * long_drift
    damping = 0.86
    preds: list[float] = []
    current = float(values[-1])
    for step in range(len(forecast_years)):
        current = current + drift * (damping**step)
        preds.append(current)
    return np.asarray(preds, dtype=float)


def logistic_predict(years: np.ndarray, values: np.ndarray, forecast_years: np.ndarray) -> np.ndarray:
    y_min = float(np.min(values))
    y_max = float(np.max(values))
    y_range = y_max - y_min
    if y_range < 1e-6:
        return np.repeat(float(values[-1]), len(forecast_years))

    x = np.asarray(years, dtype=float)
    x_future = np.asarray(forecast_years, dtype=float)
    best_rmse = np.inf
    best_params: tuple[float, float, float, float] | None = None

    for lower_margin in (0.05, 0.15, 0.30, 0.50):
        for upper_margin in (0.05, 0.15, 0.30, 0.50):
            lower = max(0.0, y_min - lower_margin * y_range)
            upper = y_max + upper_margin * y_range
            if upper <= lower:
                continue
            z = (values - lower) / (upper - lower)
            z = np.clip(z, 1e-4, 1 - 1e-4)
            logit = np.log(z / (1 - z))
            slope, intercept = np.polyfit(x, logit, deg=1)
            fitted = lower + (upper - lower) / (1 + np.exp(-(slope * x + intercept)))
            rmse = float(np.sqrt(np.mean((fitted - values) ** 2)))
            if rmse < best_rmse:
                best_rmse = rmse
                best_params = (lower, upper, slope, intercept)

    if best_params is None:
        return np.repeat(float(values[-1]), len(forecast_years))
    lower, upper, slope, intercept = best_params
    return lower + (upper - lower) / (1 + np.exp(-(slope * x_future + intercept)))


def mlp_like_predict(years: np.ndarray, values: np.ndarray, forecast_years: np.ndarray) -> np.ndarray:
    origin_year = float(np.min(years))
    scale = float(np.max(years) - np.min(years)) or 1.0
    x = normalized_years(years, origin_year, scale)
    x_future = normalized_years(forecast_years, origin_year, scale)
    centers = np.linspace(0.0, 1.0, 6)
    widths = np.linspace(0.65, 1.15, 6)
    hidden = [np.ones_like(x), x]
    hidden_future = [np.ones_like(x_future), x_future]
    for center, width in zip(centers, widths):
        hidden.append(np.tanh((x - center) / width))
        hidden_future.append(np.tanh((x_future - center) / width))
    design = np.vstack(hidden).T
    future_design = np.vstack(hidden_future).T
    ridge = 1e-2
    weights = np.linalg.solve(design.T @ design + ridge * np.eye(design.shape[1]), design.T @ values)
    return future_design @ weights


def fit_and_predict_model(province: str, history_df: pd.DataFrame, model_name: str) -> ForecastResult:
    clean = history_df[["年份", "口粮（千克/人）"]].dropna().sort_values("年份").copy()
    sample_count = int(len(clean))
    train_start_year = int(clean["年份"].min()) if sample_count else None
    train_end_year = int(clean["年份"].max()) if sample_count else None
    if sample_count < 4:
        return ForecastResult(model_name, None, train_start_year, train_end_year, sample_count, "failed", "有效样本少于4。")

    years = clean["年份"].to_numpy(dtype=float)
    values = clean["口粮（千克/人）"].to_numpy(dtype=float)
    forecast_years = np.arange(FORECAST_START_YEAR, FORECAST_END_YEAR + 1, dtype=int)

    try:
        if model_name == "linear_regression":
            pred = linear_predict(years, values, forecast_years)
        elif model_name == "logistic_curve":
            pred = logistic_predict(years, values, forecast_years)
        elif model_name == "mlp":
            pred = mlp_like_predict(years, values, forecast_years)
        elif model_name == "arima":
            pred = arima_like_predict(years, values, forecast_years)
        else:
            raise ValueError(f"未知模型: {model_name}")
        pred = clip_predictions(pred)
        prediction = pd.DataFrame(
            {
                "省份": province,
                "year": forecast_years,
                "indicator": "口粮",
                "indicator_code": "grain_raw",
                "model": model_name,
                "value_kg_per_capita": pred,
                "train_start_year": train_start_year,
                "train_end_year": train_end_year,
                "sample_count": sample_count,
                "status": "success",
                "detail": "",
            }
        )
        return ForecastResult(model_name, prediction, train_start_year, train_end_year, sample_count, "success", "")
    except Exception as exc:
        return ForecastResult(model_name, None, train_start_year, train_end_year, sample_count, "failed", str(exc))


def build_provincial_forecast(food_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []
    for province, province_df in food_df.groupby("省份", sort=True):
        for model_name in MODEL_NAMES:
            result = fit_and_predict_model(province, province_df, model_name)
            if result.prediction is not None:
                frames.append(result.prediction)
            summary_rows.append(
                {
                    "省份": province,
                    "model": result.model,
                    "train_start_year": result.train_start_year,
                    "train_end_year": result.train_end_year,
                    "sample_count": result.sample_count,
                    "status": result.status,
                    "detail": result.detail,
                }
            )

    forecast_long = pd.concat(frames, ignore_index=True)
    forecast_wide = (
        forecast_long.pivot_table(index=["省份", "year"], columns="model", values="value_kg_per_capita", aggfunc="first")
        .reset_index()
        .sort_values(["省份", "year"])
    )
    forecast_wide["median_of_models"] = forecast_wide[MODEL_NAMES].median(axis=1, skipna=True)
    forecast_wide["indicator"] = "口粮"
    forecast_wide["indicator_code"] = "grain_raw"
    forecast_wide["raw_model_reference"] = "median_of_models"
    summary = pd.DataFrame(summary_rows).sort_values(["省份", "model"]).reset_index(drop=True)
    return forecast_long, forecast_wide, summary


def load_national_grain_raw_reference() -> pd.DataFrame:
    history = pd.read_csv(NATIONAL_HISTORY_CSV, encoding="utf-8-sig")
    calibrated = pd.read_csv(NATIONAL_CALIBRATED_CSV, encoding="utf-8-sig")
    history_part = (
        history[(history["indicator_code"] == "grain_raw") & history["year"].between(PLOT_START_YEAR, 2024)][
            ["year", "value_kg_per_capita"]
        ]
        .rename(columns={"value_kg_per_capita": "national_reference"})
        .copy()
    )
    forecast_part = (
        calibrated[(calibrated["indicator_code"] == "grain_raw") & calibrated["year"].between(FORECAST_START_YEAR, PLOT_END_YEAR)][
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
            .dropna(subset=["口粮（千克/人）"])
            .sort_values("年份")
        )
        forecast = forecast_wide[forecast_wide["省份"] == province].sort_values("year")
        mean_value = float(group_df.loc[group_df["省份"] == province, "均值（千克/人）"].iloc[0])

        ax.plot(
            history["年份"],
            history["口粮（千克/人）"],
            color="#2563eb",
            linewidth=1.9,
            marker="o",
            markersize=3.6,
            label="本省历史",
        )
        ax.plot(
            forecast["year"],
            forecast["median_of_models"],
            color="#d98f00",
            linewidth=2.0,
            marker="o",
            markersize=3.4,
            linestyle="--",
            label="本省预测中位数",
        )
        ax.plot(
            national_ref["year"],
            national_ref["national_reference"],
            color="#111827",
            linewidth=1.55,
            linestyle=":",
            label="全国口粮历史+校准",
        )

        ax.set_xlim(PLOT_START_YEAR, PLOT_END_YEAR)
        y_values = pd.concat(
            [
                history["口粮（千克/人）"],
                forecast["median_of_models"],
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
        f"31省口粮消费分省子图：第{group_no}组（按口粮均值降序，第{start}-{end}位；2025-2035为四模型中位数预测）",
        fontsize=14.5,
        y=0.995,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    out_path = FIGURE_DIR / f"31省口粮消费分省子图_第{group_no}组_{n}省.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    configure_chinese_font()
    for path in [PROVINCIAL_FOOD_CSV, GROUP_CSV, NATIONAL_HISTORY_CSV, NATIONAL_CALIBRATED_CSV]:
        require_file(path)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    food_df = pd.read_csv(PROVINCIAL_FOOD_CSV, encoding="utf-8-sig")
    food_df["年份"] = pd.to_numeric(food_df["年份"], errors="coerce").astype("Int64")
    food_df["口粮（千克/人）"] = pd.to_numeric(food_df["口粮（千克/人）"], errors="coerce")
    group_df = pd.read_csv(GROUP_CSV, encoding="utf-8-sig")

    forecast_long, forecast_wide, summary = build_provincial_forecast(food_df)
    forecast_long.to_csv(TABLE_DIR / "省级口粮四模型预测长表_2025-2035.csv", index=False, encoding="utf-8-sig")
    forecast_wide.to_csv(TABLE_DIR / "省级口粮四模型预测宽表_2025-2035.csv", index=False, encoding="utf-8-sig")
    forecast_wide[
        ["省份", "year", "indicator", "indicator_code", "raw_model_reference", "median_of_models"]
    ].to_csv(TABLE_DIR / "省级口粮四模型中位数预测_2025-2035.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(TABLE_DIR / "省级口粮四模型预测拟合状态_2025-2035.csv", index=False, encoding="utf-8-sig")

    national_ref = load_national_grain_raw_reference()
    national_ref.to_csv(TABLE_DIR / "全国口粮历史与校准参考线_2013-2035.csv", index=False, encoding="utf-8-sig")

    for group_no, size in [(1, 10), (2, 10), (3, 11)]:
        lo, hi = (1, 10) if group_no == 1 else ((11, 20) if group_no == 2 else (21, 31))
        sub_group = group_df[(group_df["排序"] >= lo) & (group_df["排序"] <= hi)].sort_values("排序")
        out_path = plot_group(food_df, forecast_wide, sub_group, national_ref, group_no)
        print(out_path)

    print(TABLE_DIR / "省级口粮四模型预测长表_2025-2035.csv")
    print(TABLE_DIR / "省级口粮四模型预测宽表_2025-2035.csv")
    print(TABLE_DIR / "省级口粮四模型中位数预测_2025-2035.csv")
    print(TABLE_DIR / "省级口粮四模型预测拟合状态_2025-2035.csv")
    print(TABLE_DIR / "全国口粮历史与校准参考线_2013-2035.csv")


if __name__ == "__main__":
    main()
