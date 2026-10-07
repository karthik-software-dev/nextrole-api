"""Indeed Scraper Orchestrator.

Handles multi-page pagination, rate-limiting jitter, field parsing,
deduplication, and JSON/CSV export.
"""

import csv
import json
import logging
import random
import time
from pathlib import Path
from typing import Optional

from .client import IndeedClient
from .models import JobItem, ScraperResult
from .parser import parse_job_item

logger = logging.getLogger("custom_scraper.indeed")


class IndeedScraper:
    """High-level autonomous Indeed scraper replacing external Apify services."""

    def __init__(
        self,
        country: str = "IN",
        timeout: float = 20.0,
        min_delay: float = 0.5,
        max_delay: float = 1.2,
    ):
        self.country = country.upper()
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay

    def scrape(
        self,
        search_term: str,
        location: str = "Chennai",
        results_wanted: int = 50,
        hours_old: Optional[int] = 336,
        radius_miles: int = 50,
        page_size: int = 50,
    ) -> ScraperResult:
        """Executes a complete job discovery run with automatic cursor pagination."""
        start_time = time.time()
        logger.info(f"Starting scrape: '{search_term}' in '{location}' (Target: {results_wanted} jobs, window: {hours_old}h)...")

        collected_jobs: list[JobItem] = []
        seen_keys: set[str] = set()
        cursor: Optional[str] = None
        page = 1
        errors: list[str] = []

        with IndeedClient(country=self.country, timeout=self.timeout) as client:
            while len(collected_jobs) < results_wanted:
                needed = results_wanted - len(collected_jobs)
                limit = min(needed, page_size)

                logger.info(f"Page {page}: Fetching up to {limit} items (collected so far: {len(collected_jobs)}/{results_wanted})...")
                raw_results, next_cursor = client.fetch_job_page(
                    search_term=search_term,
                    location=location,
                    radius_miles=radius_miles,
                    limit=limit,
                    cursor=cursor,
                    hours_old=hours_old,
                )

                if not raw_results:
                    logger.info(f"No further items returned on page {page}. Concluding search.")
                    break

                new_on_page = 0
                for item in raw_results:
                    raw_job = item.get("job")
                    if not raw_job:
                        continue

                    job_key = raw_job.get("key")
                    if not job_key or job_key in seen_keys:
                        continue

                    seen_keys.add(job_key)
                    job_item = parse_job_item(raw_job, country_code=self.country)
                    collected_jobs.append(job_item)
                    new_on_page += 1

                    if len(collected_jobs) >= results_wanted:
                        break

                logger.info(f"Page {page} added {new_on_page} unique jobs.")

                # If no new items or no next cursor, finish
                if not next_cursor or new_on_page == 0:
                    logger.info("Reached end of search results pagination.")
                    break

                cursor = next_cursor
                page += 1

                # Polite jitter between pagination requests
                jitter = random.uniform(self.min_delay, self.max_delay)
                time.sleep(jitter)

        duration = time.time() - start_time
        logger.info(f"Completed scrape: retrieved {len(collected_jobs)} jobs in {duration:.2f}s.")

        return ScraperResult(
            platform="indeed",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=round(duration, 2),
            errors=errors,
        )

    @staticmethod
    def save_to_json(result: ScraperResult, file_path: Path | str) -> None:
        """Serializes scraper results to a JSON file."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "platform": result.platform,
            "search_query": result.search_query,
            "location": result.location,
            "total_found": result.total_found,
            "duration_seconds": result.duration_seconds,
            "jobs": [j.to_dict() for j in result.jobs],
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(result.jobs)} jobs to JSON: {target.resolve()}")

    @staticmethod
    def save_to_csv(result: ScraperResult, file_path: Path | str) -> None:
        """Serializes scraper results to a CSV file for tabular inspection."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        if not result.jobs:
            logger.warning("No jobs to write to CSV.")
            return

        headers = [
            "id", "title", "company", "city", "state", "country", "location",
            "is_remote", "job_type", "salary_raw", "salary_min", "salary_max",
            "salary_currency", "salary_period", "experience_raw", "experience_min",
            "experience_max", "posted_at", "discovery_url", "apply_url",
            "company_url", "company_website", "company_employees", "tags"
        ]

        with open(target, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            for job in result.jobs:
                row = job.to_dict()
                row["tags"] = "; ".join(job.tags) if job.tags else ""
                writer.writerow(row)

        logger.info(f"Saved {len(result.jobs)} jobs to CSV: {target.resolve()}")
