"""Parser and normalizer for Indeed job postings."""

import re
from datetime import datetime, timezone
from typing import Any, Optional, Tuple
from bs4 import BeautifulSoup

from processing.experience_parser import extract_experience as canonical_extract_exp
from processing.salary_parser import parse_salary as canonical_parse_salary
from .models import JobItem


def clean_html_description(html_content: Optional[str]) -> str:
    """Converts HTML job descriptions into clean, formatted plain text with preserved structure."""
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # Replace block level elements with newlines
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all("p"):
        p.insert_after("\n\n")
    for li in soup.find_all("li"):
        li.insert_before("• ")
        li.insert_after("\n")
    for header in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        header.insert_before("\n\n")
        header.insert_after("\n")

    text = soup.get_text()
    # Normalize multiple blank lines to double newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_location(job_data: dict[str, Any], description: str = "") -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Extracts and normalizes location fields (city, state, country, formatted)."""
    loc_node = job_data.get("location") or {}
    city = loc_node.get("city")
    state = loc_node.get("admin1Code")
    country = loc_node.get("countryName") or loc_node.get("countryCode") or "India"

    formatted_node = loc_node.get("formatted") or {}
    formatted_str = formatted_node.get("short") or formatted_node.get("long")

    # 1. If city is empty, check formatted location string
    if not city and formatted_str:
        if "chennai" in formatted_str.lower():
            city = "Chennai"
        elif "bangalore" in formatted_str.lower() or "bengaluru" in formatted_str.lower():
            city = "Bangalore"
        elif "hyderabad" in formatted_str.lower():
            city = "Hyderabad"
        elif "pune" in formatted_str.lower():
            city = "Pune"
        elif "mumbai" in formatted_str.lower():
            city = "Mumbai"
        elif "noida" in formatted_str.lower() or "gurugram" in formatted_str.lower() or "delhi" in formatted_str.lower():
            city = "Delhi NCR"

    # 2. Check employer addresses fallback
    if not city:
        employer_dossier = job_data.get("employer", {}).get("dossier", {}) if job_data.get("employer") else {}
        emp_details = employer_dossier.get("employerDetails", {}) if employer_dossier else {}
        addresses = emp_details.get("addresses", []) if emp_details else []
        for addr in addresses:
            if isinstance(addr, str) and "chennai" in addr.lower():
                city = "Chennai"
                break

    # 3. Check description text fallback
    if not city and description:
        chennai_neighborhoods = [
            "chennai", "guindy", "sholinganallur", "vadapalani", "t. nagar", "t nagar",
            "velachery", "thiruvanmiyur", "perungudi", "tarmani", "omr", "porur", "ambattur"
        ]
        desc_lower = description.lower()
        if any(re.search(rf"\b{re.escape(n)}\b", desc_lower) for n in chennai_neighborhoods):
            city = "Chennai"

    # Construct clean unified location string
    loc_parts = []
    if city:
        loc_parts.append(city)
    if state and state != city:
        loc_parts.append(state)
    if country and country not in loc_parts:
        loc_parts.append(country)

    location_str = ", ".join(loc_parts) if loc_parts else formatted_str or "India"
    return location_str, city, state, country


def parse_salary(job_data: dict[str, Any], description: str = "") -> Tuple[Optional[str], Optional[float], Optional[float], str, Optional[str]]:
    """Extracts salary numbers and periods from compensation node, detailedSalary, or description."""
    comp = job_data.get("compensation") or {}
    base_salary = comp.get("baseSalary") or (comp.get("estimated") or {}).get("baseSalary")
    currency = comp.get("currencyCode") or "INR"

    if base_salary:
        unit = (base_salary.get("unitOfWork") or "").upper()
        rng = base_salary.get("range") or {}
        min_val = rng.get("min")
        max_val = rng.get("max")
        if min_val is not None or max_val is not None:
            # Format raw string
            raw = f"₹{min_val:,.0f} - ₹{max_val:,.0f} {unit}" if min_val and max_val else f"₹{(min_val or max_val):,.0f} {unit}"
            return raw, float(min_val) if min_val else None, float(max_val) if max_val else None, currency, unit

    # Check recruit.detailedSalary
    recruit_salary = (job_data.get("recruit") or {}).get("detailedSalary")
    if recruit_salary:
        raw_text = str(recruit_salary)
        # Parse LPA or rupee ranges
        parsed = _parse_salary_text(raw_text)
        if parsed[0]:
            return parsed

    # Description regex fallback for Indian Rupee
    if description:
        parsed = _parse_salary_text(description)
        if parsed[0]:
            return parsed

    return None, None, None, "INR", None


def _parse_salary_text(text: str) -> Tuple[Optional[str], Optional[float], Optional[float], str, Optional[str]]:
    """Parser for salary formats via processing.salary_parser."""
    if not text:
        return None, None, None, "INR", None
    s_min, s_max, curr = canonical_parse_salary(text)
    if s_min is not None:
        return text.strip(), s_min, s_max, curr, "YEAR"
    return None, None, None, "INR", None


def extract_experience(text: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """Extracts minimum and maximum years of experience from job text via processing.experience_parser."""
    return canonical_extract_exp(text)


def parse_job_item(raw_job: dict[str, Any], country_code: str = "IN") -> JobItem:
    """Transforms a raw Indeed GraphQL job dictionary into a canonical JobItem."""
    job_key = raw_job.get("key", "")
    title = (raw_job.get("title") or "Unknown Title").strip()

    # Description
    desc_html = (raw_job.get("description") or {}).get("html") or ""
    clean_desc = clean_html_description(desc_html)

    # Employer / Company
    employer = raw_job.get("employer") or {}
    company_name = employer.get("name")
    if not company_name:
        source_node = raw_job.get("source") or {}
        src_name = source_node.get("name")
        if src_name and src_name.lower() != "indeed":
            company_name = src_name
        else:
            company_name = "Confidential Employer"

    # Company URL cleanup (prevent trailing 'None')
    rel_company_url = employer.get("relativeCompanyPageUrl")
    company_url = None
    if rel_company_url and not rel_company_url.endswith("None"):
        domain = "in" if country_code == "IN" else "www"
        company_url = f"https://{domain}.indeed.com{rel_company_url}"

    dossier = employer.get("dossier") or {}
    emp_details = dossier.get("employerDetails") or {}
    corp_website = (dossier.get("links") or {}).get("corporateWebsite")
    logo_url = (dossier.get("images") or {}).get("squareLogoUrl")
    employees = emp_details.get("employeesLocalizedLabel")
    industry = emp_details.get("industry")

    # Dates
    date_pub_ms = raw_job.get("datePublished")
    posted_at = None
    if date_pub_ms:
        try:
            posted_at = datetime.fromtimestamp(date_pub_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            pass

    # Location
    location_str, city, state, country = parse_location(raw_job, clean_desc)

    # Remote detection
    is_remote = False
    attributes = raw_job.get("attributes") or []
    attr_labels = [a.get("label", "").lower() for a in attributes if isinstance(a, dict) and a.get("label")]
    if any("remote" in label for label in attr_labels):
        is_remote = True
    elif "remote" in title.lower() or (location_str and "remote" in location_str.lower()):
        is_remote = True

    # Job type
    job_type = "Full-time"
    if any("intern" in label for label in attr_labels) or "intern" in title.lower():
        job_type = "Internship"
    elif any("contract" in label for label in attr_labels) or "contract" in title.lower():
        job_type = "Contract"
    elif any("part-time" in label for label in attr_labels):
        job_type = "Part-time"

    # Salary
    salary_raw, sal_min, sal_max, currency, period = parse_salary(raw_job, clean_desc)

    # Experience
    exp_min, exp_max, exp_raw = extract_experience(f"{title}\n{clean_desc}")

    # URLs
    domain = "in" if country_code == "IN" else "www"
    discovery_url = f"https://{domain}.indeed.com/viewjob?jk={job_key}"
    recruit_node = raw_job.get("recruit") or {}
    apply_url = recruit_node.get("viewJobUrl") or discovery_url

    # Tags / Skills
    tags = [a.get("label") for a in attributes if isinstance(a, dict) and a.get("label")]

    return JobItem(
        id=f"in-{job_key}",
        title=title,
        company=company_name,
        source="indeed",
        location=location_str,
        city=city,
        state=state,
        country=country,
        is_remote=is_remote,
        salary_raw=salary_raw,
        salary_min=sal_min,
        salary_max=sal_max,
        salary_currency=currency,
        salary_period=period,
        description=clean_desc,
        description_html=desc_html,
        discovery_url=discovery_url,
        apply_url=apply_url,
        company_url=company_url,
        company_website=corp_website,
        company_logo=logo_url,
        posted_at=posted_at,
        job_type=job_type,
        experience_min=exp_min,
        experience_max=exp_max,
        experience_raw=exp_raw,
        company_employees=employees,
        company_industry=industry,
        tags=tags,
        raw_data=raw_job,
    )
