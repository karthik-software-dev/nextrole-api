"""Standardized query dispatchers for job search portals and engines.

Executes in-house scrapers with pre-configured search queries (roles and locations),
returning normalized canonical Job models.
"""

import logging
from typing import Any, List

from custom_scraper.adapter import to_job_agent_model
from custom_scraper.apna_scraper import ApnaScraper
from custom_scraper.arbeitnow_scraper import ArbeitnowScraper
from custom_scraper.cutshort_scraper import CutshortScraper
from custom_scraper.freshersworld_scraper import FreshersworldScraper
from custom_scraper.hirist_scraper import HiristScraper
from custom_scraper.indeed_scraper import IndeedScraper
from custom_scraper.internshala_scraper import InternshalaScraper
from custom_scraper.jobicy_scraper import JobicyScraper
from custom_scraper.linkedin_scraper import LinkedInScraper
from custom_scraper.naukri_scraper import NaukriScraper
from custom_scraper.relocateme_scraper import RelocateMeScraper
from custom_scraper.remotive_scraper import RemotiveScraper
from custom_scraper.shine_scraper import ShineScraper
from custom_scraper.timesjobs_scraper import TimesJobsScraper
from custom_scraper.wellfound_scraper import WellfoundScraper
from custom_scraper.wwr_scraper import WeWorkRemotelyScraper
from custom_scraper.yc_scraper import YCWorkAtAStartupScraper
from models.job import Job
from processing.deduplication import clean_job_title

logger = logging.getLogger("custom_scraper.fetchers")

FRESHNESS_HOURS_WINDOW = 336  # 14 days (14 * 24 hours)


def fetch_naukri_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from Naukri via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Executing in-house Naukri scraper...")
    scraper = NaukriScraper(headless=True)
    search_configs = [
        {"query": "Python Backend Engineer", "location": "Bangalore", "limit": 25},
        {"query": "Python Backend Developer", "location": "Chennai", "limit": 25},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            logger.info(f"[Naukri] Scraping '{cfg['query']}' in '{cfg['location']}'...")
            res = scraper.scrape(
                search_term=cfg["query"],
                location=cfg["location"],
                results_wanted=cfg["limit"],
                hours_old=FRESHNESS_HOURS_WINDOW,
            )
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[Naukri] Bot challenge encountered on '{cfg['query']}'. Halting Naukri gracefully.")
                break
            for job in res.jobs:
                job.source = "naukri"
                jobs.append(job)
            logger.info(f"[Naukri] Fetched {len(res.jobs)} items for {cfg['location']}.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from Naukri via in-house scraper: {e}")
    return jobs


def fetch_indeed_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from Indeed via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Connecting to Indeed GraphQL API via custom scraper...")
    scraper = IndeedScraper(country="IN")
    search_configs = [
        {"position": "Python Backend Engineer", "location": "Bengaluru", "maxItems": 25},
        {"position": "Python Backend Developer", "location": "Chennai", "maxItems": 25},
        {"position": "FastAPI Developer", "location": "Bengaluru", "maxItems": 20},
        {"position": "Python AI Engineer", "location": "Bengaluru", "maxItems": 20},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            res = scraper.scrape(
                search_term=cfg["position"],
                location=cfg["location"],
                results_wanted=cfg["maxItems"],
                hours_old=FRESHNESS_HOURS_WINDOW,
            )
            for item in res.jobs:
                c_job = to_job_agent_model(item)
                c_job.source = "indeed"
                c_job.title = clean_job_title(c_job.title)
                jobs.append(c_job)
            logger.info(f"[Indeed] Fetched {len(res.jobs)} items for {cfg['location']}.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from Indeed via in-house scraper: {e}")
    return jobs


def fetch_linkedin_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from LinkedIn via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Executing in-house LinkedIn scraper...")
    scraper = LinkedInScraper(fetch_descriptions=True, max_details_per_query=3, request_delay=1.0)
    search_configs = [
        {"keyword": "Python Backend Engineer", "location": "Bengaluru", "maxItems": 20},
        {"keyword": "Python Developer", "location": "Chennai", "maxItems": 15},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            logger.info(f"[LinkedIn] Scraping '{cfg['keyword']}' in {cfg['location']} (max {cfg['maxItems']})...")
            res = scraper.scrape(
                search_term=cfg["keyword"],
                location=cfg["location"],
                results_wanted=cfg["maxItems"],
                hours_old=FRESHNESS_HOURS_WINDOW,
            )
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[LinkedIn] Challenge/rate limit encountered on '{cfg['keyword']}'. Halting LinkedIn gracefully.")
                break
            for job in res.jobs:
                job.source = "linkedin"
                jobs.append(job)
            logger.info(f"[LinkedIn] Fetched {len(res.jobs)} items for {cfg['location']}.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from LinkedIn via in-house scraper: {e}")
    return jobs


def fetch_wellfound_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from Wellfound via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Executing in-house Wellfound scraper...")
    scraper = WellfoundScraper()
    search_configs = [
        {"term": "Python", "location": "bangalore", "limit": 20},
        {"term": "Backend", "location": "bangalore", "limit": 20},
        {"term": "AI", "location": "bangalore", "limit": 15},
        {"term": "Python", "location": "chennai", "limit": 15},
        {"term": "Backend", "location": "chennai", "limit": 15},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            logger.info(f"[Wellfound] Scraping startup jobs for '{cfg['term']}' in '{cfg['location']}'...")
            res = scraper.scrape(
                search_term=cfg["term"],
                location=cfg["location"],
                results_wanted=cfg["limit"],
                hours_old=FRESHNESS_HOURS_WINDOW,
            )
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[Wellfound] Bot challenge encountered on '{cfg['term']}'. Halting Wellfound gracefully.")
                break
            for job in res.jobs:
                job.source = "wellfound"
                jobs.append(job)
            logger.info(f"[Wellfound] Fetched {len(res.jobs)} items for {cfg['term']} in {cfg['location']}.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from Wellfound for '{cfg['term']}': {e}")
    return jobs


def fetch_apna_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from Apna via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Executing in-house Apna scraper...")
    scraper = ApnaScraper()
    search_configs = [
        {"term": "Python", "location": "Bangalore", "limit": 20},
        {"term": "Backend", "location": "Chennai", "limit": 15},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            logger.info(f"[Apna] Scraping '{cfg['term']}' in '{cfg['location']}'...")
            res = scraper.scrape(search_term=cfg["term"], location=cfg["location"], results_wanted=cfg["limit"], hours_old=FRESHNESS_HOURS_WINDOW)
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[Apna] Bot challenge encountered on '{cfg['term']}'. Halting Apna gracefully.")
                break
            for job in res.jobs:
                job.source = "apna"
                jobs.append(job)
            logger.info(f"[Apna] Fetched {len(res.jobs)} items.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from Apna via in-house scraper: {e}")
    return jobs


def fetch_cutshort_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from Cutshort via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Executing in-house Cutshort scraper...")
    scraper = CutshortScraper()
    search_configs = [
        {"term": "Python", "location": "Bangalore", "limit": 20},
        {"term": "Backend", "location": "Bangalore", "limit": 20},
        {"term": "AI", "location": "Bangalore", "limit": 15},
        {"term": "FastAPI", "location": "Bangalore", "limit": 15},
        {"term": "Backend", "location": "Chennai", "limit": 15},
        {"term": "Python", "location": "Chennai", "limit": 15},
        {"term": "Python", "location": "Remote", "limit": 15},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            logger.info(f"[Cutshort] Scraping '{cfg['term']}' in '{cfg['location']}'...")
            res = scraper.scrape(search_term=cfg["term"], location=cfg["location"], results_wanted=cfg["limit"], hours_old=FRESHNESS_HOURS_WINDOW)
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[Cutshort] Bot challenge encountered on '{cfg['term']}'. Halting Cutshort gracefully.")
                break
            for job in res.jobs:
                job.source = "cutshort"
                jobs.append(job)
            logger.info(f"[Cutshort] Fetched {len(res.jobs)} items.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from Cutshort via in-house scraper: {e}")
    return jobs


def fetch_freshersworld_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from Freshersworld via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Executing in-house Freshersworld scraper...")
    scraper = FreshersworldScraper()
    search_configs = [
        {"term": "Python Developer", "location": "bangalore", "limit": 20},
        {"term": "Backend Engineer", "location": "chennai", "limit": 15},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            logger.info(f"[Freshersworld] Scraping '{cfg['term']}' in '{cfg['location']}'...")
            res = scraper.scrape(search_term=cfg["term"], location=cfg["location"], results_wanted=cfg["limit"], hours_old=FRESHNESS_HOURS_WINDOW)
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[Freshersworld] Bot challenge encountered on '{cfg['term']}'. Halting Freshersworld gracefully.")
                break
            for job in res.jobs:
                job.source = "freshersworld"
                jobs.append(job)
            logger.info(f"[Freshersworld] Fetched {len(res.jobs)} items.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from Freshersworld via in-house scraper: {e}")
    return jobs


def fetch_hirist_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from Hirist via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Executing in-house Hirist scraper...")
    scraper = HiristScraper()
    search_configs = [
        {"term": "Python", "location": "Bangalore", "limit": 20},
        {"term": "FastAPI", "location": "Bangalore", "limit": 15},
        {"term": "AI Engineer", "location": "Bangalore", "limit": 15},
        {"term": "Backend", "location": "Chennai", "limit": 15},
        {"term": "Python", "location": "Chennai", "limit": 15},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            logger.info(f"[Hirist] Scraping '{cfg['term']}' in '{cfg['location']}'...")
            res = scraper.scrape(search_term=cfg["term"], location=cfg["location"], results_wanted=cfg["limit"], hours_old=FRESHNESS_HOURS_WINDOW)
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[Hirist] Bot challenge encountered on '{cfg['term']}'. Halting Hirist gracefully.")
                break
            for job in res.jobs:
                job.source = "hirist"
                jobs.append(job)
            logger.info(f"[Hirist] Fetched {len(res.jobs)} items.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from Hirist via in-house scraper: {e}")
    return jobs


def fetch_internshala_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from Internshala via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Executing in-house Internshala scraper...")
    scraper = InternshalaScraper()
    search_configs = [
        {"term": "Python", "location": "Bangalore", "limit": 20},
        {"term": "Backend Developer", "location": "Bangalore", "limit": 15},
        {"term": "Python", "location": "Chennai", "limit": 15},
        {"term": "Backend", "location": "Chennai", "limit": 15},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            logger.info(f"[Internshala] Scraping '{cfg['term']}' in '{cfg['location']}'...")
            res = scraper.scrape(search_term=cfg["term"], location=cfg["location"], results_wanted=cfg["limit"], hours_old=FRESHNESS_HOURS_WINDOW)
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[Internshala] Bot challenge encountered on '{cfg['term']}'. Halting Internshala gracefully.")
                break
            for job in res.jobs:
                job.source = "internshala"
                jobs.append(job)
            logger.info(f"[Internshala] Fetched {len(res.jobs)} items.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from Internshala via in-house scraper: {e}")
    return jobs


def fetch_shine_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from Shine via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Executing in-house Shine scraper...")
    scraper = ShineScraper()
    search_configs = [
        {"term": "Python", "location": "Bangalore", "limit": 20},
        {"term": "Backend", "location": "Chennai", "limit": 15},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            logger.info(f"[Shine] Scraping '{cfg['term']}' in '{cfg['location']}'...")
            res = scraper.scrape(search_term=cfg["term"], location=cfg["location"], results_wanted=cfg["limit"], hours_old=FRESHNESS_HOURS_WINDOW)
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[Shine] Bot challenge encountered on '{cfg['term']}'. Halting Shine gracefully.")
                break
            for job in res.jobs:
                job.source = "shine"
                jobs.append(job)
            logger.info(f"[Shine] Fetched {len(res.jobs)} items.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from Shine via in-house scraper: {e}")
    return jobs


def fetch_timesjobs_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches jobs from TimesJobs via in-house autonomous scraper."""
    logger.info("[IN-HOUSE] Executing in-house TimesJobs scraper...")
    scraper = TimesJobsScraper()
    search_configs = [
        {"term": "Python", "location": "Bangalore", "limit": 20},
        {"term": "Backend", "location": "Chennai", "limit": 15},
    ]
    jobs: List[Job] = []
    for cfg in search_configs:
        try:
            logger.info(f"[TimesJobs] Scraping '{cfg['term']}' in '{cfg['location']}'...")
            res = scraper.scrape(search_term=cfg["term"], location=cfg["location"], results_wanted=cfg["limit"], hours_old=FRESHNESS_HOURS_WINDOW)
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[TimesJobs] Bot challenge encountered on '{cfg['term']}'. Halting TimesJobs gracefully.")
                break
            for job in res.jobs:
                job.source = "timesjobs"
                jobs.append(job)
            logger.info(f"[TimesJobs] Fetched {len(res.jobs)} items.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch from TimesJobs via in-house scraper: {e}")
    return jobs


def fetch_google_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Google Jobs scraper retired in favor of direct in-house crawling."""
    logger.info("[INFO] Google Jobs Apify scraper retired in favor of in-house scraping pipeline.")
    return []


def fetch_remotive_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches high-quality worldwide remote Python and backend jobs from Remotive API."""
    logger.info("[IN-HOUSE] Executing Remotive worldwide remote scraper...")
    scraper = RemotiveScraper()
    jobs: List[Job] = []
    try:
        res = scraper.scrape(search_term="python", results_wanted=25, hours_old=FRESHNESS_HOURS_WINDOW)
        for item in res.jobs:
            c_job = to_job_agent_model(item)
            c_job.source = "remotive"
            c_job.title = clean_job_title(c_job.title)
            jobs.append(c_job)
        logger.info(f"[Remotive] Synced {len(jobs)} worldwide remote roles.")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch from Remotive: {e}")
    return jobs


def fetch_indeed_abroad_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches international relocation roles from Indeed UAE (Dubai) and Singapore."""
    logger.info("[IN-HOUSE] Executing Indeed International (Dubai & Singapore) scraper...")
    jobs: List[Job] = []
    search_configs = [
        {"position": "Python Developer", "country": "AE", "location": "Dubai", "limit": 15},
        {"position": "Backend Developer Python", "country": "AE", "location": "Dubai", "limit": 15},
        {"position": "Python Developer", "country": "SG", "location": "Singapore", "limit": 15},
    ]
    for cfg in search_configs:
        try:
            scraper = IndeedScraper(country=cfg["country"])
            res = scraper.scrape(
                search_term=cfg["position"],
                location=cfg["location"],
                results_wanted=cfg["limit"],
                hours_old=FRESHNESS_HOURS_WINDOW,
            )
            for item in res.jobs:
                c_job = to_job_agent_model(item)
                c_job.source = "indeed_abroad"
                c_job.title = clean_job_title(c_job.title)
                jobs.append(c_job)
            logger.info(f"[Indeed Abroad] Fetched {len(res.jobs)} items for {cfg['location']}.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch Indeed abroad for {cfg['location']}: {e}")
    return jobs


def fetch_jobicy_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches high-quality worldwide remote Python and backend jobs from Jobicy REST API."""
    logger.info("[IN-HOUSE] Executing Jobicy worldwide remote scraper...")
    scraper = JobicyScraper()
    jobs: List[Job] = []
    try:
        res = scraper.scrape(search_term="python", geo="anywhere", results_wanted=30, hours_old=FRESHNESS_HOURS_WINDOW)
        for item in res.jobs:
            c_job = to_job_agent_model(item)
            c_job.source = "jobicy"
            c_job.title = clean_job_title(c_job.title)
            jobs.append(c_job)
        logger.info(f"[Jobicy] Synced {len(jobs)} worldwide remote roles.")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch from Jobicy: {e}")
    return jobs


def fetch_wwr_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches backend and full-stack worldwide remote jobs from We Work Remotely (WWR) feeds."""
    logger.info("[IN-HOUSE] Executing We Work Remotely (WWR) feed scraper...")
    scraper = WeWorkRemotelyScraper()
    jobs: List[Job] = []
    try:
        res = scraper.scrape(search_term="python", results_wanted=25, hours_old=FRESHNESS_HOURS_WINDOW)
        for item in res.jobs:
            c_job = to_job_agent_model(item)
            c_job.source = "wwr"
            c_job.title = clean_job_title(c_job.title)
            jobs.append(c_job)
        logger.info(f"[WWR] Synced {len(jobs)} remote roles.")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch from WWR: {e}")
    return jobs


def fetch_arbeitnow_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches global remote and visa-sponsored tech jobs from Arbeitnow REST API."""
    logger.info("[IN-HOUSE] Executing Arbeitnow global remote/visa scraper...")
    scraper = ArbeitnowScraper()
    jobs: List[Job] = []
    try:
        res = scraper.scrape(search_term="python", results_wanted=25, hours_old=FRESHNESS_HOURS_WINDOW)
        for item in res.jobs:
            c_job = to_job_agent_model(item)
            c_job.source = "arbeitnow"
            c_job.title = clean_job_title(c_job.title)
            jobs.append(c_job)
        logger.info(f"[Arbeitnow] Synced {len(jobs)} remote/visa roles.")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch from Arbeitnow: {e}")
    return jobs


def fetch_relocateme_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches software jobs with verified employer relocation and visa sponsorship from Relocate.me."""
    logger.info("[IN-HOUSE] Executing Relocate.me verified visa/relocation scraper...")
    scraper = RelocateMeScraper()
    jobs: List[Job] = []
    try:
        res = scraper.scrape(search_term="python", results_wanted=25, hours_old=FRESHNESS_HOURS_WINDOW)
        for item in res.jobs:
            c_job = to_job_agent_model(item)
            c_job.source = "relocateme"
            c_job.title = clean_job_title(c_job.title)
            jobs.append(c_job)
        logger.info(f"[Relocate.me] Synced {len(jobs)} visa/relocation roles.")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch from Relocate.me: {e}")
    return jobs


def fetch_linkedin_abroad_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches international relocation roles from LinkedIn for target expat hubs (Dubai, UAE & Singapore)."""
    logger.info("[IN-HOUSE] Executing LinkedIn International (Dubai & Singapore) scraper...")
    scraper = LinkedInScraper(fetch_descriptions=True, max_details_per_query=3, request_delay=1.0)
    jobs: List[Job] = []
    search_configs = [
        {"keyword": "Python Developer", "location": "Dubai, United Arab Emirates", "maxItems": 15},
        {"keyword": "Python Developer", "location": "Singapore", "maxItems": 15},
    ]
    for cfg in search_configs:
        try:
            res = scraper.scrape(
                search_term=cfg["keyword"],
                location=cfg["location"],
                results_wanted=cfg["maxItems"],
                hours_old=FRESHNESS_HOURS_WINDOW,
            )
            if res.bot_detected or res.status == "BLOCKED":
                logger.warning(f"[LinkedIn Abroad] Challenge encountered on '{cfg['keyword']}'. Halting gracefully.")
                break
            for job in res.jobs:
                job.source = "linkedin_abroad"
                jobs.append(job)
            logger.info(f"[LinkedIn Abroad] Fetched {len(res.jobs)} items for {cfg['location']}.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch LinkedIn abroad for {cfg['location']}: {e}")
    return jobs


def fetch_yc_jobs(use_cache: bool = False, cache_file: Any = None) -> List[Job]:
    """Fetches high-growth, early-stage startup engineering jobs from Y Combinator Work at a Startup."""
    logger.info("[IN-HOUSE] Executing Y Combinator Work at a Startup scraper...")
    scraper = YCWorkAtAStartupScraper()
    jobs: List[Job] = []
    try:
        res = scraper.scrape(
            search_term="Software Engineer",
            results_wanted=30,
            hours_old=FRESHNESS_HOURS_WINDOW,
        )
        for job in res.jobs:
            job.source = "yc"
            jobs.append(job)
        logger.info(f"[YC] Synced {len(jobs)} early-stage startup engineering roles.")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch from Y Combinator Work at a Startup: {e}")
    return jobs

