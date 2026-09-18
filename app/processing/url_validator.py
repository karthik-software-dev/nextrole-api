from urllib.parse import urlparse

from models.job import Job
from processing.deduplication import canonicalize_url

# Recognized ATS platforms mapped to user-friendly provider names
KNOWN_ATS_PROVIDERS = {
    "myworkdayjobs.com": "Workday ATS",
    "greenhouse.io": "Greenhouse ATS",
    "grnh.se": "Greenhouse ATS",
    "lever.co": "Lever ATS",
    "ashbyhq.com": "Ashby ATS",
    "smartrecruiters.com": "SmartRecruiters ATS",
    "icims.com": "iCIMS ATS",
    "jobvite.com": "Jobvite ATS",
    "ats.rippling.com": "Rippling ATS",
    "join.com": "Join.com ATS",
    "bamboohr.com": "BambooHR ATS",
    "darwinbox.in": "Darwinbox ATS",
    "darwinbox.com": "Darwinbox ATS",
    "zohorecruit.in": "Zoho Recruit ATS",
    "zohorecruit.com": "Zoho Recruit ATS",
    "contacthr.com": "ContactHR ATS",
    "keka.com": "Keka ATS",
    "breezy.hr": "Breezy HR ATS",
    "freshteam.com": "Freshteam ATS",
    "ripplehire.com": "RippleHire ATS",
    "pyjamahr.com": "PyjamaHR ATS",
}

# Known aggregators that redirect back to a job board rather than direct ATS
AGGREGATOR_DOMAINS = {
    "indeed.com",
    "linkedin.com",
    "naukri.com",
    "glassdoor.com",
    "monster.com",
    "shine.com",
    "timesjobs.com",
}


def validate_and_classify_url(url: str | None) -> tuple[str, str | None, str | None]:
    """Validates, canonicalizes, and classifies an application link.

    Returns:
        tuple[str, str | None, str | None]:
            (apply_type, ats_provider, clean_url)

        apply_type:
            - "DIRECT_ATS": Hosted on a verified ATS (Workday, Greenhouse, etc.)
            - "COMPANY_CAREERS": Hosted on company's verified career portal
            - "AGGREGATOR_REDIRECT": Redirects to Indeed/LinkedIn rather than direct ATS
            - "MISSING": No usable link available
    """
    if not url:
        return "MISSING", None, None

    clean_url = canonicalize_url(url)
    if not clean_url:
        return "MISSING", None, None

    try:
        parsed = urlparse(clean_url)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()
    except Exception:
        return "MISSING", None, None

    if not netloc:
        return "MISSING", None, None

    # Reject generic homepages (e.g. 'https://company.com/' or 'https://careers.company.com/') with no job path
    path_clean = path.strip("/")
    if not path_clean and not parsed.query:
        return "MISSING", None, None

    # 1. Check Known ATS Providers
    for domain, provider in KNOWN_ATS_PROVIDERS.items():
        if domain in netloc:
            return "DIRECT_ATS", provider, clean_url

    # 2. Check Aggregator Redirects
    for domain in AGGREGATOR_DOMAINS:
        if domain in netloc:
            provider_name = "Indeed Redirect" if "indeed.com" in netloc else "Aggregator Redirect"
            return "AGGREGATOR_REDIRECT", provider_name, clean_url

    # 3. Check Company Career Portal Patterns
    career_indicators = ("careers", "career", "jobs", "job", "recruiting", "talent")
    has_career_subdomain = any(ind in netloc for ind in ("careers.", "career.", "jobs.", "job."))
    has_career_path = any(f"/{ind}" in path for ind in career_indicators)

    if has_career_subdomain or has_career_path:
        return "COMPANY_CAREERS", "Company Careers Portal", clean_url

    # 4. Fallback for valid external links
    return "COMPANY_CAREERS", "Direct Portal", clean_url


def validate_job_urls(jobs: list[Job]) -> list[Job]:
    """Validates and classifies application links for a list of Job objects."""
    for job in jobs:
        apply_type, provider, clean_url = validate_and_classify_url(job.apply_url)
        job.apply_type = apply_type
        job.ats_provider = provider
        job.apply_url = clean_url

    return jobs
