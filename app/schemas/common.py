from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadata detailing pagination status."""

    total: int = Field(..., description="Total matching items across all pages")
    page: int = Field(..., description="Current 1-indexed page")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total pages available")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic wrapper for paginated collections."""

    items: list[T]
    meta: PaginationMeta


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = "ok"
    database: str = "connected"
    version: str = "1.0.0"
    memory_rss_mb: float | None = None
