from pydantic import BaseModel
from typing import List, Dict

class ProvinceMetrics(BaseModel):
    pop_density: float
    disposable_income: float
    food_grain: float
    feed_grain: float

class ProvinceClusteringData(BaseModel):
    name: str
    code: str
    cluster_m0: int
    cluster_label: str
    stability: int
    metrics: ProvinceMetrics
    labels: Dict[str, int]

class AblationMetric(BaseModel):
    id: str
    name: str
    domains: str
    silhouette: float
    ch_score: float
    ari: float
    sizes: List[int]

class AblationResponse(BaseModel):
    metrics: List[AblationMetric]
    provinces_labels: Dict[str, Dict[str, int]]

class ProvinceStability(BaseModel):
    name: str
    code: str
    stability_score: int
    detail: str
