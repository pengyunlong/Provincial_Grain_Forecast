import json
import pandas as pd
from pathlib import Path

ROOT = Path("/media/sf_/粮食需求/Provincial_Grain_Forecast/Province_Clusting")
tasks = ["economy_clustering", "feed_grain_clustering", "food_grain_clustering", "population_clustering"]

# Radar features mapping (feature_name, display_label)
RADAR_FEATURES = {
    "economy_clustering": [
        ("地区生产总值_最新年值", "GDP最新值 (亿元)"),
        ("地区生产总值_线性趋势斜率", "GDP趋势斜率 (亿元/年)"),
        ("人均可支配收入_地区总计_最新年值", "人均可支配收入 (元)"),
        ("人均消费支出_地区总计_最新年值", "人均消费支出 (元)"),
        ("地区居民消费价格指数_总指数_均值", "总CPI均值"),
        ("地区居民消费价格指数_粮食_均值", "粮食CPI均值")
    ],
    "population_clustering": [
        ("总人口_最新年值", "总人口最新值 (万人)"),
        ("城镇化率_最新年值", "城镇化率 (最新)"),
        ("65岁及以上占比_最新年值", "65岁及以上占比"),
        ("总人口_线性趋势斜率", "总人口趋势斜率 (万人/年)"),
        ("0-14岁占比_最新年值", "0-14岁占比"),
        ("平均家庭规模_最新年值", "平均家庭规模 (人)")
    ],
    "food_grain_clustering": [
        ("口粮最新年值", "口粮最新值 (kg/人)"),
        ("口粮均值", "口粮均值 (kg/人)"),
        ("口粮变化量", "口粮变化量 (kg/人)"),
        ("口粮线性趋势斜率", "口粮趋势斜率"),
        ("口粮变异系数", "口粮变异系数")
    ],
    "feed_grain_clustering": [
        ("饲料粮最新年值", "饲料粮最新值 (kg/人)"),
        ("饲料粮均值", "饲料粮均值 (kg/人)"),
        ("饲料粮变化量", "饲料粮变化量 (kg/人)"),
        ("饲料粮线性趋势斜率", "饲料粮趋势斜率"),
        ("饲料粮变异系数", "饲料粮变异系数")
    ]
}

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

# 1. Load GeoJSON and normalize names
geojson_path = ROOT / "common" / "china_provinces_online.json"
with open(geojson_path, "r", encoding="utf-8") as f:
    china_geojson = json.load(f)

for feature in china_geojson.get("features", []):
    raw_name = feature.get("properties", {}).get("name", "")
    feature["properties"]["name"] = normalize_province_name(raw_name)

# 2. Extract Province Clustering data
prov_clusters = {}  # prov_name -> task_name -> dict
national_averages = {}  # task_name -> feature -> value
feature_ranges = {}  # task_name -> feature -> {min, max}
cluster_centers = {}  # task_name -> cluster_id -> feature -> value
task_metadata = {}  # task_name -> dict

for t in tasks:
    # Read CSV results
    df_res = pd.read_csv(ROOT / t / "table" / "省份聚类结果.csv")
    df_res = df_res.fillna(0)
    
    # Store ranges for radar features
    feature_ranges[t] = {}
    for feat, label in RADAR_FEATURES[t]:
        val_min = float(df_res[feat].min())
        val_max = float(df_res[feat].max())
        feature_ranges[t][feat] = {"min": val_min, "max": val_max}
        
    # Store national averages
    national_averages[t] = {}
    numeric_cols = df_res.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        if col in ["行政区划代码", "cluster"]:
            continue
        national_averages[t][col] = float(df_res[col].mean())
        
    # Store province-level cluster assignments and all features
    for _, row in df_res.iterrows():
        prov = row["省份"]
        if prov not in prov_clusters:
            prov_clusters[prov] = {
                "name": prov,
                "code": int(row["行政区划代码"]) if "行政区划代码" in row and row["行政区划代码"] else 0,
                "tasks": {}
            }
        
        prov_task_data = {}
        prov_task_data["cluster"] = int(row["cluster"])
        prov_task_data["cluster_label"] = row["cluster_label"]
        prov_task_data["summary"] = row["核心特征摘要"]
        
        # Collect all numeric values for this province in this task
        prov_task_data["metrics"] = {}
        for col in numeric_cols:
            if col in ["行政区划代码", "cluster"]:
                continue
            prov_task_data["metrics"][col] = float(row[col])
            
        prov_clusters[prov]["tasks"][t] = prov_task_data
        
    # Read cluster centers
    df_cen = pd.read_csv(ROOT / t / "table" / "聚类中心_原始特征均值.csv")
    df_cen = df_cen.fillna(0)
    cluster_centers[t] = {}
    for _, row in df_cen.iterrows():
        cid = int(row["cluster"])
        cluster_centers[t][cid] = {}
        for col in df_cen.columns:
            if col == "cluster":
                continue
            cluster_centers[t][cid][col] = float(row[col])
            
    # Read description / metadata
    df_desc = pd.read_csv(ROOT / t / "table" / "聚类结果说明.csv")
    df_desc = df_desc.fillna("")
    if len(df_desc) > 0:
        row_desc = df_desc.iloc[0]
        task_metadata[t] = {
            "name": row_desc.get("聚类对象", t),
            "time_range": row_desc.get("时间范围", "2000-2024"),
            "k": int(row_desc.get("默认K值", 4)),
            "features_desc": row_desc.get("核心特征", ""),
            "exclude_rural": str(row_desc.get("是否排除分城乡字段", ""))
        }
    else:
        task_metadata[t] = {
            "name": t,
            "time_range": "2000-2024",
            "k": 4,
            "features_desc": "",
            "exclude_rural": ""
        }

# 3. Compute Sankey flows
sankey_nodes = set()
task_prefixes = {
    "economy_clustering": "经济",
    "population_clustering": "人口",
    "food_grain_clustering": "口粮",
    "feed_grain_clustering": "饲料"
}

node_names = {}  # task -> cluster_id -> node_name
for t in tasks:
    node_names[t] = {}
    for cid, center_data in cluster_centers[t].items():
        # Get label from results
        label = ""
        for prov, p_data in prov_clusters.items():
            if t in p_data["tasks"] and p_data["tasks"][t]["cluster"] == cid:
                label = p_data["tasks"][t]["cluster_label"]
                break
        node_name = f"{task_prefixes[t]}: 类{cid} ({label})"
        node_names[t][cid] = node_name
        sankey_nodes.add(node_name)

link_counts = {}  # (source, target) -> [provinces]
for prov, p_data in prov_clusters.items():
    # Economy -> Population
    e_node = node_names["economy_clustering"][p_data["tasks"]["economy_clustering"]["cluster"]]
    p_node = node_names["population_clustering"][p_data["tasks"]["population_clustering"]["cluster"]]
    key1 = (e_node, p_node)
    link_counts.setdefault(key1, []).append(prov)
    
    # Population -> Food Grain
    fo_node = node_names["food_grain_clustering"][p_data["tasks"]["food_grain_clustering"]["cluster"]]
    key2 = (p_node, fo_node)
    link_counts.setdefault(key2, []).append(prov)
    
    # Food Grain -> Feed Grain
    fe_node = node_names["feed_grain_clustering"][p_data["tasks"]["feed_grain_clustering"]["cluster"]]
    key3 = (fo_node, fe_node)
    link_counts.setdefault(key3, []).append(prov)

sankey_links = []
for (src, tgt), provs in link_counts.items():
    sankey_links.append({
        "source": src,
        "target": tgt,
        "value": len(provs),
        "provinces": provs
    })

sankey_nodes_list = [{"name": n} for n in sorted(list(sankey_nodes))]

# 4. Save data structures as JSON variables to be written into the HTML template
compiled_data = {
    "tasks": tasks,
    "task_metadata": task_metadata,
    "prov_clusters": prov_clusters,
    "national_averages": national_averages,
    "feature_ranges": feature_ranges,
    "cluster_centers": cluster_centers,
    "radar_features": RADAR_FEATURES,
    "sankey": {
        "nodes": sankey_nodes_list,
        "links": sankey_links
    }
}

print("Data structures ready. Compiling into HTML...")

# Write JS data
data_js = f"""
const chinaGeoJSON = {json.dumps(china_geojson, ensure_ascii=False)};
const dashboardData = {json.dumps(compiled_data, ensure_ascii=False)};
"""

# Let's inspect the compiled JSON structure size
print("JSON data size in chars:", len(data_js))
with open(ROOT / "scratch" / "data.js", "w", encoding="utf-8") as f:
    f.write(data_js)
