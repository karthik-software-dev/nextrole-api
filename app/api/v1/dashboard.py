from fastapi import APIRouter, Depends, Query
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
    range: str = Query("7d", description="Date range: today, yesterday, 7d, 30d, month, custom"),
    start_date: str | None = Query(None, description="ISO format start date YYYY-MM-DD for custom range"),
    end_date: str | None = Query(None, description="ISO format end date YYYY-MM-DD for custom range"),
    db: Session = Depends(get_db_session),
) -> DashboardSummaryOut:
    """Calculates active job counts, tier breakdowns, location distributions, and application funnel stats."""
    return DashboardService.get_summary(
        session=db,
        date_range=range,
        start_date=start_date,
        end_date=end_date,
    )
