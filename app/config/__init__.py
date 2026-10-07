import os
from pathlib import Path
from dotenv import load_dotenv

from config.target_companies import TARGET_COMPANIES, TargetCompany, get_enabled_target_companies

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:0299@localhost:5432/job_agent")
JWT_SECRET = os.getenv("JWT_SECRET", "nextrole-jwt-production-secret-key-change-in-env-2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "rahulkarthik056@gmail.com")
ADMIN_INITIAL_PASSWORD = os.getenv("ADMIN_INITIAL_PASSWORD", "#Karthick979")


__all__ = [
    "APIFY_API_TOKEN",
    "DATABASE_URL",
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "ADMIN_EMAIL",
    "ADMIN_INITIAL_PASSWORD",
    "TargetCompany",
    "TARGET_COMPANIES",
    "get_enabled_target_companies",
]


