from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db_session
from schemas.common import PaginatedResponse
from schemas.company import CompanyDetailOut, CompanyOut
from services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get(
    "",
    response_model=PaginatedResponse[CompanyOut],
    summary="List company directory with open jobs count",
)
def list_companies(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_target: bool | None = Query(None, description="Filter for target enterprise companies"),
    search: str | None = Query(None, description="Search company by name"),
    location: str | None = Query(None, description="Filter companies by location/region ('INDIA' or 'ABROAD')"),
    db: Session = Depends(get_db_session),
) -> PaginatedResponse[CompanyOut]:
    """Retrieves directory of employers with open active positions count."""
    return CompanyService.get_companies(
        session=db,
        page=page,
        page_size=page_size,
        is_target=is_target,
        search=search,
        location=location,
    )


@router.get(
    "/{company_id}",
    response_model=CompanyDetailOut,
    summary="Get company profile and active vacancies",
)
def get_company(
    company_id: int,
    db: Session = Depends(get_db_session),
) -> CompanyDetailOut:
    """Fetches company profile, career links, ATS provider, and active open jobs."""
    company = CompanyService.get_company_by_id(session=db, company_id=company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} was not found.",
        )
    return company
