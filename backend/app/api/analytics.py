"""Analytics API router (thin wrapper over simulator + analytics engine)."""

from fastapi import APIRouter, Query

from app.schemas.analytics import AnalyticsReport
from app.services.analytics import analyze_plant
from app.services.simulator import generate_plant_data

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/sample", response_model=AnalyticsReport)
def get_sample_analytics(
    machines: int = Query(4, ge=1, le=10),
    observations: int = Query(48, ge=4, le=500),
    seed: int = Query(7),
) -> AnalyticsReport:
    """Generate sample plant data and return its deterministic analytics report."""
    obs = generate_plant_data(
        num_machines=machines,
        observations_per_machine=observations,
        seed=seed,
    )
    return analyze_plant(obs)
