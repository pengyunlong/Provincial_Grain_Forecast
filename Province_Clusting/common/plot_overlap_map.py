from __future__ import annotations

import json
from pathlib import Path
import sys
import urllib.request
import itertools

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "common"))

from clustering_utils import configure_chinese_font  # noqa: E402

GEOJSON_URL = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"
GEOJSON_LOCAL_PATH = ROOT_DIR / "common" / "china_provinces_online.json"

TASKS = [
    "food_grain_clustering",
    "feed_grain_clustering",
    "population_clustering",
    "economy_clustering"
]

COLOR_PALETTE = [
    "#3b82f6",  # Cluster 0 - Blue
    "#f58518",  # Cluster 1 - Orange
    "#10b981",  # Cluster 2 - Green
    "#ef4444",  # Cluster 3 - Red
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

def get_geojson_features() -> list[dict]:
    if not GEOJSON_LOCAL_PATH.exists():
        print(f"Downloading GeoJSON from {GEOJSON_URL}...")
        try:
            with urllib.request.urlopen(GEOJSON_URL) as response:
                content = response.read().decode("utf-8")
                GEOJSON_LOCAL_PATH.write_text(content, encoding="utf-8")
        except Exception as e:
            print(f"Failed to download GeoJSON: {e}")
            raise e
    
    data = json.loads(GEOJSON_LOCAL_PATH.read_text(encoding="utf-8"))
    return data.get("features", [])

def main() -> None:
    # 1. Load results and align
    dfs = {}
    for t in TASKS:
        p = ROOT_DIR / t / "table" / "省份聚类结果.csv"
        if not p.exists():
            raise FileNotFoundError(f"Missing clustering result for {t} at {p}")
        df = pd.read_csv(p).set_index("省份")
        dfs[t] = df

    baseline = TASKS[0]
    df_base = dfs[baseline].sort_index()
    aligned_dfs = {baseline: df_base["cluster"]}

    # Perform alignment to baseline (Food Grain)
    for t in TASKS[1:]:
        df_t = dfs[t].sort_index()
        best_overlap = -1
        best_perm = None
        for perm in itertools.permutations([0, 1, 2, 3]):
            mapped = df_t["cluster"].map(lambda x: perm[x])
            overlap = (df_base["cluster"] == mapped).sum()
            if overlap > best_overlap:
                best_overlap = overlap
                best_perm = perm
        print(f"Aligned {t} to baseline. Max overlap: {best_overlap}/31. Permutation: {best_perm}")
        aligned_dfs[t] = df_t["cluster"].map(lambda x: best_perm[x])

    aligned_df = pd.DataFrame(aligned_dfs)

    # Calculate consensus and overlap counts
    def get_consensus_info(row):
        counts = row[TASKS].value_counts()
        majority_cluster = counts.index[0]
        majority_count = counts.iloc[0]
        return pd.Series([majority_cluster, majority_count])

    aligned_df[["consensus_cluster", "consensus_count"]] = aligned_df.apply(get_consensus_info, axis=1)
    aligned_df.to_csv(ROOT_DIR / "table" / "四类聚类重叠分析结果.csv", encoding="utf-8-sig")
    print("Overlap analysis result table saved.")

    # 2. Get GeoJSON map data
    features = get_geojson_features()

    # 3. Plot Map
    configure_chinese_font()
    fig, ax = plt.subplots(figsize=(12, 10), dpi=220)
    ax.set_facecolor("#080c14")  # Dark background to match our visual design
    fig.patch.set_facecolor("#080c14")

    # Normalized mapping dictionary
    aligned_df["map_name"] = aligned_df.index.map(normalize_province_name)
    overlap_info = aligned_df.set_index("map_name")[["consensus_cluster", "consensus_count"]].to_dict(orient="index")

    min_x, min_y, max_x, max_y = 180, 90, -180, -90
    for feature in features:
        raw_name = feature.get("properties", {}).get("name", "")
        province_name = normalize_province_name(raw_name)
        
        info = overlap_info.get(province_name)
        if info:
            cluster_id = int(info["consensus_cluster"])
            count = int(info["consensus_count"])
            
            # Determine color & opacity based on consensus count
            base_color = COLOR_PALETTE[cluster_id]
            if count == 4:
                facecolor = base_color  # Solid color
                linewidth = 1.0
                edgecolor = "#FFFFFF"
            elif count == 3:
                # Add transparency to base color
                rgb = matplotlib.colors.to_rgb(base_color)
                facecolor = (rgb[0], rgb[1], rgb[2], 0.55)  # 55% opacity
                linewidth = 0.7
                edgecolor = (1.0, 1.0, 1.0, 0.7)
            else:
                # 2 or fewer tasks agree: Inconsistent/Split
                facecolor = "#273549"  # Dark gray-blue
                linewidth = 0.5
                edgecolor = (1.0, 1.0, 1.0, 0.3)
        else:
            facecolor = "#151c27"  # Not in 31 provinces (e.g. Taiwan, HK, Macau)
            linewidth = 0.4
            edgecolor = (1.0, 1.0, 1.0, 0.1)

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

    # Focus axis limits around China
    ax.set_xlim(min_x - 1.0, max_x + 1.0)
    ax.set_ylim(min_y - 1.5, max_y + 1.5)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    # Legend Items
    legend_items = [
        Patch(facecolor=COLOR_PALETTE[0], edgecolor="white", label="类0: 低水平-下降型共识 (如天津,新疆,西南地区)"),
        Patch(facecolor=COLOR_PALETTE[1], edgecolor="white", label="类1: 高水平-下降型共识"),
        Patch(facecolor=COLOR_PALETTE[2], edgecolor="white", label="类2: 中等水平-下降型共识 (如甘肃,新疆等区域)"),
        Patch(facecolor=COLOR_PALETTE[3], edgecolor="white", label="类3: 中等水平-上升型共识 (东北三省,黄淮海及长江流域)"),
        Patch(facecolor="none", edgecolor="none", label=""),  # Spacer
        Patch(facecolor="#555555", edgecolor="white", label="【填色浓度指示】"),
        Patch(facecolor="#3b82f6", edgecolor="white", label="完全重叠（4个任务均在同类）"),
        Patch(facecolor=(0.23, 0.51, 0.96, 0.55), edgecolor=(1.0, 1.0, 1.0, 0.7), label="高度重叠（3个任务在同类）"),
        Patch(facecolor="#273549", edgecolor=(1.0, 1.0, 1.0, 0.3), label="低度重叠/分歧（仅2个及以下任务在同类）"),
        Patch(facecolor="#151c27", edgecolor=(1.0, 1.0, 1.0, 0.1), label="未纳入31省范围"),
    ]

    leg = ax.legend(
        handles=legend_items,
        loc="lower left",
        frameon=True,
        framealpha=0.85,
        facecolor="#0d1522",
        edgecolor=(1.0, 1.0, 1.0, 0.1),
        labelcolor="#ffffff",
        fontsize=8.5,
        title="四类聚类重叠共识分类 (K=4)",
        title_fontsize=9.5
    )
    leg.get_title().set_color('#ffffff')

    # Set Title
    ax.text(
        0.5, 0.96,
        "31省口粮/饲料粮/人口/经济聚类空间重叠与共识分析地图",
        transform=ax.transAxes,
        color="#ffffff",
        fontsize=15,
        fontweight="bold",
        ha="center"
    )
    ax.text(
        0.5, 0.92,
        "基于最大重叠度对齐各维度聚类簇后的省份共识性特征图景",
        transform=ax.transAxes,
        color="#94a3b8",
        fontsize=10.5,
        ha="center"
    )

    fig.tight_layout()
    output_path = ROOT_DIR / "四类聚类省份重叠地图.png"
    fig.savefig(output_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Map image successfully created at {output_path}")

if __name__ == "__main__":
    main()
