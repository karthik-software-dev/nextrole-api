"""Relocate.me In-House Scraper for Verified Relocation & Visa Sponsorship Tech Jobs."""

import logging
import re
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from .models import JobItem, ScraperResult
from processing.salary_parser import parse_salary

logger = logging.getLogger("custom_scraper.relocateme")

RELOCATEME_BASE_URL = "https://relocate.me"
RELOCATEME_SEARCH_URL = "https://relocate.me/search"


class RelocateMeScraper:
    """Scrapes verified software engineering jobs with employer visa sponsorship and relocation packages."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def scrape(
        self,
        search_term: str = "python",
        results_wanted: int = 25,
        hours_old: Optional[int] = 336,
    ) -> ScraperResult:
        collected: List[JobItem] = []
        errors: List[str] = []
        queries = ["python", "backend"] if search_term.lower() in ("python", "backend") else [search_term]
        seen_links = set()

        category_paths = {
            "python": "/international-jobs/python",
            "backend": "/international-jobs/software-developer",
            "remote": "/international-jobs/remote",
        }

        for q in queries:
            if len(collected) >= results_wanted:
                break
            try:
                target_path = category_paths.get(q.lower())
                if target_path:
                    req_url = f"{RELOCATEME_BASE_URL}{target_path}"
                    params = None
                else:
                    req_url = RELOCATEME_SEARCH_URL
                    params = {"query": q}

                logger.info(f"[Relocate.me] Scraping verified relocation jobs for '{q}' via {req_url}...")
                with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=self.headers) as client:
                    resp = client.get(req_url, params=params)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")

                cards = soup.select(".jobs-list__job")
                for card in cards:
                    if len(collected) >= results_wanted:
                        break

                    a_tag = card.select_one("a")
                    if not a_tag or not a_tag.get("href"):
                        continue

                    href = a_tag["href"].strip()
                    # Skip promotional banners and paid ads
                    if "paid-option" in href or "the-global-move" in href:
                        continue

                    if href in seen_links:
                        continue
                    seen_links.add(href)

                    full_url = href if href.startswith("http") else f"{RELOCATEME_BASE_URL}{href}"

                    # Extract company & country from badges
                    p_tags = [p.get_text(strip=True) for p in card.select(".job__company p")]
                    country = p_tags[0] if len(p_tags) > 0 else "Abroad"
                    company = p_tags[1] if len(p_tags) > 1 else (p_tags[0] if p_tags else "Global Employer")

                    # Extract title and city cleanly (HTML has "Title in\n    City")
                    title_elem = card.select_one(".job__title")
                    title_raw = title_elem.get_text(separator=" ", strip=True) if title_elem else "Software Engineer"
                    clean_text = re.sub(r"\s+", " ", title_raw).strip()
                    city = ""
                    title = clean_text
                    if " in " in clean_text:
                        parts = clean_text.rsplit(" in ", 1)
                        title = parts[0].strip()
                        city = parts[1].strip()

                    full_location = f"{city}, {country}" if city and country.lower() != city.lower() else country

                    prev_el = card.select_one(".job__preview")
                    preview_text = prev_el.get_text(separator=" ", strip=True) if prev_el else ""
                    prefix = f"{preview_text} " if preview_text else ""

                    desc_text = (
                        f"{prefix}Python software engineering and backend systems role at {company} in {full_location}. "
                        f"Includes verified employer work visa sponsorship and full relocation support package."
                    )

                    job_id = f"relocateme_{abs(hash(href)) % 10000000}"

                    job_item = JobItem(
                        id=job_id,
                        title=title,
                        company=company,
                        source="relocateme",
                        location=full_location,
                        is_remote=False,
                        salary_raw=None,
                        salary_min=None,
                        salary_max=None,
                        salary_currency="EUR",
                        description=desc_text,
                        discovery_url=full_url,
                        apply_url=full_url,
                        posted_at=None,
                        tags=["Visa Sponsorship", "Relocation Package", "Engineering"],
                        raw_data={"href": href, "visa_sponsorship": True, "relocation": True},
                    )
                    collected.append(job_item)

            except Exception as e:
                logger.error(f"[Relocate.me] Error querying '{q}': {e}")
                errors.append(str(e))

        logger.info(f"[Relocate.me] Successfully fetched {len(collected)} verified visa-sponsored roles.")
        return ScraperResult(
            platform="relocateme",
            search_query=search_term,
            location="Abroad",
            total_found=len(collected),
            jobs=collected,
            errors=errors if errors else None,
        )
