from pydantic import BaseModel
from typing import List


class KPIStats(BaseModel):
    new_jobs: int
    validated_jobs: int
    duplicates: int
    deals_created: int
    errors: int
    active_search_profiles: int


class TimeSeriesPoint(BaseModel):
    date: str
    count: int


class TechStackItem(BaseModel):
    technology: str
    count: int


class LocationItem(BaseModel):
    location: str
    count: int


class DashboardResponse(BaseModel):
    kpis: KPIStats
    jobs_per_day: List[TimeSeriesPoint]
    deals_per_day: List[TimeSeriesPoint]
    top_technologies: List[TechStackItem]
    top_locations: List[LocationItem]
