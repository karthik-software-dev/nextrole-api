from dataclasses import dataclass, field


@dataclass
class TargetCompany:
    name: str
    ats_type: str                  # "smartrecruiters", "greenhouse", "lever", "workday"
    identifier: str                # Public company slug or board token
    career_url: str                # Official career site URL
    enabled: bool = True
    keywords: list[str] = field(default_factory=lambda: ["python", "backend"])
    location_filter: str | None = "India"


# Curated catalog of target tech employers with verified zero-cost public ATS APIs
TARGET_COMPANIES: list[TargetCompany] = [
    TargetCompany(
        name="ServiceNow",
        ats_type="smartrecruiters",
        identifier="ServiceNow",
        career_url="https://www.servicenow.com/company/careers.html",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Freshworks",
        ats_type="smartrecruiters",
        identifier="Freshworks",
        career_url="https://www.freshworks.com/company/careers/",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Razorpay",
        ats_type="greenhouse",
        identifier="razorpaysoftwareprivatelimited",
        career_url="https://razorpay.com/jobs/",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
]


def get_enabled_target_companies() -> list[TargetCompany]:
    """Returns only actively enabled target company configurations."""
    return [c for c in TARGET_COMPANIES if c.enabled]
