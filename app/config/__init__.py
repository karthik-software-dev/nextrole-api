import os
from dotenv import load_dotenv

from config.target_companies import TARGET_COMPANIES, TargetCompany, get_enabled_target_companies

load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:0299@localhost:5432/job_agent")

__all__ = [
    "APIFY_API_TOKEN",
    "DATABASE_URL",
    "TargetCompany",
    "TARGET_COMPANIES",
    "get_enabled_target_companies",
]

