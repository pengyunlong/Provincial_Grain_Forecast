from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "common"))

from clustering_utils import configure_chinese_font  # noqa: E402


GEOJSON_PATH = (
    ROOT_DIR.parents[2]
    / "区域供需平衡"
    / "Division_of_Grain_Production_and_Consumption_Zone"
    / "Data_Summary"
    / "china_provinces.json"
)


TASKS = [
    {
        "folder": "food_grain_clustering",
        "title": "31省口粮消费聚类中国地图",
    },
    {
        "folder": "feed_grain_clustering",
        "title": "31省饲料粮消费聚类中国地图",
    },
    {
        "folder": "population_clustering",
        "title": "31省人口结构聚类中国地图",
    },
    {
        "folder": "economy_clustering",
        "title": "31省经济指标聚类中国地图",
    },
]


COLOR_PALETTE = [
    "#4C78A8",
    "#F58518",
    "#54A24B",
    "#E45756",
    "#72B7B2",
    "#B279A2",
]


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
    rings: list[list[list[float]]] = []
    if geom_type == "Polygon":
        if coords:
            rings.append(coords[0])
    elif geom_type == "MultiPolygon":
        for polygon in coords:
            if polygon:
                rings.append(polygon[0])
    return rings


def read_geojson() -> list[dict]:
    data = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
    return data.get("features", [])


def plot_task_map(task: dict, features: list[dict]) -> None:
    task_dir = ROOT_DIR / task["folder"]
    result_path = task_dir / "table" / "省份聚类结果.csv"
    figure_dir = task_dir / "figure"
    figure_dir.mkdir(parents=True, exist_ok=True)

    result = pd.read_csv(result_path, encoding="utf-8-sig")
    result["map_name"] = result["省份"].map(normalize_province_name)
    cluster_info = (
        result[["map_name", "cluster", "cluster_label"]]
        .drop_duplicates(subset=["map_name"])
        .set_index("map_name")
        .to_dict(orient="index")
    )

    unique_clusters = sorted(result["cluster"].unique())
    color_map = {cluster: COLOR_PALETTE[i % len(COLOR_PALETTE)] for i, cluster in enumerate(unique_clusters)}

    configure_chinese_font()
    fig, ax = plt.subplots(figsize=(11, 9), dpi=220)
    ax.set_facecolor("#F7F8FA")

    min_x, min_y, max_x, max_y = 180, 90, -180, -90
    for feature in features:
        raw_name = feature.get("properties", {}).get("name", "")
        province_name = normalize_province_name(raw_name)
        info = cluster_info.get(province_name)
        facecolor = color_map[info["cluster"]] if info else "#D9DEE7"
        edgecolor = "#FFFFFF" if info else "#C8CED8"
        linewidth = 0.65 if info else 0.45

        for ring in iter_exterior_rings(feature.get("geometry", {})):
            if len(ring) < 3:
                continue
            xs = [point[0] for point in ring]
            ys = [point[1] for point in ring]
            min_x = min(min_x, min(xs))
            min_y = min(min_y, min(ys))
            max_x = max(max_x, max(xs))
            max_y = max(max_y, max(ys))
            patch = Polygon(
                ring,
                closed=True,
                facecolor=facecolor,
                edgecolor=edgecolor,
                linewidth=linewidth,
                joinstyle="round",
            )
            ax.add_patch(patch)

    ax.set_xlim(min_x - 2.0, max_x + 2.0)
    ax.set_ylim(min_y - 2.0, max_y + 2.0)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    counts = result.groupby(["cluster", "cluster_label"]).size().reset_index(name="省份数")
    legend_items = []
    for row in counts.sort_values("cluster").itertuples(index=False):
        label = f"类{row.cluster}: {row.cluster_label}（{row.省份数}省）"
        legend_items.append(Patch(facecolor=color_map[row.cluster], edgecolor="white", label=label))
    legend_items.append(Patch(facecolor="#D9DEE7", edgecolor="#C8CED8", label="未纳入31省范围"))

    ax.legend(
        handles=legend_items,
        loc="lower left",
        frameon=True,
        framealpha=0.94,
        fontsize=9,
        title="聚类结果",
        title_fontsize=10,
    )
    ax.set_title(task["title"], fontsize=16, pad=12)
    fig.tight_layout()
    fig.savefig(figure_dir / "中国地图聚类结果.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(f"缺少中国省级边界文件: {GEOJSON_PATH}")
    features = read_geojson()
    for task in TASKS:
        plot_task_map(task, features)


if __name__ == "__main__":
    main()
