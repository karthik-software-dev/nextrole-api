"""Target Companies Registry and Configuration.

Single consolidated source of truth for target employers across all ATS providers
(Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Recruitee, Workable, Teamtailor,
BambooHR, Personio, Breezy HR).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TargetCompany:
    name: str
    ats_type: str                  # "smartrecruiters", "greenhouse", "lever", "workday", etc.
    identifier: str                # Public company slug or board token
    career_url: str                # Official career site URL
    enabled: bool = True
    category: str = "india"        # "india" or "abroad"
    keywords: list[str] = field(default_factory=lambda: ["python", "backend"])
    location_filter: str | None = "India"
    target_locations: list[str] = field(default_factory=lambda: ["Bangalore", "Bengaluru", "Chennai", "Remote"])
    workday_datacenter: Optional[str] = None
    workday_site: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "company": self.name,
            "career_url": self.career_url,
            "ats": self.ats_type,
            "ats_identifier": self.identifier,
            "category": self.category,
            "target_locations": self.target_locations,
            "enabled": self.enabled,
        }
        if self.workday_datacenter:
            d["workday_datacenter"] = self.workday_datacenter
        if self.workday_site:
            d["workday_site"] = self.workday_site
        return d


import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

JSON_REGISTRY_PATH = Path(__file__).resolve().parent / "target_companies.json"


def load_target_companies(json_path: Path | str | None = None) -> List[TargetCompany]:
    """Loads target companies from the external JSON registry (supports categorized dict or flat list)."""
    path = Path(json_path) if json_path else JSON_REGISTRY_PATH
    if not path.exists():
        logger.warning(f"Target company registry file not found: {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        companies: List[TargetCompany] = []
        if isinstance(data, dict):
            for cat, comp_list in data.items():
                for item in comp_list:
                    item_copy = dict(item)
                    item_copy.setdefault("category", cat)
                    if cat == "abroad":
                        item_copy.setdefault("location_filter", None)
                    companies.append(TargetCompany(**item_copy))
        elif isinstance(data, list):
            for item in data:
                companies.append(TargetCompany(**item))
        return companies
    except Exception as e:
        logger.error(f"Error loading target company registry from {path}: {e}")
        return []


def save_target_companies(companies: List[TargetCompany], json_path: Path | str | None = None) -> None:
    """Serializes a list of TargetCompany instances back to the JSON registry file categorized by region."""
    path = Path(json_path) if json_path else JSON_REGISTRY_PATH
    categorized: Dict[str, list] = {"india": [], "abroad": []}
    for c in companies:
        d = {
            "name": c.name,
            "ats_type": c.ats_type,
            "identifier": c.identifier,
            "career_url": c.career_url,
            "enabled": c.enabled,
            "category": c.category,
        }
        if c.location_filter != "India":
            d["location_filter"] = c.location_filter
        if c.keywords != ["python", "backend"]:
            d["keywords"] = c.keywords
        if c.target_locations != ["Bangalore", "Bengaluru", "Chennai", "Remote"]:
            d["target_locations"] = c.target_locations
        if c.workday_datacenter:
            d["workday_datacenter"] = c.workday_datacenter
        if c.workday_site:
            d["workday_site"] = c.workday_site

        cat = getattr(c, "category", "india") or "india"
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(d)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(categorized, f, indent=2, ensure_ascii=False)


def reload_target_companies() -> None:
    """Reloads the in-memory global catalog and dictionary registry from JSON."""
    global TARGET_COMPANIES, COMPANY_REGISTRY
    TARGET_COMPANIES = load_target_companies()
    COMPANY_REGISTRY = [c.to_dict() for c in TARGET_COMPANIES]


def get_companies_by_category(category: str) -> List[TargetCompany]:
    """Retrieve enabled target companies filtered by category ('india' or 'abroad')."""
    target_cat = category.strip().lower()
    return [c for c in TARGET_COMPANIES if c.category.lower() == target_cat and c.enabled]


def add_target_company(company_dict: Dict[str, Any], json_path: Path | str | None = None) -> TargetCompany:
    """Appends a new target company to the JSON registry and reloads the in-memory catalog."""
    new_company = TargetCompany(**company_dict)
    current_companies = load_target_companies(json_path)
    current_companies.append(new_company)
    save_target_companies(current_companies, json_path)
    reload_target_companies()
    return new_company


# Curated catalog of target employers loaded dynamically from JSON registry
TARGET_COMPANIES: List[TargetCompany] = load_target_companies()

# Canonical dictionary-format registry derived from single source of truth
COMPANY_REGISTRY: List[Dict[str, Any]] = [c.to_dict() for c in TARGET_COMPANIES]


def get_enabled_target_companies() -> List[TargetCompany]:
    """Returns only actively enabled target company configurations."""
    return [c for c in TARGET_COMPANIES if c.enabled]


def get_companies_by_ats(ats: str) -> List[Dict[str, Any]]:
    """Retrieve enabled company registry entries for a specific ATS provider."""
    return [c for c in COMPANY_REGISTRY if c.get("ats") == ats and c.get("enabled", True)]


def get_company_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Retrieve a company registry entry by company name."""
    target = name.strip().lower()
    for c in COMPANY_REGISTRY:
        if c.get("company", "").strip().lower() == target:
            return c
    return None
