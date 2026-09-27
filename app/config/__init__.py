import os
from dotenv import load_dotenv

from config.target_companies import TARGET_COMPANIES, TargetCompany, get_enabled_target_companies

load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:0299@localhost:5432/job_agent")


from typing import Any


def get_apify_token() -> str:
    """Returns active Apify token dynamically from environment or database settings."""
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if token and token != "your_apify_api_token_here":
        return token
    try:
        from storage.database import get_db
        from services.settings_service import SettingsService

        with get_db() as session:
            return SettingsService.get_active_apify_token(session)
    except Exception:
        return ""


def extract_apify_dataset_id(run: Any) -> str | None:
    """Extracts default dataset ID from Apify Actor run (supporting both apify-client v2 dict and v3 Pydantic model)."""
    if run is None:
        return None
    if isinstance(run, dict):
        return run.get("default_dataset_id") or run.get("defaultDatasetId")
    return getattr(run, "default_dataset_id", None) or getattr(run, "defaultDatasetId", None)


__all__ = [
    "APIFY_API_TOKEN",
    "get_apify_token",
    "extract_apify_dataset_id",
    "DATABASE_URL",
    "TargetCompany",
    "TARGET_COMPANIES",
    "get_enabled_target_companies",
]

