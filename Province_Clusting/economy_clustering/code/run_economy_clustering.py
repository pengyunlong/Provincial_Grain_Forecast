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
INPUT_CSV = GRAIN_DIR / "宏观数据收集（CSV编码）" / "经济数据（省级）.csv"

YEAR_START = 2000
YEAR_END = 2024
DEFAULT_K = 4

RENAME_MAP = {
    "Unnamed: 0": "省份",
    "Unnamed: 1": "年份",
    "Unnamed: 2": "行政区划代码",
    "Unnamed: 3": "地区生产总值",
    "人均可支配收入": "人均可支配收入_地区总计",
    "人均消费支出": "人均消费支出_地区总计",
    "地区居民消费价格指数": "地区居民消费价格指数_总指数",
    "Unnamed: 13": "地区居民消费价格指数_食品",
    "Unnamed: 14": "地区居民消费价格指数_粮食",
}

VALUE_COLS = [
    "地区生产总值",
    "人均可支配收入_地区总计",
    "人均消费支出_地区总计",
    "地区居民消费价格指数_总指数",
    "地区居民消费价格指数_食品",
    "地区居民消费价格指数_粮食",
]

EXCLUDED_WORDS = ["城镇", "农村", "城市"]


def load_clean_data() -> pd.DataFrame:
    raw = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    df = raw.rename(columns=RENAME_MAP).copy()
    df["年份"] = pd.to_numeric(df["年份"], errors="coerce")
    df = df[df["年份"].notna()].copy()
    df["年份"] = df["年份"].astype(int)
    df = df[df["年份"].between(YEAR_START, YEAR_END)].copy()
    for col in ["行政区划代码"] + VALUE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    clean = df[["省份", "年份", "行政区划代码"] + VALUE_COLS].sort_values(["省份", "年份"])
    clean = fill_panel_by_province(clean, "省份", "年份", VALUE_COLS)
    if clean["省份"].nunique() != 31:
        raise ValueError(f"经济清洗后省份数量不是31: {clean['省份'].nunique()}")
    bad_cols = [col for col in clean.columns if any(word in col for word in EXCLUDED_WORDS)]
    if bad_cols:
        raise ValueError(f"经济聚类清洗表仍包含分城乡字段: {bad_cols}")
    return clean.reset_index(drop=True)


def build_economy_features(clean: pd.DataFrame) -> pd.DataFrame:
    feature_parts = []
    for col in VALUE_COLS:
        part = build_series_features(clean, col, prefix=f"{col}_", include_std=True)
        feature_parts.append(part)
    features = reduce(lambda left, right: left.merge(right, on=["省份", "行政区划代码"], how="outer"), feature_parts)
    features = features.replace([np.inf, -np.inf], np.nan)
    return features.sort_values("省份").reset_index(drop=True)


def main() -> None:
    configure_chinese_font()
    ensure_dirs(TABLE_DIR, FIGURE_DIR)
    clean = load_clean_data()
    clean.to_csv(TABLE_DIR / "清洗后长表.csv", index=False, encoding="utf-8-sig")

    features = build_economy_features(clean)
    features.to_csv(TABLE_DIR / "省份聚类特征表.csv", index=False, encoding="utf-8-sig")

    cluster_info = cluster_feature_table(features, TABLE_DIR, default_k=DEFAULT_K)
    excluded_in_features = any(any(word in col for word in EXCLUDED_WORDS) for col in cluster_info["numeric_cols"])
    labeled = make_cluster_labels(
        cluster_info["result_df"],
        cluster_info["clean_feature_df"],
        level_col="人均可支配收入_地区总计_最新年值",
        trend_col="人均可支配收入_地区总计_线性趋势斜率",
        high_word="高经济水平",
        mid_word="中等经济水平",
        low_word="低经济水平",
    )
    labeled = add_summary_column(
        labeled,
        [
            "地区生产总值_最新年值",
            "人均可支配收入_地区总计_最新年值",
            "人均消费支出_地区总计_最新年值",
            "地区居民消费价格指数_总指数_最新年值",
        ],
    )
    result_cols = ["省份", "行政区划代码", "cluster", "cluster_label", "核心特征摘要"] + cluster_info["numeric_cols"]
    labeled = labeled[result_cols].sort_values(
        ["cluster", "人均可支配收入_地区总计_最新年值", "省份"], ascending=[True, False, True]
    )
    labeled.to_csv(TABLE_DIR / "省份聚类结果.csv", index=False, encoding="utf-8-sig")

    summary = pd.DataFrame(
        [
            {
                "聚类对象": "经济水平与价格指标",
                "时间范围": f"{YEAR_START}-{YEAR_END}",
                "默认K值": cluster_info["selected_k"],
                "省份数量": labeled["省份"].nunique(),
                "输入文件": str(INPUT_CSV),
                "核心特征": "GDP、人均可支配收入总计、人均消费支出总计、总CPI、食品CPI、粮食CPI的水平、趋势与波动特征",
                "是否排除分城乡字段": not excluded_in_features,
            }
        ]
    )
    summary.to_csv(TABLE_DIR / "聚类结果说明.csv", index=False, encoding="utf-8-sig")

    plot_pca_scatter(
        cluster_info["scaled_values"],
        make_cluster_labels(
            cluster_info["result_df"],
            cluster_info["clean_feature_df"],
            "人均可支配收入_地区总计_最新年值",
            "人均可支配收入_地区总计_线性趋势斜率",
            "高经济水平",
            "中等经济水平",
            "低经济水平",
        ),
        f"31省经济指标聚类PCA散点图（{YEAR_START}-{YEAR_END}, K={cluster_info['selected_k']}）",
        FIGURE_DIR / "PCA二维聚类散点图.png",
    )
    plot_center_heatmap(
        cluster_info["scaled_centers"],
        f"经济聚类特征标准化中心热图（K={cluster_info['selected_k']}）",
        FIGURE_DIR / "聚类特征均值热图.png",
    )
    plot_cluster_counts(labeled, "经济聚类各类省份数量", FIGURE_DIR / "各聚类省份数量柱状图.png")
    plot_sorted_results(
        labeled,
        "人均可支配收入_地区总计_最新年值",
        "各省份经济聚类结果排序",
        FIGURE_DIR / "各省份聚类结果排序图.png",
    )

    write_quality_report(
        labeled,
        cluster_info["clean_feature_df"],
        cluster_info["numeric_cols"],
        cluster_info["evaluation_df"],
        cluster_info["selected_k"],
        TABLE_DIR / "质量检查.csv",
        extra_checks={"经济聚类不包含分城乡字段": not excluded_in_features},
    )


if __name__ == "__main__":
    main()
