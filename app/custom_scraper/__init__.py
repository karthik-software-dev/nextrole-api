"""Custom In-House Scraper Package.

An autonomous, Apify-free scraping engine designed for discovering,
crawling, and extracting jobs across 23 integrated sources.
"""

from datetime import datetime, timezone

CURRENT_DATE = datetime(2026, 9, 28, tzinfo=timezone.utc)

# 1. Scraper Classes
from .indeed_scraper import IndeedScraper
from .naukri_scraper import NaukriScraper
from .linkedin_scraper import LinkedInScraper
from .wellfound_scraper import WellfoundScraper
from .cutshort_scraper import CutshortScraper
from .hirist_scraper import HiristScraper
from .shine_scraper import ShineScraper
from .timesjobs_scraper import TimesJobsScraper
from .internshala_scraper import InternshalaScraper
from .apna_scraper import ApnaScraper
from .freshersworld_scraper import FreshersworldScraper, scrape_freshersworld_jobs
from .greenhouse_scraper import GreenhouseScraper, scrape_greenhouse_jobs
from .lever_scraper import LeverScraper, scrape_lever_jobs
from .ashby_scraper import AshbyScraper, scrape_ashby_jobs
from .workday_scraper import WorkdayScraper, scrape_workday_jobs
from .smartrecruiters_scraper import SmartRecruitersScraper, scrape_smartrecruiters_jobs
from .recruitee_scraper import RecruiteeScraper, scrape_recruitee_jobs
from .workable_scraper import WorkableScraper, scrape_workable_jobs
from .teamtailor_scraper import TeamtailorScraper, scrape_teamtailor_jobs
from .bamboohr_scraper import BambooHRScraper
from .personio_scraper import PersonioScraper
from .breezy_scraper import BreezyScraper
from .remotive_scraper import RemotiveScraper
from .jobicy_scraper import JobicyScraper
from .wwr_scraper import WeWorkRemotelyScraper
from .arbeitnow_scraper import ArbeitnowScraper
from .relocateme_scraper import RelocateMeScraper
from .yc_scraper import YCWorkAtAStartupScraper, YCWorkAtAStartupScrapeResult
from .models import JobItem, ScraperResult

# 2. ATS Fetchers & Dispatchers
from .ats_source import (
    fetch_target_company_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_smartrecruiters_jobs,
    fetch_workday_jobs,
    fetch_ashby_jobs,
    fetch_bamboohr_jobs,
    fetch_personio_jobs,
    fetch_recruitee_jobs,
    fetch_workable_jobs,
    fetch_teamtailor_jobs,
    fetch_breezy_jobs,
)

# 3. Portal Fetchers & Dispatchers
from .fetchers import (
    fetch_naukri_jobs,
    fetch_indeed_jobs,
    fetch_linkedin_jobs,
    fetch_wellfound_jobs,
    fetch_apna_jobs,
    fetch_cutshort_jobs,
    fetch_freshersworld_jobs,
    fetch_hirist_jobs,
    fetch_internshala_jobs,
    fetch_shine_jobs,
    fetch_timesjobs_jobs,
    fetch_google_jobs,
    fetch_remotive_jobs,
    fetch_indeed_abroad_jobs,
    fetch_jobicy_jobs,
    fetch_wwr_jobs,
    fetch_arbeitnow_jobs,
    fetch_relocateme_jobs,
    fetch_linkedin_abroad_jobs,
    fetch_yc_jobs,
)

__all__ = [
    # Classes
    "IndeedScraper",
    "NaukriScraper",
    "LinkedInScraper",
    "WellfoundScraper",
    "CutshortScraper",
    "HiristScraper",
    "ShineScraper",
    "TimesJobsScraper",
    "InternshalaScraper",
    "ApnaScraper",
    "FreshersworldScraper",
    "GreenhouseScraper",
    "LeverScraper",
    "AshbyScraper",
    "WorkdayScraper",
    "SmartRecruitersScraper",
    "RecruiteeScraper",
    "WorkableScraper",
    "TeamtailorScraper",
    "BambooHRScraper",
    "PersonioScraper",
    "BreezyScraper",
    "RemotiveScraper",
    "JobicyScraper",
    "WeWorkRemotelyScraper",
    "ArbeitnowScraper",
    "RelocateMeScraper",
    "YCWorkAtAStartupScraper",
    "YCWorkAtAStartupScrapeResult",
    "JobItem",
    "ScraperResult",
    # Portal Fetchers
    "fetch_naukri_jobs",
    "fetch_indeed_jobs",
    "fetch_linkedin_jobs",
    "fetch_wellfound_jobs",
    "fetch_apna_jobs",
    "fetch_cutshort_jobs",
    "fetch_freshersworld_jobs",
    "fetch_hirist_jobs",
    "fetch_internshala_jobs",
    "fetch_shine_jobs",
    "fetch_timesjobs_jobs",
    "fetch_google_jobs",
    "fetch_remotive_jobs",
    "fetch_indeed_abroad_jobs",
    "fetch_jobicy_jobs",
    "fetch_wwr_jobs",
    "fetch_arbeitnow_jobs",
    "fetch_relocateme_jobs",
    "fetch_linkedin_abroad_jobs",
    "fetch_yc_jobs",
    # ATS Fetchers
    "fetch_target_company_jobs",
    "fetch_greenhouse_jobs",
    "fetch_lever_jobs",
    "fetch_smartrecruiters_jobs",
    "fetch_workday_jobs",
    "fetch_ashby_jobs",
    "fetch_bamboohr_jobs",
    "fetch_personio_jobs",
    "fetch_recruitee_jobs",
    "fetch_workable_jobs",
    "fetch_teamtailor_jobs",
    "fetch_breezy_jobs",
    # Specific ATS direct scrapers
    "scrape_freshersworld_jobs",
    "scrape_greenhouse_jobs",
    "scrape_lever_jobs",
    "scrape_ashby_jobs",
    "scrape_workday_jobs",
    "scrape_smartrecruiters_jobs",
    "scrape_recruitee_jobs",
    "scrape_workable_jobs",
    "scrape_teamtailor_jobs",
]
