"""Company Career Pages Unified Registry Adapter.

Re-exports the canonical company registry and lookup helpers from the single source of truth in
app.config.target_companies. Preserves backwards compatibility for all scraper imports.
"""

from config.target_companies import (
    COMPANY_REGISTRY,
    TARGET_COMPANIES,
    TargetCompany,
    get_companies_by_ats,
    get_company_by_name,
    get_enabled_target_companies,
)

__all__ = [
    "COMPANY_REGISTRY",
    "TARGET_COMPANIES",
    "TargetCompany",
    "get_companies_by_ats",
    "get_company_by_name",
    "get_enabled_target_companies",
]
