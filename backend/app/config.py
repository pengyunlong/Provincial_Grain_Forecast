from pathlib import Path

# 项目根目录：/media/sf_Provincial_Grain_Forecast
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 数据源路径
CLUSTERING_DIR = PROJECT_ROOT / "Province_Clusting" / "combined_clustering"
TABLE_DIR = CLUSTERING_DIR / "table"

# 统一使用的 GeoJSON 地图数据路径
GEOJSON_PATH = PROJECT_ROOT / "Province_Clusting" / "common" / "china_provinces_online.json"
