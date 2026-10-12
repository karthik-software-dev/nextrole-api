from fastapi import APIRouter, BackgroundTasks, status

from schemas.discovery import (
    DiscoveryLogOut,
    DiscoveryRunIn,
    DiscoverySourceOut,
    DiscoveryStatusOut,
)
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


@router.get(
    "/sources",
    response_model=list[DiscoverySourceOut],
    summary="Get all 30 tracked source engines and live metrics",
)
def get_discovery_sources() -> list[DiscoverySourceOut]:
    """Returns the complete catalog of 30 sources with real-time database yield metrics."""
    return DiscoveryService.get_sources()


@router.get(
    "/logs",
    response_model=list[DiscoveryLogOut],
    summary="Get live crawler terminal execution logs",
)
def get_discovery_logs(since_id: int = 0) -> list[DiscoveryLogOut]:
    """Returns sequential real-time execution logs from the in-memory scraper ring buffer."""
    return DiscoveryService.get_logs(since_id=since_id)


@router.delete(
    "/logs",
    summary="Clear in-memory terminal logs",
)
def clear_discovery_logs() -> dict[str, str]:
    """Resets the live terminal log buffer."""
    DiscoveryService.clear_logs()
    return {"message": "Discovery terminal logs cleared."}




@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger asynchronous job discovery pipeline",
)
def trigger_discovery_run(
    payload: DiscoveryRunIn,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    started = DiscoveryService.start_pipeline_async(
        background_tasks=background_tasks,
        source=payload.source,
        location=payload.location,
        use_cache=payload.use_cache,
    )
    if not started:
        return {
            "message": "Discovery run is already in progress.",
            "status": "running",
        }

    return {
        "message": f"Discovery pipeline initiated in background (source={payload.source}, location={payload.location}).",
        "status": "initiated",
    }
