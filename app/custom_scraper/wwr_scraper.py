"""We Work Remotely (WWR) Structured Feed Scraper for Global Remote Engineering Roles."""

import logging
from typing import List, Optional
import xml.etree.ElementTree as ET
import httpx

from .models import JobItem, ScraperResult
from processing.salary_parser import parse_salary

logger = logging.getLogger("custom_scraper.wwr")

WWR_FEEDS = [
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
]


class WeWorkRemotelyScraper:
    """Fetches high-quality worldwide remote software jobs from We Work Remotely's official feeds."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def scrape(
        self,
        search_term: str = "python",
        results_wanted: int = 25,
        hours_old: Optional[int] = 336,
    ) -> ScraperResult:
        collected: List[JobItem] = []
        errors: List[str] = []
        seen_ids = set()

        for feed_url in WWR_FEEDS:
            if len(collected) >= results_wanted:
                break
            try:
                logger.info(f"[WWR] Querying structured feed: {feed_url}...")
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(feed_url)
                    resp.raise_for_status()
                    root = ET.fromstring(resp.text)

                items = root.findall(".//item")
                for item in items:
                    if len(collected) >= results_wanted:
                        break

                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    guid_elem = item.find("guid")
                    desc_elem = item.find("description")
                    pubdate_elem = item.find("pubDate")
                    region_elem = item.find("region")

                    full_title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                    if not full_title:
                        continue

                    # Extract company and job title (format: "Company: Title")
                    if ":" in full_title:
                        company, job_title = full_title.split(":", 1)
                        company = company.strip()
                        job_title = job_title.strip()
                    else:
                        company = "Tech Company"
                        job_title = full_title

                    job_url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                    job_guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else job_url
                    if job_guid in seen_ids:
                        continue
                    seen_ids.add(job_guid)

                    region_text = region_elem.text.strip() if region_elem is not None and region_elem.text else "Anywhere in the World"
                    desc_text = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""

                    # Filter: Candidate must match search term (in title or description)
                    term_lower = search_term.lower()
                    if term_lower not in job_title.lower() and term_lower not in desc_text.lower():
                        continue

                    # Exclude US-only / North-America only roles if restricted
                    reg_lower = region_text.lower()
                    is_locked = any(l in reg_lower for l in ["usa only", "us only", "uk only", "canada only", "north america only"]) and "anywhere" not in reg_lower
                    if is_locked:
                        continue

                    sal_min, sal_max, sal_curr = parse_salary(desc_text)

                    job_item = JobItem(
                        id=f"wwr_{abs(hash(job_guid)) % 10000000}",
                        title=job_title,
                        company=company,
                        source="wwr",
                        location=f"Worldwide Remote ({region_text})",
                        is_remote=True,
                        salary_raw=None,
                        salary_min=sal_min,
                        salary_max=sal_max,
                        salary_currency=sal_curr,
                        description=desc_text,
                        discovery_url=job_url,
                        apply_url=job_url,
                        posted_at=pubdate_elem.text.strip() if pubdate_elem is not None and pubdate_elem.text else None,
                        raw_data={"guid": job_guid, "region": region_text, "feed": feed_url},
                    )
                    collected.append(job_item)

            except Exception as e:
                logger.error(f"[WWR] Scrape error on {feed_url}: {e}")
                errors.append(str(e))

        logger.info(f"[WWR] Successfully fetched {len(collected)} worldwide remote jobs.")
        return ScraperResult(
            platform="wwr",
            search_query=search_term,
            location="Worldwide Remote",
            total_found=len(collected),
            jobs=collected,
            errors=errors if errors else None,
        )
