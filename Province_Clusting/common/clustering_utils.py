from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd


PROVINCE_COLS = ["省份", "行政区划代码"]


class SimpleKMeansResult:
    def __init__(self, labels: np.ndarray, centers: np.ndarray, inertia: float) -> None:
        self.labels = labels
        self.cluster_centers_ = centers
        self.inertia_ = float(inertia)


def configure_chinese_font() -> None:
    local_font = Path(__file__).resolve().parent / "fonts" / "NotoSansCJKsc-Regular.otf"
    candidate_files = [
        str(local_font),
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for file_name in candidate_files:
        path = Path(file_name)
        if not path.exists():
            continue
        try:
            font_manager.fontManager.addfont(str(path))
            font_name = font_manager.FontProperties(fname=str(path)).get_name()
            plt.rcParams["font.family"] = [font_name]
            plt.rcParams["font.sans-serif"] = [font_name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            return
        except Exception:
            continue
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def linear_slope(years: Iterable[float], values: Iterable[float]) -> float:
    x = np.asarray(list(years), dtype=float)
    y = np.asarray(list(values), dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 2:
        return np.nan
    return float(np.polyfit(x[mask], y[mask], deg=1)[0])


def safe_rate(delta: float, base: float) -> float:
    if pd.isna(delta) or pd.isna(base) or abs(float(base)) < 1e-12:
        return np.nan
    return float(delta) / float(base)


def fill_panel_by_province(
    df: pd.DataFrame,
    province_col: str,
    year_col: str,
    value_cols: list[str],
) -> pd.DataFrame:
    out = df.sort_values([province_col, year_col]).copy()
    for col in value_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out[value_cols] = (
        out.groupby(province_col, group_keys=False)[value_cols]
        .apply(lambda g: g.interpolate(method="linear", limit_direction="both"))
        .ffill()
        .bfill()
    )
    return out


def build_series_features(
    df: pd.DataFrame,
    value_col: str,
    year_col: str = "年份",
    province_col: str = "省份",
    admin_col: str = "行政区划代码",
    prefix: str = "",
    include_std: bool = True,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for province, group in df.groupby(province_col, sort=True):
        group = group.sort_values(year_col).copy()
        values = pd.to_numeric(group[value_col], errors="coerce")
        years = pd.to_numeric(group[year_col], errors="coerce")
        valid = group[values.notna() & years.notna()].copy()
        if valid.empty:
            continue
        valid_values = pd.to_numeric(valid[value_col], errors="coerce")
        valid_years = pd.to_numeric(valid[year_col], errors="coerce")
        first_value = float(valid_values.iloc[0])
        latest_value = float(valid_values.iloc[-1])
        delta = latest_value - first_value
        row: dict[str, object] = {
            "省份": province,
            "行政区划代码": valid[admin_col].iloc[0] if admin_col in valid.columns else np.nan,
            f"{prefix}均值": float(valid_values.mean()),
            f"{prefix}最新年值": latest_value,
            f"{prefix}首年值": first_value,
            f"{prefix}变化量": delta,
            f"{prefix}变化率": safe_rate(delta, first_value),
            f"{prefix}线性趋势斜率": linear_slope(valid_years, valid_values),
        }
        if include_std:
            std = float(valid_values.std(ddof=0))
            mean = float(valid_values.mean())
            row[f"{prefix}标准差"] = std
            row[f"{prefix}变异系数"] = safe_rate(std, mean)
        rows.append(row)
    return pd.DataFrame(rows)


def prepare_features_for_clustering(
    feature_df: pd.DataFrame,
    exclude_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    exclude = set(PROVINCE_COLS + (exclude_cols or []))
    numeric_cols = [
        col
        for col in feature_df.columns
        if col not in exclude and pd.api.types.is_numeric_dtype(feature_df[col])
    ]
    clean = feature_df.copy()
    for col in numeric_cols:
        clean[col] = pd.to_numeric(clean[col], errors="coerce")
    all_na_cols = [col for col in numeric_cols if clean[col].isna().all()]
    numeric_cols = [col for col in numeric_cols if col not in all_na_cols]
    for col in numeric_cols:
        if clean[col].isna().any():
            clean[col] = clean[col].fillna(clean[col].median())
    if not numeric_cols:
        raise ValueError("没有可用于聚类的数值特征。")
    if clean[numeric_cols].isna().any().any():
        missing = clean[numeric_cols].columns[clean[numeric_cols].isna().any()].tolist()
        raise ValueError(f"聚类特征仍存在缺失值: {missing}")
    return clean, numeric_cols


def standardize_values(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    means = np.nanmean(values, axis=0)
    stds = np.nanstd(values, axis=0)
    stds[stds < 1e-12] = 1.0
    return (values - means) / stds, means, stds


def pairwise_distances(values: np.ndarray) -> np.ndarray:
    diff = values[:, None, :] - values[None, :, :]
    return np.sqrt(np.sum(diff * diff, axis=2))


def fit_simple_kmeans(
    values: np.ndarray,
    n_clusters: int,
    random_state: int = 42,
    n_init: int = 80,
    max_iter: int = 300,
) -> SimpleKMeansResult:
    rng = np.random.default_rng(random_state)
    n_samples = values.shape[0]
    best: SimpleKMeansResult | None = None
    for _ in range(n_init):
        center_idx = rng.choice(n_samples, size=n_clusters, replace=False)
        centers = values[center_idx].copy()
        labels = np.zeros(n_samples, dtype=int)
        for _iteration in range(max_iter):
            distances = np.sum((values[:, None, :] - centers[None, :, :]) ** 2, axis=2)
            new_labels = distances.argmin(axis=1)
            new_centers = centers.copy()
            for cluster in range(n_clusters):
                members = values[new_labels == cluster]
                if len(members) == 0:
                    farthest = np.argmax(distances.min(axis=1))
                    new_centers[cluster] = values[farthest]
                else:
                    new_centers[cluster] = members.mean(axis=0)
            if np.array_equal(new_labels, labels) and np.allclose(new_centers, centers):
                labels = new_labels
                centers = new_centers
                break
            labels = new_labels
            centers = new_centers
        final_distances = np.sum((values - centers[labels]) ** 2, axis=1)
        inertia = float(final_distances.sum())
        candidate = SimpleKMeansResult(labels.copy(), centers.copy(), inertia)
        if best is None or candidate.inertia_ < best.inertia_:
            best = candidate
    if best is None:
        raise ValueError("KMeans 未能生成结果。")
    return best


def silhouette_score_np(values: np.ndarray, labels: np.ndarray) -> float:
    unique_labels = np.unique(labels)
    if len(unique_labels) < 2:
        return np.nan
    distances = pairwise_distances(values)
    scores = []
    for i in range(values.shape[0]):
        same = labels == labels[i]
        same[i] = False
        a = distances[i, same].mean() if same.any() else 0.0
        b_candidates = []
        for label in unique_labels:
            if label == labels[i]:
                continue
            other = labels == label
            if other.any():
                b_candidates.append(distances[i, other].mean())
        b = min(b_candidates) if b_candidates else 0.0
        denom = max(a, b)
        scores.append(0.0 if denom < 1e-12 else (b - a) / denom)
    return float(np.mean(scores))


def calinski_harabasz_score_np(values: np.ndarray, labels: np.ndarray, centers: np.ndarray) -> float:
    n_samples = values.shape[0]
    unique_labels = np.unique(labels)
    n_clusters = len(unique_labels)
    if n_clusters < 2 or n_clusters >= n_samples:
        return np.nan
    overall = values.mean(axis=0)
    between = 0.0
    within = 0.0
    for label in unique_labels:
        members = values[labels == label]
        center = centers[label]
        between += len(members) * float(np.sum((center - overall) ** 2))
        within += float(np.sum((members - center) ** 2))
    if within < 1e-12:
        return np.nan
    return float((between / (n_clusters - 1)) / (within / (n_samples - n_clusters)))


def davies_bouldin_score_np(values: np.ndarray, labels: np.ndarray, centers: np.ndarray) -> float:
    unique_labels = np.unique(labels)
    n_clusters = len(unique_labels)
    if n_clusters < 2:
        return np.nan
    scatter = {}
    for label in unique_labels:
        members = values[labels == label]
        center = centers[label]
        scatter[label] = float(np.sqrt(np.sum((members - center) ** 2, axis=1)).mean()) if len(members) else 0.0
    db_values = []
    for i in unique_labels:
        ratios = []
        for j in unique_labels:
            if i == j:
                continue
            distance = float(np.sqrt(np.sum((centers[i] - centers[j]) ** 2)))
            if distance < 1e-12:
                ratios.append(np.inf)
            else:
                ratios.append((scatter[i] + scatter[j]) / distance)
        db_values.append(max(ratios))
    return float(np.mean(db_values))


def evaluate_k_values(
    scaled_values: np.ndarray,
    k_values: Iterable[int] = range(2, 7),
    random_state: int = 42,
) -> pd.DataFrame:
    rows = []
    n_samples = scaled_values.shape[0]
    for k in k_values:
        if k >= n_samples:
            continue
        model = fit_simple_kmeans(scaled_values, n_clusters=k, random_state=random_state)
        labels = model.labels
        rows.append(
            {
                "K": k,
                "inertia": float(model.inertia_),
                "silhouette_score": silhouette_score_np(scaled_values, labels),
                "calinski_harabasz_score": calinski_harabasz_score_np(
                    scaled_values, labels, model.cluster_centers_
                ),
                "davies_bouldin_score": davies_bouldin_score_np(
                    scaled_values, labels, model.cluster_centers_
                ),
            }
        )
    return pd.DataFrame(rows)


def choose_k(evaluation_df: pd.DataFrame) -> int:
    if evaluation_df.empty:
        raise ValueError("K 值评估表为空。")
    ranked = evaluation_df.sort_values(
        ["silhouette_score", "calinski_harabasz_score", "davies_bouldin_score"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    best_score = float(ranked.loc[0, "silhouette_score"])
    close = evaluation_df[evaluation_df["silhouette_score"] >= best_score - 0.03].copy()
    preferred = close[close["K"].isin([3, 4])].sort_values(
        ["silhouette_score", "K"], ascending=[False, True]
    )
    if not preferred.empty:
        return int(preferred.iloc[0]["K"])
    return int(ranked.loc[0, "K"])


def cluster_feature_table(
    feature_df: pd.DataFrame,
    output_table_dir: Path,
    default_k: int | None = None,
    random_state: int = 42,
) -> dict[str, object]:
    clean, numeric_cols = prepare_features_for_clustering(feature_df)
    scaled_values, _means, _stds = standardize_values(clean[numeric_cols].to_numpy(dtype=float))
    scaled_df = clean[PROVINCE_COLS].copy()
    scaled_df[numeric_cols] = scaled_values

    evaluation_df = None
    if default_k is None:
        evaluation_df = evaluate_k_values(scaled_values, random_state=random_state)
        selected_k = choose_k(evaluation_df)
    else:
        selected_k = int(default_k)
    if selected_k < 2 or selected_k >= scaled_values.shape[0]:
        raise ValueError(f"K 值不合法: {selected_k}")
    model = fit_simple_kmeans(scaled_values, n_clusters=selected_k, random_state=random_state)
    labels = model.labels

    result_df = clean[PROVINCE_COLS].copy()
    result_df["cluster"] = labels

    scaled_centers = pd.DataFrame(model.cluster_centers_, columns=numeric_cols)
    scaled_centers.insert(0, "cluster", range(selected_k))
    original_centers = clean.copy()
    original_centers["cluster"] = labels
    original_centers = original_centers.groupby("cluster")[numeric_cols].mean().reset_index()

    output_table_dir.mkdir(parents=True, exist_ok=True)
    scaled_df.to_csv(output_table_dir / "省份聚类标准化特征表.csv", index=False, encoding="utf-8-sig")
    scaled_centers.to_csv(output_table_dir / "聚类中心_标准化.csv", index=False, encoding="utf-8-sig")
    original_centers.to_csv(output_table_dir / "聚类中心_原始特征均值.csv", index=False, encoding="utf-8-sig")

    return {
        "clean_feature_df": clean,
        "scaled_df": scaled_df,
        "numeric_cols": numeric_cols,
        "scaled_values": scaled_values,
        "labels": labels,
        "result_df": result_df,
        "evaluation_df": evaluation_df,
        "selected_k": selected_k,
        "scaled_centers": scaled_centers,
        "original_centers": original_centers,
    }


def make_cluster_labels(
    result_df: pd.DataFrame,
    feature_df: pd.DataFrame,
    level_col: str,
    trend_col: str | None = None,
    high_word: str = "高水平",
    mid_word: str = "中等水平",
    low_word: str = "低水平",
) -> pd.DataFrame:
    merged = result_df.merge(feature_df, on=PROVINCE_COLS, how="left")
    centers = merged.groupby("cluster")[level_col].mean()
    q_low = centers.quantile(0.33)
    q_high = centers.quantile(0.67)
    label_map = {}
    for cluster, value in centers.items():
        if value >= q_high:
            level = high_word
        elif value <= q_low:
            level = low_word
        else:
            level = mid_word
        if trend_col and trend_col in merged.columns:
            trend = merged.loc[merged["cluster"] == cluster, trend_col].mean()
            if trend > 0.5:
                direction = "上升型"
            elif trend < -0.5:
                direction = "下降型"
            else:
                direction = "稳定型"
            label_map[cluster] = f"{level}-{direction}"
        else:
            label_map[cluster] = level
    out = merged.copy()
    out["cluster_label"] = out["cluster"].map(label_map)
    return out


def add_summary_column(df: pd.DataFrame, summary_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    parts = []
    for _, row in out.iterrows():
        items = []
        for col in summary_cols:
            if col not in out.columns:
                continue
            value = row[col]
            if pd.isna(value):
                continue
            if isinstance(value, (int, float, np.integer, np.floating)):
                items.append(f"{col}={value:.2f}")
            else:
                items.append(f"{col}={value}")
        parts.append("；".join(items))
    out["核心特征摘要"] = parts
    return out


def plot_pca_scatter(
    scaled_values: np.ndarray,
    result_df: pd.DataFrame,
    title: str,
    output_path: Path,
) -> None:
    configure_chinese_font()
    centered = scaled_values - scaled_values.mean(axis=0)
    _u, singular_values, vt = np.linalg.svd(centered, full_matrices=False)
    components = vt[:2].T
    coords = centered @ components
    explained = (singular_values**2) / max(scaled_values.shape[0] - 1, 1)
    total = explained.sum()
    explained_ratio = explained[:2] / total if total > 1e-12 else np.array([0.0, 0.0])
    plot_df = result_df.copy().reset_index(drop=True)
    plot_df["PC1"] = coords[:, 0]
    plot_df["PC2"] = coords[:, 1]

    fig, ax = plt.subplots(figsize=(11, 8), dpi=180)
    scatter = ax.scatter(
        plot_df["PC1"],
        plot_df["PC2"],
        c=plot_df["cluster"],
        cmap="tab10",
        s=90,
        alpha=0.88,
        edgecolor="#333333",
        linewidth=0.5,
    )
    for _, row in plot_df.iterrows():
        ax.annotate(row["省份"], (row["PC1"], row["PC2"]), xytext=(4, 3), textcoords="offset points", fontsize=8)
    ax.set_title(title, fontsize=15)
    ax.set_xlabel(f"PC1 ({explained_ratio[0] * 100:.1f}%)")
    ax.set_ylabel(f"PC2 ({explained_ratio[1] * 100:.1f}%)")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.35)
    legend = ax.legend(*scatter.legend_elements(), title="聚类", loc="best", fontsize=9)
    ax.add_artist(legend)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_center_heatmap(
    center_df: pd.DataFrame,
    title: str,
    output_path: Path,
) -> None:
    configure_chinese_font()
    data = center_df.set_index("cluster")
    fig_width = max(10, min(24, 0.42 * len(data.columns)))
    fig, ax = plt.subplots(figsize=(fig_width, 5.8), dpi=180)
    im = ax.imshow(data.values, aspect="auto", cmap="RdBu_r")
    ax.set_title(title, fontsize=15)
    ax.set_xticks(np.arange(len(data.columns)))
    ax.set_xticklabels(data.columns, rotation=55, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(data.index)))
    ax.set_yticklabels([f"类{idx}" for idx in data.index], fontsize=10)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.ax.set_ylabel("标准化中心值", rotation=90)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_cluster_counts(result_df: pd.DataFrame, title: str, output_path: Path) -> None:
    configure_chinese_font()
    counts = result_df.groupby(["cluster", "cluster_label"]).size().reset_index(name="省份数量")
    labels = [f"{row.cluster}: {row.cluster_label}" for row in counts.itertuples(index=False)]
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=180)
    bars = ax.bar(labels, counts["省份数量"], color="#4C78A8")
    ax.set_title(title, fontsize=15)
    ax.set_ylabel("省份数量")
    ax.set_ylim(0, max(counts["省份数量"].max() + 2, 5))
    ax.bar_label(bars, padding=3, fontsize=10)
    ax.tick_params(axis="x", labelrotation=20)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_sorted_results(
    result_df: pd.DataFrame,
    value_col: str,
    title: str,
    output_path: Path,
) -> None:
    configure_chinese_font()
    df = result_df.sort_values(value_col, ascending=True).copy()
    fig_height = max(7, 0.28 * len(df))
    fig, ax = plt.subplots(figsize=(10, fig_height), dpi=180)
    colors = plt.get_cmap("tab10")(df["cluster"].to_numpy() % 10)
    ax.barh(df["省份"], df[value_col], color=colors)
    ax.set_title(title, fontsize=15)
    ax.set_xlabel(value_col)
    ax.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.35)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def write_quality_report(
    result_df: pd.DataFrame,
    feature_df: pd.DataFrame,
    numeric_cols: list[str],
    evaluation_df: pd.DataFrame | None,
    selected_k: int,
    output_path: Path,
    extra_checks: dict[str, bool] | None = None,
) -> None:
    rows = [
        {"检查项": "聚类结果覆盖31个省份", "通过": result_df["省份"].nunique() == 31},
        {"检查项": "不允许出现空聚类", "通过": result_df["cluster"].nunique() == selected_k},
        {"检查项": "聚类特征无缺失值", "通过": not feature_df[numeric_cols].isna().any().any()},
    ]
    if extra_checks:
        rows.extend({"检查项": key, "通过": value} for key, value in extra_checks.items())
    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
