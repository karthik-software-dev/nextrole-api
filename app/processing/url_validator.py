import logging
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

from models.job import Job
from processing.deduplication import canonicalize_url

logger = logging.getLogger("processing.url_validator")

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
    "workable.com": "Workable ATS",
    "teamtailor.com": "Teamtailor ATS",
    "personio.de": "Personio ATS",
    "personio.com": "Personio ATS",
    "recruitee.com": "Recruitee ATS",
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

# Phrases indicating that a job posting has been filled, closed, or deactivated
CLOSED_PHRASES = (
    "not accepting applications",
    "no longer accepting applications",
    "no longer accepting submissions",
    "this position has been filled",
    "this role has been filled",
    "this job is closed",
    "job has been closed",
    "job has expired",
    "posting has expired",
    "position is no longer available",
    "job is no longer available",
    "job not found",
    "we are currently not accepting",
    "the posting you are looking for has expired",
)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def check_url_liveness(url: str | None, timeout: float = 4.0) -> tuple[bool, str]:
    """Checks whether an application link is active or indicates an expired/closed job.

    Returns:
        tuple[bool, str]: (is_active, status_reason)
            is_active is False only for confirmed 404/410 or explicit "closed" banners.
            Temporary errors / bot challenges return True to avoid false negatives.
    """
    if not url:
        return False, "EMPTY_URL"

    try:
        req = urllib.request.Request(url, headers=_HTTP_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            status_code = getattr(resp, "status", 200)
            if status_code in (404, 410):
                return False, f"HTTP_{status_code}"

            # Inspect first 32KB of HTML for closed job notices
            html_snippet = resp.read(32768).decode("utf-8", errors="ignore").lower()
            for phrase in CLOSED_PHRASES:
                if phrase in html_snippet:
                    return False, f"CLOSED_BANNER: {phrase}"

            return True, "ACTIVE"
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return False, f"HTTP_{e.code}"
        # 403 Forbidden / 429 Rate limit / 500 are often anti-bot gates; keep as unverifiable
        return True, f"UNVERIFIABLE: HTTP_{e.code}"
    except Exception as e:
        # Timeout or DNS error -> treat as unverifiable rather than dropping valid jobs
        return True, f"UNVERIFIABLE: {type(e).__name__}"


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


def validate_job_urls(
    jobs: list[Job],
    check_liveness: bool = False,
    max_workers: int = 10,
) -> list[Job]:
    """Validates and classifies application links for a list of Job objects.

    If check_liveness=True, concurrently pings candidate URLs to discard
    postings that are 404, 410, or display 'closed / not accepting' banners.
    """
    for job in jobs:
        target_url = job.apply_url or job.discovery_url
        apply_type, provider, clean_url = validate_and_classify_url(target_url)
        job.apply_type = apply_type
        if provider and provider != "Company Careers Portal":
            job.ats_provider = provider
        elif not job.ats_provider:
            job.ats_provider = provider
        job.apply_url = clean_url

    if not check_liveness:
        return jobs

    jobs_to_check = [j for j in jobs if j.apply_url and j.apply_type != "MISSING"]
    if not jobs_to_check:
        return jobs

    logger.info(f"[UrlValidator] Verifying liveness for {len(jobs_to_check)} candidate URLs...")
    active_jobs: list[Job] = []
    dropped_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_job = {
            executor.submit(check_url_liveness, j.apply_url): j
            for j in jobs_to_check
        }
        for future in as_completed(future_to_job):
            j = future_to_job[future]
            try:
                is_active, reason = future.result()
            except Exception:
                is_active, reason = True, "CHECK_ERROR"

            if is_active:
                active_jobs.append(j)
            else:
                dropped_count += 1
                logger.info(f"[UrlValidator] Dropped closed job '{j.title}' @ '{j.company}': {reason}")

    active_ids = {id(j) for j in active_jobs}
    final_jobs = [j for j in jobs if id(j) in active_ids or (not j.apply_url or j.apply_type == "MISSING")]
    logger.info(f"[UrlValidator] Liveness verification finished: {len(final_jobs)} active, {dropped_count} closed/expired.")
    return final_jobs
