from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db_session
from schemas.dashboard import DashboardSummaryOut
from services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryOut,
    summary="Get aggregated discovery and application pipeline metrics",
)
def get_dashboard_summary(
    db: Session = Depends(get_db_session),
) -> DashboardSummaryOut:
    """Calculates active job counts, tier breakdowns, location distributions, and application funnel stats."""
    return DashboardService.get_summary(session=db)
