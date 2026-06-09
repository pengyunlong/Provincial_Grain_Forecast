from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "common"))

from clustering_utils import (  # noqa: E402
    add_summary_column,
    build_series_features,
    cluster_feature_table,
    configure_chinese_font,
    ensure_dirs,
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
INPUT_CSV = (
    PROJECT_DIR
    / "数据提取与可视化"
    / "七类动物性消费"
    / "饲料粮"
    / "table"
    / "省级饲料粮长表数据.csv"
)

VALUE_COL = "饲料粮折算值（千克/人）"
YEAR_START = 2015
YEAR_END = 2024
DEFAULT_K = 4


def load_clean_data() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    df["年份"] = pd.to_numeric(df["年份"], errors="coerce").astype("Int64")
    df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
    clean = df[df["年份"].between(YEAR_START, YEAR_END)].copy()
    clean = clean[["省份", "年份", "行政区划代码", VALUE_COL]].sort_values(["省份", "年份"])
    if clean["省份"].nunique() != 31:
        raise ValueError(f"饲料粮清洗后省份数量不是31: {clean['省份'].nunique()}")
    missing = clean.groupby("省份")[VALUE_COL].apply(lambda s: s.isna().sum())
    if (missing > 0).any():
        raise ValueError(f"饲料粮 2015-2024 存在缺失: {missing[missing > 0].to_dict()}")
    return clean.reset_index(drop=True)


def main() -> None:
    configure_chinese_font()
    ensure_dirs(TABLE_DIR, FIGURE_DIR)
    clean = load_clean_data()
    clean.to_csv(TABLE_DIR / "清洗后长表.csv", index=False, encoding="utf-8-sig")

    features = build_series_features(clean, VALUE_COL, prefix="饲料粮")
    features.to_csv(TABLE_DIR / "省份聚类特征表.csv", index=False, encoding="utf-8-sig")

    cluster_info = cluster_feature_table(features, TABLE_DIR, default_k=DEFAULT_K)
    labeled = make_cluster_labels(
        cluster_info["result_df"],
        cluster_info["clean_feature_df"],
        level_col="饲料粮均值",
        trend_col="饲料粮线性趋势斜率",
    )
    labeled = add_summary_column(
        labeled,
        ["饲料粮均值", "饲料粮最新年值", "饲料粮变化量", "饲料粮线性趋势斜率", "饲料粮变异系数"],
    )
    result_cols = ["省份", "行政区划代码", "cluster", "cluster_label", "核心特征摘要"] + cluster_info["numeric_cols"]
    labeled = labeled[result_cols].sort_values(["cluster", "饲料粮均值", "省份"], ascending=[True, False, True])
    labeled.to_csv(TABLE_DIR / "省份聚类结果.csv", index=False, encoding="utf-8-sig")

    summary = pd.DataFrame(
        [
            {
                "聚类对象": "饲料粮消费",
                "时间范围": f"{YEAR_START}-{YEAR_END}",
                "默认K值": cluster_info["selected_k"],
                "省份数量": labeled["省份"].nunique(),
                "输入文件": str(INPUT_CSV),
                "核心特征": "均值、最新年值、首年值、变化量、变化率、线性趋势斜率、标准差、变异系数",
            }
        ]
    )
    summary.to_csv(TABLE_DIR / "聚类结果说明.csv", index=False, encoding="utf-8-sig")

    plot_pca_scatter(
        cluster_info["scaled_values"],
        make_cluster_labels(cluster_info["result_df"], cluster_info["clean_feature_df"], "饲料粮均值", "饲料粮线性趋势斜率"),
        f"31省饲料粮消费聚类PCA散点图（{YEAR_START}-{YEAR_END}, K={cluster_info['selected_k']}）",
        FIGURE_DIR / "PCA二维聚类散点图.png",
    )
    plot_center_heatmap(
        cluster_info["scaled_centers"],
        f"饲料粮聚类特征标准化中心热图（K={cluster_info['selected_k']}）",
        FIGURE_DIR / "聚类特征均值热图.png",
    )
    plot_cluster_counts(labeled, "饲料粮聚类各类省份数量", FIGURE_DIR / "各聚类省份数量柱状图.png")
    plot_sorted_results(labeled, "饲料粮均值", "各省份饲料粮聚类结果排序", FIGURE_DIR / "各省份聚类结果排序图.png")

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
