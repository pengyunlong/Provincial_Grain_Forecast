import json
import pandas as pd
from pathlib import Path

ROOT = Path("/media/sf_/粮食需求/Provincial_Grain_Forecast/Province_Clusting")

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

# Load GeoJSON names
geojson_path = ROOT / "common" / "china_provinces_online.json"
with open(geojson_path, "r", encoding="utf-8") as f:
    geojson = json.load(f)

geojson_names = set()
for feature in geojson.get("features", []):
    raw_name = feature.get("properties", {}).get("name", "")
    norm_name = normalize_province_name(raw_name)
    geojson_names.add(norm_name)

# Load CSV names from one of the tasks
csv_path = ROOT / "economy_clustering" / "table" / "省份聚类结果.csv"
df = pd.read_csv(csv_path)
csv_names = set(df["省份"].unique())

print("CSV Province Names (31):", sorted(list(csv_names)))
print("Unmatched in GeoJSON:", csv_names - geojson_names)
print("Unmatched in CSV:", geojson_names - csv_names)
