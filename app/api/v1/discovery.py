from fastapi import APIRouter, BackgroundTasks, status

from schemas.discovery import DiscoveryRunIn, DiscoveryStatusOut
from services.discovery_service import DiscoveryService

router = APIRouter(prefix="/discovery", tags=["Discovery"])


@router.get(
    "/status",
    response_model=DiscoveryStatusOut,
    summary="Get background discovery runner status",
)
def get_discovery_status() -> DiscoveryStatusOut:
    """Returns whether scrapers are running, last run timestamp, jobs found, and errors."""
    return DiscoveryService.get_status()


@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger asynchronous job discovery pipeline",
)
def trigger_discovery_run(
    payload: DiscoveryRunIn,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Launches the multi-source scraper pipeline asynchronously in the background."""
    current_status = DiscoveryService.get_status()
    if current_status.is_running:
        return {
            "message": "Discovery run is already in progress.",
            "status": "running",
        }

    background_tasks.add_task(
        DiscoveryService.run_pipeline,
        source=payload.source,
        location=payload.location,
        use_cache=payload.use_cache,
    )

    return {
        "message": f"Discovery pipeline initiated in background (source={payload.source}, location={payload.location}).",
        "status": "initiated",
    }
