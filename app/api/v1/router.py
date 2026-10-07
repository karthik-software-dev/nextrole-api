from fastapi import APIRouter

from api.v1.analytics import router as analytics_router
from api.v1.applications import router as applications_router
from api.v1.auth import router as auth_router
from api.v1.companies import router as companies_router
from api.v1.dashboard import router as dashboard_router
from api.v1.discovery import router as discovery_router
from api.v1.jobs import router as jobs_router
from api.v1.notifications import router as notifications_router
from api.v1.settings import router as settings_router

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(companies_router)
api_v1_router.include_router(applications_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(discovery_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(notifications_router)



