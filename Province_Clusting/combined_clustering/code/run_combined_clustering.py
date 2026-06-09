from __future__ import annotations

from functools import reduce
import itertools
import json
from math import comb, sqrt
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import colors as matplotlib_colors
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch, Polygon
import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT_DIR.parent
GRAIN_DIR = ROOT_DIR.parents[1]
TASK_DIR = Path(__file__).resolve().parents[1]
TABLE_DIR = TASK_DIR / "table"
FIGURE_DIR = TASK_DIR / "figure"
sys.path.insert(0, str(ROOT_DIR / "common"))

from clustering_utils import (  # noqa: E402
    build_series_features,
    calinski_harabasz_score_np,
    configure_chinese_font,
    davies_bouldin_score_np,
    ensure_dirs,
    fit_simple_kmeans,
    plot_center_heatmap,
    plot_cluster_counts,
    plot_pca_scatter,
    silhouette_score_np,
    standardize_values,
)


YEAR_START = 2015
YEAR_END = 2024
EXPECTED_PROVINCES = 31
EXPECTED_PANEL_ROWS = EXPECTED_PROVINCES * (YEAR_END - YEAR_START + 1)
N_CLUSTERS = 5
RANDOM_STATE = 42
N_INIT = 80
MAX_ITER = 300
GRAIN_TREND_THRESHOLD = 0.5

POPULATION_CSV = GRAIN_DIR / "宏观数据收集（CSV编码）" / "人口数据（省级）.csv"
ECONOMY_CSV = GRAIN_DIR / "宏观数据收集（CSV编码）" / "经济数据（省级）.csv"
FOOD_GRAIN_CSV = PROJECT_DIR / "数据提取与可视化" / "口粮" / "table" / "省级口粮长表数据.csv"
FEED_GRAIN_CSV = (
    PROJECT_DIR
    / "数据提取与可视化"
    / "七类动物性消费"
    / "饲料粮"
    / "table"
    / "省级饲料粮长表数据.csv"
)
AREA_CSV = ROOT_DIR / "table" / "省级行政区土地面积.csv"
GEOJSON_PATH = ROOT_DIR / "common" / "china_provinces_online.json"

PROVINCE_COLS = ["省份", "行政区划代码"]

DOMAIN_COLS = {
    "人口域": [
        "log1p人口密度_最新年值",
        "log1p人口密度_线性趋势斜率",
        "城镇化率_最新年值",
        "城镇化率_线性趋势斜率",
        "老龄人口占比_最新年值",
        "老龄人口占比_线性趋势斜率",
        "少儿人口占比_最新年值",
        "少儿人口占比_线性趋势斜率",
        "平均家庭规模_最新年值",
        "平均家庭规模_线性趋势斜率",
    ],
    "经济域": [
        "log1p人均可支配收入_最新年值",
        "log1p人均可支配收入_线性趋势斜率",
        "log1p人均消费支出_最新年值",
        "log1p人均消费支出_线性趋势斜率",
    ],
    "口粮域": [
        "口粮_最新年值",
        "口粮_线性趋势斜率",
        "口粮_变异系数",
    ],
    "饲料粮域": [
        "饲料粮_最新年值",
        "饲料粮_线性趋势斜率",
        "饲料粮_变异系数",
    ],
}

DOMAIN_ORDER = list(DOMAIN_COLS)
CORE_COLS = [col for domain in DOMAIN_ORDER for col in DOMAIN_COLS[domain]]

EXPERIMENTS = [
    {
        "id": "M0",
        "name": "四域等权主实验",
        "domains": DOMAIN_ORDER,
        "direct_feature_equal": False,
        "weight_rule": "四域重新等权，各域约25%",
    },
    {
        "id": "C1",
        "name": "所有特征直接等权",
        "domains": DOMAIN_ORDER,
        "direct_feature_equal": True,
        "weight_rule": "仅逐列z-score，不做域权重校正",
    },
    {
        "id": "C2",
        "name": "移除人口域",
        "domains": ["经济域", "口粮域", "饲料粮域"],
        "direct_feature_equal": False,
        "weight_rule": "剩余三域重新等权，各域约33.3%",
    },
    {
        "id": "C3",
        "name": "移除经济域",
        "domains": ["人口域", "口粮域", "饲料粮域"],
        "direct_feature_equal": False,
        "weight_rule": "剩余三域重新等权，各域约33.3%",
    },
    {
        "id": "C4",
        "name": "移除口粮域",
        "domains": ["人口域", "经济域", "饲料粮域"],
        "direct_feature_equal": False,
        "weight_rule": "剩余三域重新等权，各域约33.3%",
    },
    {
        "id": "C5",
        "name": "移除饲料粮域",
        "domains": ["人口域", "经济域", "口粮域"],
        "direct_feature_equal": False,
        "weight_rule": "剩余三域重新等权，各域约33.3%",
    },
]

COLOR_PALETTE = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#B279A2"]


def require_columns(df: pd.DataFrame, required: list[str], dataset_name: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{dataset_name} 缺少字段: {missing}")


def normalize_admin_code(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if values.isna().any():
        raise ValueError("行政区划代码存在无法解析的值。")
    return values.astype(int)


def standardize_admin_codes_by_area(
    df: pd.DataFrame,
    area: pd.DataFrame,
    dataset_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = df.copy()
    out["行政区划代码"] = normalize_admin_code(out["行政区划代码"])
    area_codes = area.set_index("省份")["行政区划代码"]
    standard_codes = out["省份"].map(area_codes)
    if standard_codes.isna().any():
        missing = sorted(out.loc[standard_codes.isna(), "省份"].unique().tolist())
        raise ValueError(f"{dataset_name} 存在无法匹配面积表的省份: {missing}")
    standard_codes = standard_codes.astype(int)
    corrections = out.loc[out["行政区划代码"] != standard_codes, ["省份", "行政区划代码"]].drop_duplicates()
    corrections = corrections.rename(columns={"行政区划代码": "原始行政区划代码"})
    corrections["标准行政区划代码"] = corrections["省份"].map(area_codes).astype(int)
    corrections.insert(0, "数据集", dataset_name)
    out["行政区划代码"] = standard_codes
    return out, corrections.reset_index(drop=True)


def assert_complete_panel(
    df: pd.DataFrame,
    dataset_name: str,
    value_cols: list[str],
) -> None:
    if df["省份"].nunique() != EXPECTED_PROVINCES:
        raise ValueError(f"{dataset_name} 省份数量不是 {EXPECTED_PROVINCES}: {df['省份'].nunique()}")
    if len(df) != EXPECTED_PANEL_ROWS:
        raise ValueError(f"{dataset_name} 记录数不是 {EXPECTED_PANEL_ROWS}: {len(df)}")
    if df.duplicated(["省份", "年份"]).any():
        raise ValueError(f"{dataset_name} 存在重复的省份-年份记录。")
    missing = df[value_cols].isna().sum()
    if (missing > 0).any():
        raise ValueError(f"{dataset_name} 存在缺失值: {missing[missing > 0].to_dict()}")
    expected_years = set(range(YEAR_START, YEAR_END + 1))
    invalid = {
        province: sorted(expected_years - set(group["年份"]))
        for province, group in df.groupby("省份")
        if set(group["年份"]) != expected_years
    }
    if invalid:
        raise ValueError(f"{dataset_name} 年份覆盖不完整: {invalid}")


def load_area_table() -> pd.DataFrame:
    area = pd.read_csv(AREA_CSV, encoding="utf-8-sig")
    required = PROVINCE_COLS + ["土地调查总面积（公顷）", "土地调查总面积（平方公里）", "调查年份"]
    require_columns(area, required, "省级行政区土地面积表")
    area["行政区划代码"] = normalize_admin_code(area["行政区划代码"])
    for col in ["土地调查总面积（公顷）", "土地调查总面积（平方公里）", "调查年份"]:
        area[col] = pd.to_numeric(area[col], errors="coerce")
    if len(area) != EXPECTED_PROVINCES:
        raise ValueError(f"省级行政区土地面积表记录数不是 {EXPECTED_PROVINCES}: {len(area)}")
    if area["省份"].nunique() != EXPECTED_PROVINCES or area["行政区划代码"].nunique() != EXPECTED_PROVINCES:
        raise ValueError("省级行政区土地面积表中的省份或行政区划代码不唯一。")
    if area[["土地调查总面积（公顷）", "土地调查总面积（平方公里）"]].isna().any().any():
        raise ValueError("省级行政区土地面积表存在缺失面积。")
    if (area[["土地调查总面积（公顷）", "土地调查总面积（平方公里）"]] <= 0).any().any():
        raise ValueError("省级行政区土地面积表存在非正面积。")
    converted = area["土地调查总面积（公顷）"] / 100
    if not np.allclose(converted, area["土地调查总面积（平方公里）"], rtol=0, atol=1e-8):
        raise ValueError("省级行政区土地面积表的公顷与平方公里换算不一致。")
    return area.sort_values("省份").reset_index(drop=True)


def load_population_panel(area: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(POPULATION_CSV, encoding="utf-8-sig")
    df = raw.rename(columns={"Unnamed: 0": "省份", "Unnamed: 1": "年份"}).copy()
    value_cols = ["总人口", "城镇人口", "0-14岁", "65岁及以上", "平均家庭规模"]
    require_columns(df, PROVINCE_COLS + ["年份"] + value_cols, "人口数据")
    df["年份"] = pd.to_numeric(df["年份"], errors="coerce")
    df = df[df["年份"].notna()].copy()
    df["年份"] = df["年份"].astype(int)
    df = df[df["年份"].between(YEAR_START, YEAR_END)].copy()
    df, corrections = standardize_admin_codes_by_area(df, area, "人口数据")
    for col in value_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[PROVINCE_COLS + ["年份"] + value_cols].sort_values(["省份", "年份"])
    assert_complete_panel(df, "人口数据", value_cols)

    area_cols = ["省份", "土地调查总面积（平方公里）"]
    clean = df.merge(area[area_cols], on="省份", how="left", validate="many_to_one")
    if clean["土地调查总面积（平方公里）"].isna().any():
        missing = clean.loc[clean["土地调查总面积（平方公里）"].isna(), "省份"].unique().tolist()
        raise ValueError(f"人口数据无法匹配土地面积: {missing}")
    if set(df["省份"]) != set(area["省份"]):
        raise ValueError("面积表与人口表的省份集合不完全一致。")

    clean["人口密度（人/平方公里）"] = clean["总人口"] * 10000 / clean["土地调查总面积（平方公里）"]
    clean["log1p人口密度"] = np.log1p(clean["人口密度（人/平方公里）"])
    clean["城镇化率"] = clean["城镇人口"] / clean["总人口"]
    clean["老龄人口占比"] = clean["65岁及以上"] / clean["总人口"]
    clean["少儿人口占比"] = clean["0-14岁"] / clean["总人口"]
    derived = ["人口密度（人/平方公里）", "log1p人口密度", "城镇化率", "老龄人口占比", "少儿人口占比"]
    if not np.isfinite(clean[derived].to_numpy(dtype=float)).all():
        raise ValueError("人口域派生指标存在缺失值或无穷值。")
    return clean.reset_index(drop=True), corrections


def load_economy_panel(area: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(ECONOMY_CSV, encoding="utf-8-sig")
    df = raw.rename(
        columns={
            "Unnamed: 0": "省份",
            "Unnamed: 1": "年份",
            "Unnamed: 2": "行政区划代码",
            "人均可支配收入": "人均可支配收入_地区总计",
            "人均消费支出": "人均消费支出_地区总计",
        }
    ).copy()
    value_cols = ["人均可支配收入_地区总计", "人均消费支出_地区总计"]
    require_columns(df, PROVINCE_COLS + ["年份"] + value_cols, "经济数据")
    df["年份"] = pd.to_numeric(df["年份"], errors="coerce")
    df = df[df["年份"].notna()].copy()
    df["年份"] = df["年份"].astype(int)
    df = df[df["年份"].between(YEAR_START, YEAR_END)].copy()
    df, corrections = standardize_admin_codes_by_area(df, area, "经济数据")
    for col in value_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    clean = df[PROVINCE_COLS + ["年份"] + value_cols].sort_values(["省份", "年份"])
    assert_complete_panel(clean, "经济数据", value_cols)
    if (clean[value_cols] < 0).any().any():
        raise ValueError("经济数据存在负数，无法执行 log1p 转换。")
    clean["log1p人均可支配收入"] = np.log1p(clean["人均可支配收入_地区总计"])
    clean["log1p人均消费支出"] = np.log1p(clean["人均消费支出_地区总计"])
    return clean.reset_index(drop=True), corrections


def load_grain_panel(
    path: Path,
    value_col: str,
    dataset_name: str,
    area: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(path, encoding="utf-8-sig")
    require_columns(df, PROVINCE_COLS + ["年份", value_col], dataset_name)
    df["年份"] = pd.to_numeric(df["年份"], errors="coerce")
    df = df[df["年份"].notna()].copy()
    df["年份"] = df["年份"].astype(int)
    df = df[df["年份"].between(YEAR_START, YEAR_END)].copy()
    df, corrections = standardize_admin_codes_by_area(df, area, dataset_name)
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    clean = df[PROVINCE_COLS + ["年份", value_col]].sort_values(["省份", "年份"])
    assert_complete_panel(clean, dataset_name, [value_col])
    return clean.reset_index(drop=True), corrections


def extract_level_slope(panel: pd.DataFrame, value_col: str, prefix: str) -> pd.DataFrame:
    features = build_series_features(panel, value_col, prefix=f"{prefix}_", include_std=False)
    return features[PROVINCE_COLS + [f"{prefix}_最新年值", f"{prefix}_线性趋势斜率"]]


def extract_level_slope_cv(panel: pd.DataFrame, value_col: str, prefix: str) -> pd.DataFrame:
    features = build_series_features(panel, value_col, prefix=f"{prefix}_", include_std=True)
    return features[
        PROVINCE_COLS
        + [
            f"{prefix}_最新年值",
            f"{prefix}_线性趋势斜率",
            f"{prefix}_变异系数",
        ]
    ]


def build_core_features(
    population: pd.DataFrame,
    economy: pd.DataFrame,
    food_grain: pd.DataFrame,
    feed_grain: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    parts = [
        extract_level_slope(population, "log1p人口密度", "log1p人口密度"),
        extract_level_slope(population, "城镇化率", "城镇化率"),
        extract_level_slope(population, "老龄人口占比", "老龄人口占比"),
        extract_level_slope(population, "少儿人口占比", "少儿人口占比"),
        extract_level_slope(population, "平均家庭规模", "平均家庭规模"),
        extract_level_slope(economy, "log1p人均可支配收入", "log1p人均可支配收入"),
        extract_level_slope(economy, "log1p人均消费支出", "log1p人均消费支出"),
        extract_level_slope_cv(food_grain, "口粮（千克/人）", "口粮"),
        extract_level_slope_cv(feed_grain, "饲料粮折算值（千克/人）", "饲料粮"),
    ]
    feature_df = reduce(lambda left, right: left.merge(right, on=PROVINCE_COLS, how="inner"), parts)
    feature_df = feature_df[PROVINCE_COLS + CORE_COLS].sort_values("省份").reset_index(drop=True)
    if len(feature_df) != EXPECTED_PROVINCES:
        raise ValueError(f"联合聚类核心特征表省份数量不是 {EXPECTED_PROVINCES}: {len(feature_df)}")
    if not np.isfinite(feature_df[CORE_COLS].to_numpy(dtype=float)).all():
        raise ValueError("联合聚类核心特征存在缺失值或无穷值。")

    population_latest = population[population["年份"] == YEAR_END][
        PROVINCE_COLS + ["人口密度（人/平方公里）", "城镇化率", "老龄人口占比", "少儿人口占比", "平均家庭规模"]
    ]
    economy_latest = economy[economy["年份"] == YEAR_END][
        PROVINCE_COLS + ["人均可支配收入_地区总计", "人均消费支出_地区总计"]
    ]
    food_latest = food_grain[food_grain["年份"] == YEAR_END][PROVINCE_COLS + ["口粮（千克/人）"]]
    feed_latest = feed_grain[feed_grain["年份"] == YEAR_END][PROVINCE_COLS + ["饲料粮折算值（千克/人）"]]
    explanation_df = reduce(
        lambda left, right: left.merge(right, on=PROVINCE_COLS, how="inner"),
        [population_latest, economy_latest, food_latest, feed_latest],
    )
    explanation_df = explanation_df.merge(
        feature_df[
            PROVINCE_COLS
            + [
                "口粮_线性趋势斜率",
                "口粮_变异系数",
                "饲料粮_线性趋势斜率",
                "饲料粮_变异系数",
            ]
        ],
        on=PROVINCE_COLS,
        how="inner",
    )
    return feature_df, explanation_df.sort_values("省份").reset_index(drop=True)


def build_experiment_matrix(
    scaled_df: pd.DataFrame,
    domains: list[str],
    direct_feature_equal: bool,
) -> tuple[np.ndarray, list[str]]:
    selected_cols = [col for domain in domains for col in DOMAIN_COLS[domain]]
    if direct_feature_equal:
        return scaled_df[selected_cols].to_numpy(dtype=float), selected_cols
    blocks = []
    for domain in domains:
        cols = DOMAIN_COLS[domain]
        blocks.append(scaled_df[cols].to_numpy(dtype=float) / sqrt(len(cols)))
    return np.concatenate(blocks, axis=1), selected_cols


def adjusted_rand_index(labels_a: np.ndarray, labels_b: np.ndarray) -> float:
    table = pd.crosstab(pd.Series(labels_a, name="a"), pd.Series(labels_b, name="b"))
    sum_comb_cells = sum(comb(int(value), 2) for value in table.to_numpy().ravel())
    sum_comb_rows = sum(comb(int(value), 2) for value in table.sum(axis=1))
    sum_comb_cols = sum(comb(int(value), 2) for value in table.sum(axis=0))
    total_pairs = comb(len(labels_a), 2)
    if total_pairs == 0:
        return 1.0
    expected = sum_comb_rows * sum_comb_cols / total_pairs
    maximum = 0.5 * (sum_comb_rows + sum_comb_cols)
    denominator = maximum - expected
    if abs(denominator) < 1e-12:
        return 1.0
    return float((sum_comb_cells - expected) / denominator)


def align_labels_to_baseline(labels: np.ndarray, baseline: np.ndarray) -> tuple[np.ndarray, dict[int, int]]:
    best_overlap = -1
    best_mapping: dict[int, int] | None = None
    unique = sorted(np.unique(labels).tolist())
    for permutation in itertools.permutations(range(N_CLUSTERS)):
        mapping = dict(zip(unique, permutation, strict=True))
        mapped = np.array([mapping[int(label)] for label in labels], dtype=int)
        overlap = int((mapped == baseline).sum())
        if overlap > best_overlap:
            best_overlap = overlap
            best_mapping = mapping
    if best_mapping is None:
        raise ValueError("对照实验簇编号未能与 M0 对齐。")
    aligned = np.array([best_mapping[int(label)] for label in labels], dtype=int)
    return aligned, best_mapping


def fit_experiments(scaled_df: pd.DataFrame) -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    baseline_labels: np.ndarray | None = None
    for spec in EXPERIMENTS:
        matrix, selected_cols = build_experiment_matrix(
            scaled_df,
            spec["domains"],
            bool(spec["direct_feature_equal"]),
        )
        model = fit_simple_kmeans(
            matrix,
            n_clusters=N_CLUSTERS,
            random_state=RANDOM_STATE,
            n_init=N_INIT,
            max_iter=MAX_ITER,
        )
        labels = model.labels
        if len(np.unique(labels)) != N_CLUSTERS:
            raise ValueError(f"{spec['id']} 出现空簇。")
        if baseline_labels is None:
            aligned = labels.copy()
            mapping = {cluster: cluster for cluster in range(N_CLUSTERS)}
            baseline_labels = labels.copy()
        else:
            aligned, mapping = align_labels_to_baseline(labels, baseline_labels)
        total_energy = float(np.sum((matrix - matrix.mean(axis=0)) ** 2))
        results[str(spec["id"])] = {
            "spec": spec,
            "matrix": matrix,
            "selected_cols": selected_cols,
            "model": model,
            "labels": labels,
            "aligned_labels": aligned,
            "mapping": mapping,
            "inertia_ratio": float(model.inertia_ / total_energy) if total_energy > 1e-12 else np.nan,
            "silhouette_score": silhouette_score_np(matrix, labels),
            "calinski_harabasz_score": calinski_harabasz_score_np(matrix, labels, model.cluster_centers_),
            "davies_bouldin_score": davies_bouldin_score_np(matrix, labels, model.cluster_centers_),
            "ari": 1.0 if str(spec["id"]) == "M0" else adjusted_rand_index(baseline_labels, labels),
        }
    return results


def classify_level(values: pd.Series) -> dict[int, str]:
    low = values.quantile(0.33)
    high = values.quantile(0.67)
    labels = {}
    for cluster, value in values.items():
        if value >= high:
            labels[int(cluster)] = "高"
        elif value <= low:
            labels[int(cluster)] = "低"
        else:
            labels[int(cluster)] = "中"
    return labels


def classify_grain_trend(value: float) -> str:
    if value > GRAIN_TREND_THRESHOLD:
        return "上升"
    if value < -GRAIN_TREND_THRESHOLD:
        return "下降"
    return "稳定"


def make_profile_labels(m0_labels: np.ndarray, explanation_df: pd.DataFrame) -> tuple[dict[int, str], pd.DataFrame]:
    centers = explanation_df.copy()
    centers["cluster"] = m0_labels
    centers = centers.groupby("cluster").mean(numeric_only=True)
    density_levels = classify_level(centers["人口密度（人/平方公里）"])
    income_levels = classify_level(centers["人均可支配收入_地区总计"])
    food_levels = classify_level(centers["口粮（千克/人）"])
    feed_levels = classify_level(centers["饲料粮折算值（千克/人）"])
    labels = {}
    for cluster, row in centers.iterrows():
        cluster_id = int(cluster)
        labels[cluster_id] = (
            f"{density_levels[cluster_id]}密度-"
            f"{income_levels[cluster_id]}收入-"
            f"口粮{food_levels[cluster_id]}位{classify_grain_trend(row['口粮_线性趋势斜率'])}-"
            f"饲料粮{feed_levels[cluster_id]}位{classify_grain_trend(row['饲料粮_线性趋势斜率'])}"
        )
    return labels, centers.reset_index()


def make_summary(row: pd.Series) -> str:
    return "；".join(
        [
            f"人口密度={row['人口密度（人/平方公里）']:.2f}人/平方公里",
            f"收入={row['人均可支配收入_地区总计']:.2f}元",
            f"支出={row['人均消费支出_地区总计']:.2f}元",
            f"口粮={row['口粮（千克/人）']:.2f}千克/人",
            f"饲料粮={row['饲料粮折算值（千克/人）']:.2f}千克/人",
        ]
    )


def build_result_tables(
    feature_df: pd.DataFrame,
    explanation_df: pd.DataFrame,
    scaled_df: pd.DataFrame,
    experiments: dict[str, dict[str, object]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    m0_labels = np.asarray(experiments["M0"]["aligned_labels"], dtype=int)
    profile_labels, explanation_centers = make_profile_labels(m0_labels, explanation_df)
    explanation_extra_cols = [
        col for col in explanation_df.columns if col in PROVINCE_COLS or col not in feature_df.columns
    ]
    result = feature_df.merge(explanation_df[explanation_extra_cols], on=PROVINCE_COLS, how="inner")
    result["cluster"] = m0_labels
    result["cluster_label"] = result["cluster"].map(profile_labels)
    result["核心特征摘要"] = result.apply(make_summary, axis=1)
    result = result[
        PROVINCE_COLS
        + ["cluster", "cluster_label", "核心特征摘要"]
        + [col for col in explanation_extra_cols if col not in PROVINCE_COLS]
        + CORE_COLS
    ].sort_values(["cluster", "省份"])

    plain_scaled_centers = scaled_df.copy()
    plain_scaled_centers["cluster"] = m0_labels
    plain_scaled_centers = plain_scaled_centers.groupby("cluster")[CORE_COLS].mean().reset_index()

    original_centers = feature_df.merge(explanation_df[explanation_extra_cols], on=PROVINCE_COLS, how="inner")
    original_centers["cluster"] = m0_labels
    original_centers = original_centers.groupby("cluster").mean(numeric_only=True).reset_index()
    original_centers["cluster_label"] = original_centers["cluster"].map(profile_labels)
    ordered = ["cluster", "cluster_label"] + [
        col for col in original_centers.columns if col not in {"cluster", "cluster_label", "行政区划代码"}
    ]
    original_centers = original_centers[ordered]

    explanation_centers["cluster_label"] = explanation_centers["cluster"].map(profile_labels)
    return result.reset_index(drop=True), plain_scaled_centers, original_centers


def build_experiment_tables(
    feature_df: pd.DataFrame,
    experiments: dict[str, dict[str, object]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    quality_rows = []
    label_wide = feature_df[PROVINCE_COLS].copy()
    baseline = np.asarray(experiments["M0"]["aligned_labels"], dtype=int)
    for spec in EXPERIMENTS:
        exp_id = str(spec["id"])
        info = experiments[exp_id]
        labels = np.asarray(info["aligned_labels"], dtype=int)
        label_wide[exp_id] = labels
        counts = pd.Series(labels).value_counts()
        quality_rows.append(
            {
                "实验编号": exp_id,
                "实验名称": spec["name"],
                "保留指标域": "、".join(spec["domains"]),
                "权重规则": spec["weight_rule"],
                "K": N_CLUSTERS,
                "inertia": float(info["model"].inertia_),
                "inertia_ratio": float(info["inertia_ratio"]),
                "silhouette_score": float(info["silhouette_score"]),
                "calinski_harabasz_score": float(info["calinski_harabasz_score"]),
                "davies_bouldin_score": float(info["davies_bouldin_score"]),
                "与M0的ARI一致性": float(info["ari"]),
                **{f"类{cluster}省份数量": int(counts.get(cluster, 0)) for cluster in range(N_CLUSTERS)},
            }
        )
    quality = pd.DataFrame(quality_rows)
    stability = label_wide.copy()
    for exp_id in ["C1", "C2", "C3", "C4", "C5"]:
        stability[f"{exp_id}与M0一致"] = stability[exp_id] == stability["M0"]
    consistency_cols = [f"{exp_id}与M0一致" for exp_id in ["C1", "C2", "C3", "C4", "C5"]]
    stability["发生变化次数"] = (~stability[consistency_cols]).sum(axis=1)
    stability["稳定实验数量（含M0）"] = 1 + stability[consistency_cols].sum(axis=1)
    stability = stability.sort_values(["M0", "发生变化次数", "省份"], ascending=[True, True, True])
    return quality, label_wide, stability


def normalize_province_name(name: str) -> str:
    replacements = [
        ("维吾尔自治区", ""),
        ("壮族自治区", ""),
        ("回族自治区", ""),
        ("自治区", ""),
        ("特别行政区", ""),
        ("省", ""),
        ("市", ""),
    ]
    out = str(name).strip()
    for old, new in replacements:
        out = out.replace(old, new)
    return out


def iter_exterior_rings(geometry: dict) -> list[list[list[float]]]:
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if geom_type == "Polygon":
        return [coords[0]] if coords else []
    if geom_type == "MultiPolygon":
        return [polygon[0] for polygon in coords if polygon]
    return []


def plot_china_map(
    result: pd.DataFrame,
    output_path: Path,
    title: str,
    legend_title: str = "联合聚类结果",
) -> None:
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(f"缺少中国省级边界文件: {GEOJSON_PATH}")
    features = json.loads(GEOJSON_PATH.read_text(encoding="utf-8")).get("features", [])
    map_df = result.copy()
    map_df["map_name"] = map_df["省份"].map(normalize_province_name)
    cluster_info = map_df.set_index("map_name")[["cluster", "cluster_label"]].to_dict(orient="index")
    configure_chinese_font()
    fig, ax = plt.subplots(figsize=(13, 10), dpi=220)
    ax.set_facecolor("#F7F8FA")
    min_x, min_y, max_x, max_y = 180.0, 90.0, -180.0, -90.0
    for feature in features:
        raw_name = feature.get("properties", {}).get("name", "")
        info = cluster_info.get(normalize_province_name(raw_name))
        facecolor = COLOR_PALETTE[int(info["cluster"])] if info else "#D9DEE7"
        edgecolor = "#FFFFFF" if info else "#C8CED8"
        for ring in iter_exterior_rings(feature.get("geometry", {})):
            if len(ring) < 3:
                continue
            xs = [point[0] for point in ring]
            ys = [point[1] for point in ring]
            min_x, min_y = min(min_x, min(xs)), min(min_y, min(ys))
            max_x, max_y = max(max_x, max(xs)), max(max_y, max(ys))
            ax.add_patch(
                Polygon(
                    ring,
                    closed=True,
                    facecolor=facecolor,
                    edgecolor=edgecolor,
                    linewidth=0.65 if info else 0.45,
                    joinstyle="round",
                )
            )
    ax.set_xlim(min_x - 2.0, max_x + 2.0)
    ax.set_ylim(min_y - 2.0, max_y + 2.0)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    counts = result.groupby(["cluster", "cluster_label"]).size().reset_index(name="省份数")
    legend_items = [
        Patch(
            facecolor=COLOR_PALETTE[int(row.cluster)],
            edgecolor="white",
            label=f"类{row.cluster}: {row.cluster_label}（{row.省份数}省）",
        )
        for row in counts.sort_values("cluster").itertuples(index=False)
    ]
    legend_items.append(Patch(facecolor="#D9DEE7", edgecolor="#C8CED8", label="未纳入31省范围"))
    ax.legend(handles=legend_items, loc="lower left", frameon=True, framealpha=0.94, fontsize=8.5, title=legend_title)
    ax.set_title(title, fontsize=16, pad=12)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def blend_with_white(color: str, white_ratio: float) -> tuple[float, float, float]:
    rgb = np.asarray(matplotlib_colors.to_rgb(color), dtype=float)
    return tuple((rgb * (1 - white_ratio) + white_ratio).tolist())


def darken_color(color: str, factor: float) -> tuple[float, float, float]:
    rgb = np.asarray(matplotlib_colors.to_rgb(color), dtype=float)
    return tuple((rgb * factor).tolist())


def plot_stable_core_map(
    result: pd.DataFrame,
    stability: pd.DataFrame,
    output_path: Path,
) -> int:
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(f"缺少中国省级边界文件: {GEOJSON_PATH}")
    features = json.loads(GEOJSON_PATH.read_text(encoding="utf-8")).get("features", [])
    stable_provinces = set(stability.loc[stability["发生变化次数"] == 0, "省份"])
    map_df = result.copy()
    map_df["is_stable_core"] = map_df["省份"].isin(stable_provinces)
    map_df["map_name"] = map_df["省份"].map(normalize_province_name)
    cluster_info = map_df.set_index("map_name")[["cluster", "cluster_label", "is_stable_core"]].to_dict(orient="index")
    configure_chinese_font()
    fig, ax = plt.subplots(figsize=(13, 10), dpi=220)
    ax.set_facecolor("#F7F8FA")
    min_x, min_y, max_x, max_y = 180.0, 90.0, -180.0, -90.0
    for feature in features:
        raw_name = feature.get("properties", {}).get("name", "")
        info = cluster_info.get(normalize_province_name(raw_name))
        if info:
            base_color = COLOR_PALETTE[int(info["cluster"])]
            facecolor = darken_color(base_color, 0.72) if info["is_stable_core"] else blend_with_white(base_color, 0.62)
            edgecolor = "#FFFFFF"
            linewidth = 0.85 if info["is_stable_core"] else 0.55
        else:
            facecolor = "#D9DEE7"
            edgecolor = "#C8CED8"
            linewidth = 0.45
        for ring in iter_exterior_rings(feature.get("geometry", {})):
            if len(ring) < 3:
                continue
            xs = [point[0] for point in ring]
            ys = [point[1] for point in ring]
            min_x, min_y = min(min_x, min(xs)), min(min_y, min(ys))
            max_x, max_y = max(max_x, max(xs)), max(max_y, max(ys))
            ax.add_patch(
                Polygon(
                    ring,
                    closed=True,
                    facecolor=facecolor,
                    edgecolor=edgecolor,
                    linewidth=linewidth,
                    joinstyle="round",
                )
            )
    ax.set_xlim(min_x - 2.0, max_x + 2.0)
    ax.set_ylim(min_y - 2.0, max_y + 2.0)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    core_counts = map_df.groupby(["cluster", "cluster_label"])["is_stable_core"].agg(["sum", "count"]).reset_index()
    legend_items = []
    for row in core_counts.sort_values("cluster").itertuples(index=False):
        cluster = int(row.cluster)
        legend_items.append(
            Patch(
                facecolor=darken_color(COLOR_PALETTE[cluster], 0.72),
                edgecolor="white",
                label=f"类{cluster}核心省份: {row.cluster_label}（{int(row.sum)}省）",
            )
        )
    legend_items.extend(
        [
            Patch(facecolor="#6B7280", edgecolor="white", label="深色：六组实验分类完全一致的核心省份"),
            Patch(facecolor="#D1D5DB", edgecolor="white", label="浅色：其余主实验分类省份"),
            Patch(facecolor="#D9DEE7", edgecolor="#C8CED8", label="未纳入31省范围"),
        ]
    )
    ax.legend(
        handles=legend_items,
        loc="lower left",
        frameon=True,
        framealpha=0.94,
        fontsize=8.2,
        title="强力绝对稳定核心省份",
    )
    ax.set_title(
        f"31省主实验强力绝对稳定核心省份分布（M0, {YEAR_START}-{YEAR_END}, K={N_CLUSTERS}）",
        fontsize=16,
        pad=12,
    )
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return len(stable_provinces)


def plot_quality_comparison(quality: pd.DataFrame, output_path: Path) -> None:
    configure_chinese_font()
    labels = quality["实验编号"].tolist()
    metrics = [
        ("inertia_ratio", "类内离差占总离差比例", "越低越好"),
        ("silhouette_score", "轮廓系数", "越高越好"),
        ("calinski_harabasz_score", "Calinski-Harabasz 指数", "越高越好"),
        ("davies_bouldin_score", "Davies-Bouldin 指数", "越低越好"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), dpi=180)
    for ax, (col, title, note) in zip(axes.ravel(), metrics, strict=True):
        bars = ax.bar(labels, quality[col], color=["#4C78A8"] + ["#72B7B2"] * 5)
        ax.set_title(f"{title}（{note}）")
        ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.35)
        ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
    fig.suptitle("六组联合聚类实验质量对比", fontsize=16)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_stability_heatmap(stability: pd.DataFrame, output_path: Path) -> None:
    configure_chinese_font()
    experiment_ids = [str(spec["id"]) for spec in EXPERIMENTS]
    matrix = stability[experiment_ids].to_numpy(dtype=int)
    fig, ax = plt.subplots(figsize=(9, 10), dpi=180)
    image = ax.imshow(
        matrix,
        aspect="auto",
        cmap=ListedColormap(COLOR_PALETTE),
        vmin=-0.5,
        vmax=N_CLUSTERS - 0.5,
    )
    ax.set_title("31省联合聚类稳定性热图")
    ax.set_xticks(np.arange(len(experiment_ids)))
    ax.set_xticklabels(experiment_ids)
    ax.set_yticks(np.arange(len(stability)))
    ax.set_yticklabels(stability["省份"], fontsize=8)
    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            ax.text(col_idx, row_idx, str(matrix[row_idx, col_idx]), ha="center", va="center", color="white", fontsize=7)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.03, ticks=range(N_CLUSTERS))
    colorbar.ax.set_yticklabels([f"类{cluster}" for cluster in range(N_CLUSTERS)])
    ax.set_xlabel("实验编号")
    ax.set_ylabel("省份（按 M0 类别和稳定性排序）")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_ari_comparison(quality: pd.DataFrame, output_path: Path) -> None:
    configure_chinese_font()
    df = quality[quality["实验编号"] != "M0"].copy()
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=180)
    bars = ax.bar(df["实验编号"], df["与M0的ARI一致性"], color="#59A14F")
    ax.set_ylim(min(-0.1, float(df["与M0的ARI一致性"].min()) - 0.05), 1.05)
    ax.set_title("对照实验与 M0 的 ARI 一致性")
    ax.set_ylabel("ARI")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.35)
    ax.bar_label(bars, fmt="%.3f", padding=3)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def write_quality_checks(
    area: pd.DataFrame,
    population: pd.DataFrame,
    economy: pd.DataFrame,
    food_grain: pd.DataFrame,
    feed_grain: pd.DataFrame,
    feature_df: pd.DataFrame,
    experiments: dict[str, dict[str, object]],
) -> pd.DataFrame:
    rows = [
        {"检查项": "面积表覆盖31个省份", "通过": len(area) == EXPECTED_PROVINCES},
        {
            "检查项": "面积表省份和行政区划代码唯一",
            "通过": area["省份"].nunique() == EXPECTED_PROVINCES and area["行政区划代码"].nunique() == EXPECTED_PROVINCES,
        },
        {"检查项": "土地面积均为正数", "通过": bool((area["土地调查总面积（平方公里）"] > 0).all())},
        {"检查项": "面积表与人口表省份完全匹配", "通过": set(area["省份"]) == set(population["省份"])},
        {
            "检查项": "四类输入的行政区划代码均已按面积表统一",
            "通过": all(
                set(panel[PROVINCE_COLS].drop_duplicates().itertuples(index=False, name=None))
                == set(area[PROVINCE_COLS].drop_duplicates().itertuples(index=False, name=None))
                for panel in [population, economy, food_grain, feed_grain]
            ),
        },
        {
            "检查项": "人口表2015-2024覆盖31省且总人口无缺失",
            "通过": len(population) == EXPECTED_PANEL_ROWS and not population["总人口"].isna().any(),
        },
        {
            "检查项": "人口密度均为正数且无缺失",
            "通过": bool((population["人口密度（人/平方公里）"] > 0).all())
            and not population["人口密度（人/平方公里）"].isna().any(),
        },
        {"检查项": "经济数据覆盖31省", "通过": economy["省份"].nunique() == EXPECTED_PROVINCES},
        {"检查项": "口粮数据覆盖31省", "通过": food_grain["省份"].nunique() == EXPECTED_PROVINCES},
        {"检查项": "饲料粮数据覆盖31省", "通过": feed_grain["省份"].nunique() == EXPECTED_PROVINCES},
        {
            "检查项": "20个联合聚类核心特征无缺失值和无穷值",
            "通过": feature_df[CORE_COLS].shape[1] == 20
            and bool(np.isfinite(feature_df[CORE_COLS].to_numpy(dtype=float)).all()),
        },
        {
            "检查项": "六组实验均覆盖31省",
            "通过": all(len(np.asarray(info["labels"])) == EXPECTED_PROVINCES for info in experiments.values()),
        },
        {"检查项": "六组实验均固定K=5", "通过": N_CLUSTERS == 5 and len(experiments) == 6},
        {
            "检查项": "六组实验均无空簇",
            "通过": all(len(np.unique(np.asarray(info["labels"]))) == N_CLUSTERS for info in experiments.values()),
        },
        {
            "检查项": "六组实验使用统一复现参数",
            "通过": RANDOM_STATE == 42 and N_INIT == 80 and MAX_ITER == 300,
        },
        {"检查项": "PCA仅用于展示", "通过": True},
    ]
    quality = pd.DataFrame(rows)
    if not quality["通过"].all():
        failed = quality.loc[~quality["通过"], "检查项"].tolist()
        raise ValueError(f"质量检查未通过: {failed}")
    return quality


def write_outputs(
    area: pd.DataFrame,
    admin_code_corrections: pd.DataFrame,
    population: pd.DataFrame,
    economy: pd.DataFrame,
    food_grain: pd.DataFrame,
    feed_grain: pd.DataFrame,
    feature_df: pd.DataFrame,
    explanation_df: pd.DataFrame,
    scaled_df: pd.DataFrame,
    experiments: dict[str, dict[str, object]],
) -> None:
    result, scaled_centers, original_centers = build_result_tables(feature_df, explanation_df, scaled_df, experiments)
    quality, label_wide, stability = build_experiment_tables(feature_df, experiments)
    checks = write_quality_checks(area, population, economy, food_grain, feed_grain, feature_df, experiments)

    population.to_csv(TABLE_DIR / "人口域清洗后长表.csv", index=False, encoding="utf-8-sig")
    economy.to_csv(TABLE_DIR / "经济域清洗后长表.csv", index=False, encoding="utf-8-sig")
    food_grain.to_csv(TABLE_DIR / "口粮域清洗后长表.csv", index=False, encoding="utf-8-sig")
    feed_grain.to_csv(TABLE_DIR / "饲料粮域清洗后长表.csv", index=False, encoding="utf-8-sig")
    feature_df.to_csv(TABLE_DIR / "联合聚类核心特征表.csv", index=False, encoding="utf-8-sig")
    scaled_df.to_csv(TABLE_DIR / "联合聚类标准化特征表.csv", index=False, encoding="utf-8-sig")
    result.to_csv(TABLE_DIR / "省份联合聚类结果.csv", index=False, encoding="utf-8-sig")
    scaled_centers.to_csv(TABLE_DIR / "聚类中心_标准化.csv", index=False, encoding="utf-8-sig")
    original_centers.to_csv(TABLE_DIR / "聚类中心_原始特征均值.csv", index=False, encoding="utf-8-sig")
    quality.to_csv(TABLE_DIR / "六组实验聚类质量对比.csv", index=False, encoding="utf-8-sig")
    label_wide.to_csv(TABLE_DIR / "六组实验省份聚类标签宽表.csv", index=False, encoding="utf-8-sig")
    stability.to_csv(TABLE_DIR / "省份分组稳定性.csv", index=False, encoding="utf-8-sig")
    admin_code_corrections.to_csv(TABLE_DIR / "行政区划代码校正记录.csv", index=False, encoding="utf-8-sig")

    summary = pd.DataFrame(
        [
            {
                "聚类对象": "人口、经济、口粮、饲料粮四域联合聚类",
                "时间范围": f"{YEAR_START}-{YEAR_END}",
                "固定K值": N_CLUSTERS,
                "省份数量": EXPECTED_PROVINCES,
                "核心特征数量": len(CORE_COLS),
                "主实验": "M0四域等权",
                "对照实验": "C1所有特征直接等权；C2-C5逐一移除单个域并将剩余三域重新等权",
                "对数转换": "人口密度、人均可支配收入、人均消费支出先执行log1p",
                "面积口径": "中科院地理科学与资源研究所人地系统数据库1996年分省土地调查面积",
                "面积来源": "https://www.data.ac.cn/table/tbb07",
                "行政区划代码处理": "按面积表统一31省行政区划代码；原始数据中的海南450000校正为460000",
                "随机参数": f"random_state={RANDOM_STATE}; n_init={N_INIT}; max_iter={MAX_ITER}",
            }
        ]
    )
    summary.to_csv(TABLE_DIR / "聚类结果说明.csv", index=False, encoding="utf-8-sig")

    m0 = experiments["M0"]
    profile_labels = result[["cluster", "cluster_label"]].drop_duplicates().set_index("cluster")["cluster_label"].to_dict()
    map_paths = [FIGURE_DIR / "中国地图聚类结果.png"]
    plot_china_map(
        result,
        map_paths[0],
        f"31省四域等权联合聚类中国地图（M0, {YEAR_START}-{YEAR_END}, K={N_CLUSTERS}）",
    )
    for spec in EXPERIMENTS[1:]:
        exp_id = str(spec["id"])
        experiment_map = feature_df[PROVINCE_COLS].copy()
        experiment_map["cluster"] = np.asarray(experiments[exp_id]["aligned_labels"], dtype=int)
        experiment_map["cluster_label"] = experiment_map["cluster"].map(profile_labels)
        map_path = FIGURE_DIR / f"中国地图聚类结果_{exp_id}{spec['name']}.png"
        plot_china_map(
            experiment_map,
            map_path,
            f"31省联合聚类中国地图（{exp_id}: {spec['name']}, {YEAR_START}-{YEAR_END}, K={N_CLUSTERS}）",
            legend_title="与 M0 对齐后的聚类结果",
        )
        map_paths.append(map_path)
    stable_core_map_path = FIGURE_DIR / "中国地图聚类结果_M0强力绝对稳定核心省份加深色.png"
    stable_core_count = plot_stable_core_map(result, stability, stable_core_map_path)
    plot_pca_scatter(
        np.asarray(m0["matrix"], dtype=float),
        result,
        f"31省四域等权联合聚类PCA散点图（{YEAR_START}-{YEAR_END}, K={N_CLUSTERS}）",
        FIGURE_DIR / "PCA二维聚类散点图.png",
    )
    plot_center_heatmap(
        scaled_centers,
        f"四域联合聚类核心特征标准化中心热图（K={N_CLUSTERS}）",
        FIGURE_DIR / "聚类核心特征均值热图.png",
    )
    plot_cluster_counts(result, "四域联合聚类各类省份数量", FIGURE_DIR / "各聚类省份数量柱状图.png")
    plot_quality_comparison(quality, FIGURE_DIR / "六组实验聚类质量对比.png")
    plot_stability_heatmap(stability, FIGURE_DIR / "省份聚类稳定性热图.png")
    plot_ari_comparison(quality, FIGURE_DIR / "消融实验ARI一致性对比.png")
    checks = pd.concat(
        [
            checks,
            pd.DataFrame(
                [
                    {
                        "检查项": "M0、C1-C5中国地图聚类图均已生成",
                        "通过": len(map_paths) == len(EXPERIMENTS) and all(path.exists() for path in map_paths),
                    },
                    {
                        "检查项": "M0强力绝对稳定核心省份加深色地图已生成",
                        "通过": stable_core_map_path.exists() and stable_core_count > 0,
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    if not checks["通过"].all():
        failed = checks.loc[~checks["通过"], "检查项"].tolist()
        raise ValueError(f"质量检查未通过: {failed}")
    checks.to_csv(TABLE_DIR / "质量检查.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    configure_chinese_font()
    ensure_dirs(TABLE_DIR, FIGURE_DIR)
    area = load_area_table()
    population, population_corrections = load_population_panel(area)
    economy, economy_corrections = load_economy_panel(area)
    food_grain, food_corrections = load_grain_panel(FOOD_GRAIN_CSV, "口粮（千克/人）", "口粮数据", area)
    feed_grain, feed_corrections = load_grain_panel(
        FEED_GRAIN_CSV,
        "饲料粮折算值（千克/人）",
        "饲料粮数据",
        area,
    )
    admin_code_corrections = pd.concat(
        [population_corrections, economy_corrections, food_corrections, feed_corrections],
        ignore_index=True,
    )
    feature_df, explanation_df = build_core_features(population, economy, food_grain, feed_grain)

    scaled_values, _means, _stds = standardize_values(feature_df[CORE_COLS].to_numpy(dtype=float))
    scaled_df = feature_df[PROVINCE_COLS].copy()
    scaled_df[CORE_COLS] = scaled_values
    experiments = fit_experiments(scaled_df)
    write_outputs(
        area,
        admin_code_corrections,
        population,
        economy,
        food_grain,
        feed_grain,
        feature_df,
        explanation_df,
        scaled_df,
        experiments,
    )
    print(f"联合聚类完成，输出目录: {TASK_DIR}")


if __name__ == "__main__":
    main()
