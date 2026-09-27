from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.deps import get_db_session
from schemas.settings import ApifyTestIn, ApifyTestOut, SettingsOut, SettingsUpdateIn
from services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "",
    response_model=SettingsOut,
    summary="Get user profile and search scoring settings",
)
def get_settings(db: Session = Depends(get_db_session)) -> SettingsOut:
    """Retrieves the active user candidate profile and search scoring preferences."""
    return SettingsService.get_settings(session=db)


@router.put(
    "",
    response_model=SettingsOut,
    summary="Update user profile and search scoring settings",
)
def update_settings(
    payload: SettingsUpdateIn,
    db: Session = Depends(get_db_session),
) -> SettingsOut:
    """Updates candidate profile identity, search scoring calibration, and API integrations."""
    return SettingsService.update_settings(session=db, payload=payload)


@router.post(
    "/test-apify",
    response_model=ApifyTestOut,
    summary="Test and validate Apify API token",
)
def test_apify_token(payload: ApifyTestIn) -> ApifyTestOut:
    """Tests an Apify API token against Apify's live authentication API."""
    return SettingsService.test_apify_token(token=payload.token)
