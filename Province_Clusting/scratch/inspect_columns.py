import pandas as pd
from pathlib import Path

ROOT = Path("/media/sf_/粮食需求/Provincial_Grain_Forecast/Province_Clusting")
tasks = ["economy_clustering", "feed_grain_clustering", "food_grain_clustering", "population_clustering"]

for t in tasks:
    p = ROOT / t / "table" / "省份聚类结果.csv"
    if p.exists():
        df = pd.read_csv(p)
        print(f"Task: {t}")
        print(f"Columns: {list(df.columns[:15])} ... total {len(df.columns)} columns")
        print(f"Clusters: {df['cluster'].unique()}")
        print("-" * 50)
