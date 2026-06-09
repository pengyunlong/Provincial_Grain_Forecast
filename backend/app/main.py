from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from typing import List
import json

from app.config import TABLE_DIR, GEOJSON_PATH
from app.schemas import ProvinceClusteringData, ProvinceMetrics, AblationResponse, AblationMetric, ProvinceStability

app = FastAPI(title="Provincial Grain Forecast Clustering Dashboard API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_code(code_val) -> str:
    try:
        return f"{int(float(code_val)):06d}"
    except (ValueError, TypeError):
        return str(code_val).strip()

def clean_float(val) -> float:
    if pd.isna(val) or val is None or (isinstance(val, float) and np.isnan(val)):
        return 0.0
    return float(val)

def clean_int(val) -> int:
    if pd.isna(val) or val is None or (isinstance(val, float) and np.isnan(val)):
        return 0
    return int(val)

@app.get("/api/provinces", response_model=List[ProvinceClusteringData])
def get_provinces():
    try:
        # Load main clustering results
        results_path = TABLE_DIR / "省份联合聚类结果.csv"
        if not results_path.exists():
            raise HTTPException(status_code=404, detail=f"Results file not found at {results_path}")
        df_results = pd.read_csv(results_path)

        # Load labels wide table
        labels_path = TABLE_DIR / "六组实验省份聚类标签宽表.csv"
        if not labels_path.exists():
            raise HTTPException(status_code=404, detail=f"Labels wide table not found at {labels_path}")
        df_labels = pd.read_csv(labels_path)

        # Load stability table
        stability_path = TABLE_DIR / "省份分组稳定性.csv"
        if not stability_path.exists():
            raise HTTPException(status_code=404, detail=f"Stability table not found at {stability_path}")
        df_stability = pd.read_csv(stability_path)

        # Format codes for merge consistency
        df_results['code'] = df_results['行政区划代码'].apply(format_code)
        df_labels['code'] = df_labels['行政区划代码'].apply(format_code)
        df_stability['code'] = df_stability['行政区划代码'].apply(format_code)

        # Build maps for labels and stability
        labels_map = {}
        for _, row in df_labels.iterrows():
            code = row['code']
            labels_map[code] = {
                "M0": clean_int(row.get('M0')),
                "C1": clean_int(row.get('C1')),
                "C2": clean_int(row.get('C2')),
                "C3": clean_int(row.get('C3')),
                "C4": clean_int(row.get('C4')),
                "C5": clean_int(row.get('C5'))
            }

        stability_map = {}
        for _, row in df_stability.iterrows():
            code = row['code']
            stability_map[code] = clean_int(row.get('稳定实验数量（含M0）', 0))

        # Combine data
        provinces = []
        for _, row in df_results.iterrows():
            code = row['code']
            prov_name = str(row['省份']).strip()
            
            cluster_m0 = clean_int(row.get('cluster', 0))
            cluster_label = str(row.get('cluster_label', ''))
            
            metrics = ProvinceMetrics(
                pop_density=clean_float(row.get('人口密度（人/平方公里）', 0.0)),
                disposable_income=clean_float(row.get('人均可支配收入_地区总计', 0.0)),
                food_grain=clean_float(row.get('口粮（千克/人）', 0.0)),
                feed_grain=clean_float(row.get('饲料粮折算值（千克/人）', 0.0))
            )
            
            labels = labels_map.get(code, {
                "M0": cluster_m0,
                "C1": cluster_m0,
                "C2": cluster_m0,
                "C3": cluster_m0,
                "C4": cluster_m0,
                "C5": cluster_m0
            })
            
            stability_val = stability_map.get(code, 6) # Default to 6 if not in stability map

            provinces.append(ProvinceClusteringData(
                name=prov_name,
                code=code,
                cluster_m0=cluster_m0,
                cluster_label=cluster_label,
                stability=stability_val,
                metrics=metrics,
                labels=labels
            ))

        return provinces
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch provinces data: {str(e)}")

@app.get("/api/ablation", response_model=AblationResponse)
def get_ablation():
    try:
        # Load quality comparison
        quality_path = TABLE_DIR / "六组实验聚类质量对比.csv"
        if not quality_path.exists():
            raise HTTPException(status_code=404, detail=f"Quality comparison file not found at {quality_path}")
        df_quality = pd.read_csv(quality_path)

        # Load labels wide table
        labels_path = TABLE_DIR / "六组实验省份聚类标签宽表.csv"
        if not labels_path.exists():
            raise HTTPException(status_code=404, detail=f"Labels wide table not found at {labels_path}")
        df_labels = pd.read_csv(labels_path)
        df_labels['code'] = df_labels['行政区划代码'].apply(format_code)

        metrics = []
        for _, row in df_quality.iterrows():
            sizes = [
                clean_int(row.get('类0省份数量', 0)),
                clean_int(row.get('类1省份数量', 0)),
                clean_int(row.get('类2省份数量', 0)),
                clean_int(row.get('类3省份数量', 0)),
                clean_int(row.get('类4省份数量', 0))
            ]
            metrics.append(AblationMetric(
                id=str(row['实验编号']),
                name=str(row['实验名称']),
                domains=str(row['保留指标域']),
                silhouette=clean_float(row.get('silhouette_score', 0.0)),
                ch_score=clean_float(row.get('calinski_harabasz_score', 0.0)),
                ari=clean_float(row.get('与M0的ARI一致性', 0.0)),
                sizes=sizes
            ))

        provinces_labels = {}
        for _, row in df_labels.iterrows():
            code = row['code']
            provinces_labels[code] = {
                "M0": clean_int(row.get('M0')),
                "C1": clean_int(row.get('C1')),
                "C2": clean_int(row.get('C2')),
                "C3": clean_int(row.get('C3')),
                "C4": clean_int(row.get('C4')),
                "C5": clean_int(row.get('C5'))
            }

        return AblationResponse(
            metrics=metrics,
            provinces_labels=provinces_labels
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch ablation data: {str(e)}")

@app.get("/api/stability", response_model=List[ProvinceStability])
def get_stability():
    try:
        # Load stability table
        stability_path = TABLE_DIR / "省份分组稳定性.csv"
        if not stability_path.exists():
            raise HTTPException(status_code=404, detail=f"Stability table not found at {stability_path}")
        df_stability = pd.read_csv(stability_path)
        df_stability['code'] = df_stability['行政区划代码'].apply(format_code)

        def is_consistent(val):
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return bool(val)
            if isinstance(val, str):
                return val.lower() == 'true'
            return bool(val)

        stability_list = []
        for _, row in df_stability.iterrows():
            code = row['code']
            prov_name = str(row['省份']).strip()
            stability_score = clean_int(row.get('稳定实验数量（含M0）', 0))

            changes = []
            if not is_consistent(row.get('C1与M0一致', True)):
                changes.append("所有特征直接等权(C1)")
            if not is_consistent(row.get('C2与M0一致', True)):
                changes.append("移除人口域(C2)")
            if not is_consistent(row.get('C3与M0一致', True)):
                changes.append("移除经济域(C3)")
            if not is_consistent(row.get('C4与M0一致', True)):
                changes.append("移除口粮域(C4)")
            if not is_consistent(row.get('C5与M0一致', True)):
                changes.append("移除饲料粮域(C5)")

            if not changes:
                detail = "分类在所有实验中均保持完全稳定"
            elif len(changes) == 1:
                detail = f"仅在{changes[0]}时分类漂移"
            else:
                detail = f"在{', '.join(changes)}时分类漂移"

            stability_list.append(ProvinceStability(
                name=prov_name,
                code=code,
                stability_score=stability_score,
                detail=detail
            ))

        return stability_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stability data: {str(e)}")

# Add a route to serve China provinces GeoJSON directly for frontend ease
@app.get("/api/geojson")
def get_geojson():
    try:
        if not GEOJSON_PATH.exists():
            raise HTTPException(status_code=404, detail="GeoJSON map data not found")
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load GeoJSON: {str(e)}")
