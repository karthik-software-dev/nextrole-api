import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from models.job import Job

# Query parameter prefixes or exact keys to strip for canonicalizing ATS links
TRACKING_PARAM_PREFIXES = (
    "utm_",
    "iis",
    "indeed-",
    "gh_src",
)

TRACKING_PARAMS_EXACT = {
    "jobsite",
    "source",
    "ref",
    "from",
    "sp_source",
    "campaign",
    "locale",
}


def canonicalize_url(url: str | None) -> str | None:
    """Strips marketing/tracking query parameters and normalizes the URL.

    Example:
        'https://ats.rippling.com/jobs/123?jobSite=Indeed&utm_source=indeed'
        -> 'https://ats.rippling.com/jobs/123'
    """
    if not url:
        return None

    try:
        parsed = urlparse(url.strip())
        if not parsed.scheme or not parsed.netloc:
            return url.strip().rstrip("/")

        query_params = parse_qsl(parsed.query, keep_blank_values=False)
        filtered_params = []
        for k, v in query_params:
            k_lower = k.lower()
            if any(k_lower.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES):
                continue
            if k_lower in TRACKING_PARAMS_EXACT:
                continue
            filtered_params.append((k, v))

        filtered_params.sort()
        new_query = urlencode(filtered_params)

        clean_netloc = parsed.netloc.lower()
        clean_path = parsed.path.rstrip("/")

        return urlunparse((parsed.scheme.lower(), clean_netloc, clean_path, "", new_query, ""))
    except Exception:
        return url.strip().rstrip("/")


def normalize_company(company: str | None) -> str:
    """Normalizes company name by stripping legal entities, punctuation, and extra whitespace."""
    if not company:
        return ""

    name = company.lower()
    legal_terms = [
        r"\bpvt\.?\s*ltd\.?\b",
        r"\bprivate\s+limited\b",
        r"\binc\.?\b",
        r"\bcorp\.?\b",
        r"\bcorporation\b",
        r"\bllc\b",
        r"\bltd\.?\b",
        r"\binternal\b",
        r"\btechnologies\b",
        r"\btelematics\b",
    ]
    for term in legal_terms:
        name = re.sub(term, "", name, flags=re.IGNORECASE)

    name = re.sub(r"[^\w\s]", "", name)
    return re.sub(r"\s+", " ", name).strip()


def normalize_title(title: str | None) -> str:
    """Normalizes job title by stripping bracketed qualifiers and department tags."""
    if not title:
        return ""

    t = title.lower()
    # Remove bracketed text like (Retail), (Bangalore), (5+ Years)
    t = re.sub(r"\([^)]*\)", "", t)
    # Remove after hyphens if it's location/department
    t = re.sub(
        r"\s*-\s*(bangalore|bengaluru|india|karnataka|retail|studio team)\b.*",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def deduplicate_jobs(jobs: list[Job]) -> list[Job]:
    """Deduplicates a list of Job objects using canonical apply URLs and normalized (company, title) keys.

    Intelligently merges duplicate postings, preserving the best direct ATS apply link,
    the highest score, and a union of matched skills.
    """
    seen_by_url: dict[str, Job] = {}
    seen_by_semantic: dict[tuple[str, str], Job] = {}
    unique_jobs: list[Job] = []

    for job in jobs:
        canon_apply_url = canonicalize_url(job.apply_url)
        norm_co = normalize_company(job.company)
        norm_title = normalize_title(job.title)
        semantic_key = (norm_co, norm_title) if (norm_co and norm_title) else None

        existing: Job | None = None

        # 1. Match by canonical apply URL if available
        if canon_apply_url and canon_apply_url in seen_by_url:
            existing = seen_by_url[canon_apply_url]
        # 2. Match by normalized (company, title)
        elif semantic_key and semantic_key in seen_by_semantic:
            existing = seen_by_semantic[semantic_key]

        if existing:
            # Duplicate found: merge attributes
            existing.duplicate_count += 1

            # Prioritize official ATS application URLs over aggregator links
            if job.source == "ats" and job.apply_url:
                existing.apply_url = job.apply_url
                if "ats" not in existing.source:
                    existing.source = f"{existing.source}+ats"
            elif not existing.apply_url and job.apply_url:
                existing.apply_url = job.apply_url
            elif job.source not in existing.source:
                existing.source = f"{existing.source}+{job.source}"

            # Keep the higher relevance score
            if job.relevance_score > existing.relevance_score:
                existing.relevance_score = job.relevance_score

            # Merge matched skills
            for s in job.matched_skills:
                if s not in existing.matched_skills:
                    existing.matched_skills.append(s)

            # Preserve discovery URL if missing
            if not existing.discovery_url and job.discovery_url:
                existing.discovery_url = job.discovery_url
        else:
            # New unique job
            job.duplicate_count = 1
            if canon_apply_url:
                seen_by_url[canon_apply_url] = job
            if semantic_key:
                seen_by_semantic[semantic_key] = job
            unique_jobs.append(job)

    return unique_jobs
