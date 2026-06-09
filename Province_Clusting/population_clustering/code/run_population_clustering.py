from __future__ import annotations

from functools import reduce
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
GRAIN_DIR = ROOT_DIR.parents[1]
sys.path.insert(0, str(ROOT_DIR / "common"))

from clustering_utils import (  # noqa: E402
    add_summary_column,
    build_series_features,
    cluster_feature_table,
    configure_chinese_font,
    ensure_dirs,
    fill_panel_by_province,
    make_cluster_labels,
    plot_center_heatmap,
    plot_cluster_counts,
    plot_pca_scatter,
    plot_sorted_results,
    write_quality_report,
)


TASK_DIR = Path(__file__).resolve().parents[1]
TABLE_DIR = TASK_DIR / "table"
FIGURE_DIR = TASK_DIR / "figure"
INPUT_CSV = GRAIN_DIR / "宏观数据收集（CSV编码）" / "人口数据（省级）.csv"

YEAR_START = 2000
YEAR_END = 2024
DEFAULT_K = 4

BASE_COLS = [
    "总人口",
    "城镇人口",
    "乡村人口",
    "0-14岁",
    "15-64岁",
    "65岁及以上",
    "平均家庭规模",
    "户数",
]
RATIO_COLS = ["城镇化率", "乡村人口占比", "0-14岁占比", "15-64岁占比", "65岁及以上占比"]


def load_clean_data() -> pd.DataFrame:
    raw = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    df = raw.rename(columns={"Unnamed: 0": "省份", "Unnamed: 1": "年份"}).copy()
    df["年份"] = pd.to_numeric(df["年份"], errors="coerce")
    df = df[df["年份"].notna()].copy()
    df["年份"] = df["年份"].astype(int)
    df = df[df["年份"].between(YEAR_START, YEAR_END)].copy()
    for col in ["行政区划代码"] + BASE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["城镇化率"] = df["城镇人口"] / df["总人口"]
    df["乡村人口占比"] = df["乡村人口"] / df["总人口"]
    df["0-14岁占比"] = df["0-14岁"] / df["总人口"]
    df["15-64岁占比"] = df["15-64岁"] / df["总人口"]
    df["65岁及以上占比"] = df["65岁及以上"] / df["总人口"]

    value_cols = BASE_COLS + RATIO_COLS
    clean = df[["省份", "年份", "行政区划代码"] + value_cols].sort_values(["省份", "年份"])
    clean = fill_panel_by_province(clean, "省份", "年份", value_cols)
    if clean["省份"].nunique() != 31:
        raise ValueError(f"人口清洗后省份数量不是31: {clean['省份'].nunique()}")
    return clean.reset_index(drop=True)


def build_population_features(clean: pd.DataFrame) -> pd.DataFrame:
    feature_parts = []
    for col in BASE_COLS + RATIO_COLS:
        part = build_series_features(clean, col, prefix=f"{col}_", include_std=False)
        feature_parts.append(part)
    features = reduce(lambda left, right: left.merge(right, on=["省份", "行政区划代码"], how="outer"), feature_parts)
    features = features.replace([np.inf, -np.inf], np.nan)
    return features.sort_values("省份").reset_index(drop=True)


def apply_population_labels(result_df: pd.DataFrame, feature_df: pd.DataFrame) -> pd.DataFrame:
    merged = result_df.merge(feature_df, on=["省份", "行政区划代码"], how="left")
    centers = merged.groupby("cluster")[
        ["总人口_最新年值", "65岁及以上占比_最新年值", "总人口_线性趋势斜率"]
    ].mean()
    pop_low = centers["总人口_最新年值"].quantile(0.33)
    pop_high = centers["总人口_最新年值"].quantile(0.67)
    age_low = centers["65岁及以上占比_最新年值"].quantile(0.33)
    age_high = centers["65岁及以上占比_最新年值"].quantile(0.67)
    label_map = {}
    for cluster, row in centers.iterrows():
        if row["总人口_最新年值"] >= pop_high:
            pop_level = "高人口规模"
        elif row["总人口_最新年值"] <= pop_low:
            pop_level = "低人口规模"
        else:
            pop_level = "中等人口规模"

        if row["65岁及以上占比_最新年值"] >= age_high:
            age_level = "老龄化高"
        elif row["65岁及以上占比_最新年值"] <= age_low:
            age_level = "老龄化低"
        else:
            age_level = "老龄化中"

        if row["总人口_线性趋势斜率"] > 0.5:
            direction = "上升型"
        elif row["总人口_线性趋势斜率"] < -0.5:
            direction = "下降型"
        else:
            direction = "稳定型"
        label_map[cluster] = f"{pop_level}-{age_level}-{direction}"
    merged["cluster_label"] = merged["cluster"].map(label_map)
    return merged


def main() -> None:
    configure_chinese_font()
    ensure_dirs(TABLE_DIR, FIGURE_DIR)
    clean = load_clean_data()
    clean.to_csv(TABLE_DIR / "清洗后长表.csv", index=False, encoding="utf-8-sig")

    features = build_population_features(clean)
    features.to_csv(TABLE_DIR / "省份聚类特征表.csv", index=False, encoding="utf-8-sig")

    cluster_info = cluster_feature_table(features, TABLE_DIR, default_k=DEFAULT_K)
    labeled = apply_population_labels(cluster_info["result_df"], cluster_info["clean_feature_df"])
    labeled = add_summary_column(
        labeled,
        ["总人口_最新年值", "城镇化率_最新年值", "65岁及以上占比_最新年值", "总人口_线性趋势斜率"],
    )
    result_cols = ["省份", "行政区划代码", "cluster", "cluster_label", "核心特征摘要"] + cluster_info["numeric_cols"]
    labeled = labeled[result_cols].sort_values(["cluster", "总人口_最新年值", "省份"], ascending=[True, False, True])
    labeled.to_csv(TABLE_DIR / "省份聚类结果.csv", index=False, encoding="utf-8-sig")

    summary = pd.DataFrame(
        [
            {
                "聚类对象": "人口结构",
                "时间范围": f"{YEAR_START}-{YEAR_END}",
                "默认K值": cluster_info["selected_k"],
                "省份数量": labeled["省份"].nunique(),
                "输入文件": str(INPUT_CSV),
                "核心特征": "人口规模、城乡结构、年龄结构、家庭规模、户数的水平和趋势特征",
            }
        ]
    )
    summary.to_csv(TABLE_DIR / "聚类结果说明.csv", index=False, encoding="utf-8-sig")

    plot_pca_scatter(
        cluster_info["scaled_values"],
        apply_population_labels(cluster_info["result_df"], cluster_info["clean_feature_df"]),
        f"31省人口结构聚类PCA散点图（{YEAR_START}-{YEAR_END}, K={cluster_info['selected_k']}）",
        FIGURE_DIR / "PCA二维聚类散点图.png",
    )
    plot_center_heatmap(
        cluster_info["scaled_centers"],
        f"人口聚类特征标准化中心热图（K={cluster_info['selected_k']}）",
        FIGURE_DIR / "聚类特征均值热图.png",
    )
    plot_cluster_counts(labeled, "人口聚类各类省份数量", FIGURE_DIR / "各聚类省份数量柱状图.png")
    plot_sorted_results(labeled, "总人口_最新年值", "各省份人口聚类结果排序", FIGURE_DIR / "各省份聚类结果排序图.png")

    write_quality_report(
        labeled,
        cluster_info["clean_feature_df"],
        cluster_info["numeric_cols"],
        cluster_info["evaluation_df"],
        cluster_info["selected_k"],
        TABLE_DIR / "质量检查.csv",
    )


if __name__ == "__main__":
    main()
