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
        name="Bosch Group",
        ats_type="smartrecruiters",
        identifier="BoschGroup",
        career_url="https://careers.smartrecruiters.com/BoschGroup",
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
    TargetCompany(
        name="InMobi",
        ats_type="greenhouse",
        identifier="inmobi",
        career_url="https://www.inmobi.com/company/careers",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Slice",
        ats_type="greenhouse",
        identifier="slice",
        career_url="https://www.sliceit.com/careers",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Groww",
        ats_type="greenhouse",
        identifier="groww",
        career_url="https://groww.in/careers",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Databricks",
        ats_type="greenhouse",
        identifier="databricks",
        career_url="https://www.databricks.com/company/careers",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Rubrik",
        ats_type="greenhouse",
        identifier="rubrik",
        career_url="https://www.rubrik.com/company/careers",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Apollo.io",
        ats_type="greenhouse",
        identifier="apolloio",
        career_url="https://www.apollo.io/careers",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Abnormal Security",
        ats_type="greenhouse",
        identifier="abnormalsecurity",
        career_url="https://abnormalsecurity.com/careers",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="6sense",
        ats_type="greenhouse",
        identifier="6sense",
        career_url="https://6sense.com/careers/",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Ethos Life",
        ats_type="greenhouse",
        identifier="ethoslife",
        career_url="https://www.ethoslife.com/careers/",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Elastic",
        ats_type="greenhouse",
        identifier="elastic",
        career_url="https://www.elastic.co/careers",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Deliveroo",
        ats_type="greenhouse",
        identifier="deliveroo",
        career_url="https://careers.deliveroo.co.uk/",
        enabled=True,
        keywords=["python", "backend"],
        location_filter="India",
    ),
    TargetCompany(
        name="Spotify",
        ats_type="lever",
        identifier="spotify",
        career_url="https://www.lifeatspotify.com/jobs",
        enabled=True,
        keywords=["python", "backend"],
        location_filter=None,
    ),
    TargetCompany(
        name="Palantir",
        ats_type="lever",
        identifier="palantir",
        career_url="https://www.palantir.com/careers/",
        enabled=True,
        keywords=["python", "backend"],
        location_filter=None,
    ),
]


def get_enabled_target_companies() -> list[TargetCompany]:
    """Returns only actively enabled target company configurations."""
    return [c for c in TARGET_COMPANIES if c.enabled]
