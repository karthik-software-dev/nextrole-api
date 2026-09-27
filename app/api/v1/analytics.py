from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db_session
from schemas.analytics import AnalyticsSummaryOut
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryOut)
def get_analytics_summary(
    range: str = Query("30d", description="Date range: today, yesterday, 7d, 30d, month, custom"),
    start_date: str | None = Query(None, description="Start date ISO string (YYYY-MM-DD) for custom range"),
    end_date: str | None = Query(None, description="End date ISO string (YYYY-MM-DD) for custom range"),
    db: Session = Depends(get_db_session),
) -> AnalyticsSummaryOut:
    """Returns aggregated deep analytics for Analytics Tab 2."""
    return AnalyticsService.get_analytics_summary(
        session=db,
        range_val=range,
        start_date=start_date,
        end_date=end_date,
    )
