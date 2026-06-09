import json
import pandas as pd
from pathlib import Path

ROOT = Path("/media/sf_/粮食需求/Provincial_Grain_Forecast/Province_Clusting")
tasks = ["economy_clustering", "feed_grain_clustering", "food_grain_clustering", "population_clustering"]

# We will collect the data here
data = {}

# 1. Load GeoJSON
geojson_path = ROOT / "common" / "china_provinces_online.json"
if geojson_path.exists():
    with open(geojson_path, "r", encoding="utf-8") as f:
        data["geojson"] = json.load(f)
else:
    print("GeoJSON not found!")
    data["geojson"] = {}

# 2. Load clustering results and metadata for each task
data["tasks"] = {}

for t in tasks:
    t_data = {}
    
    # Load results
    results_path = ROOT / t / "table" / "省份聚类结果.csv"
    if results_path.exists():
        df_res = pd.read_csv(results_path)
        # Convert NaN to empty or appropriate values
        df_res = df_res.fillna("")
        t_data["results"] = df_res.to_dict(orient="records")
        t_data["columns"] = list(df_res.columns)
    else:
        print(f"Results not found for {t}")
        t_data["results"] = []
        t_data["columns"] = []
        
    # Load cluster centers
    centers_path = ROOT / t / "table" / "聚类中心_原始特征均值.csv"
    if centers_path.exists():
        df_cen = pd.read_csv(centers_path)
        df_cen = df_cen.fillna("")
        t_data["centers"] = df_cen.to_dict(orient="records")
        t_data["center_columns"] = list(df_cen.columns)
    else:
        print(f"Centers not found for {t}")
        t_data["centers"] = []
        t_data["center_columns"] = []
        
    # Load description
    desc_path = ROOT / t / "table" / "聚类结果说明.csv"
    if desc_path.exists():
        df_desc = pd.read_csv(desc_path)
        df_desc = df_desc.fillna("")
        t_data["description"] = df_desc.to_dict(orient="records")[0] if len(df_desc) > 0 else {}
    else:
        print(f"Description not found for {t}")
        t_data["description"] = {}
        
    data["tasks"][t] = t_data

print("Successfully compiled data keys:", data.keys())
print("Tasks compiled:", list(data["tasks"].keys()))
