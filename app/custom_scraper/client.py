"""Low-level HTTP client for Indeed GraphQL API."""

import logging
import random
import time
from typing import Any, Dict, Optional, Tuple
import httpx

logger = logging.getLogger("custom_scraper.client")

INDEED_GRAPHQL_URL = "https://apis.indeed.com/graphql"

# Default mobile API key and headers used by Indeed mobile app
DEFAULT_API_KEY = "161092c2017b5bbab13edb12461a62d5a833871e7cad6d9d475304573de67ac8"

GRAPHQL_SEARCH_QUERY = """
query GetJobData {{
    jobSearch(
        {what_clause}
        {location_clause}
        limit: {limit}
        {cursor_clause}
        sort: RELEVANCE
        {filters_clause}
    ) {{
        pageInfo {{
            nextCursor
        }}
        results {{
            trackingKey
            job {{
                key
                title
                datePublished
                dateOnIndeed
                description {{
                    html
                }}
                location {{
                    countryName
                    countryCode
                    admin1Code
                    city
                    postalCode
                    streetAddress
                    formatted {{
                        short
                        long
                    }}
                }}
                compensation {{
                    estimated {{
                        currencyCode
                        baseSalary {{
                            unitOfWork
                            range {{
                                ... on Range {{
                                    min
                                    max
                                }}
                            }}
                        }}
                    }}
                    baseSalary {{
                        unitOfWork
                        range {{
                            ... on Range {{
                                min
                                max
                            }}
                        }}
                    }}
                    currencyCode
                }}
                attributes {{
                    key
                    label
                }}
                employer {{
                    relativeCompanyPageUrl
                    name
                    dossier {{
                        employerDetails {{
                            addresses
                            industry
                            employeesLocalizedLabel
                            revenueLocalizedLabel
                            briefDescription
                            ceoName
                        }}
                        images {{
                            headerImageUrl
                            squareLogoUrl
                        }}
                        links {{
                            corporateWebsite
                        }}
                    }}
                }}
                recruit {{
                    viewJobUrl
                    detailedSalary
                    workSchedule
                }}
                source {{
                    name
                }}
            }}
        }}
    }}
}}
"""


class IndeedClient:
    """Client for directly querying Indeed's GraphQL backend."""

    def __init__(
        self,
        api_key: str = DEFAULT_API_KEY,
        country: str = "IN",
        timeout: float = 20.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.country = country.upper()
        self.timeout = timeout
        self.max_retries = max_retries

        self.headers = {
            "Host": "apis.indeed.com",
            "content-type": "application/json",
            "indeed-api-key": self.api_key,
            "accept": "application/json",
            "indeed-locale": "en-US",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Indeed App 193.1",
            "indeed-app-info": "appv=193.1; appid=com.indeed.jobsearch; osv=16.6.1; os=ios; dtype=phone",
            "indeed-co": self.country,
        }

        self._client = httpx.Client(
            headers=self.headers,
            timeout=self.timeout,
            verify=False,
        )

    def close(self):
        """Close underlying HTTP client connection."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def fetch_job_page(
        self,
        search_term: str,
        location: str = "Chennai",
        radius_miles: int = 50,
        limit: int = 50,
        cursor: Optional[str] = None,
        hours_old: Optional[int] = 336,
    ) -> Tuple[list[dict[str, Any]], Optional[str]]:
        """Fetches a single page of job results.

        Returns (results_list, next_cursor).
        """
        what_clause = f'what: "{search_term}"' if search_term else ""
        location_clause = f'location: {{where: "{location}", radius: {radius_miles}, radiusUnit: MILES}}' if location else ""
        cursor_clause = f'cursor: "{cursor}"' if cursor else ""

        filters_clause = ""
        if hours_old:
            filters_clause = f'filters: {{ date: {{ field: "dateOnIndeed", start: "{hours_old}h" }} }}'

        formatted_query = GRAPHQL_SEARCH_QUERY.format(
            what_clause=what_clause,
            location_clause=location_clause,
            limit=limit,
            cursor_clause=cursor_clause,
            filters_clause=filters_clause,
        )

        payload = {"query": formatted_query}

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Fetching Indeed page (attempt {attempt}/{self.max_retries})...")
                response = self._client.post(INDEED_GRAPHQL_URL, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    search_data = data.get("data", {}).get("jobSearch", {})
                    results = search_data.get("results", [])
                    next_cursor = (search_data.get("pageInfo") or {}).get("nextCursor")
                    return results, next_cursor

                elif response.status_code in (429, 502, 503, 504):
                    backoff = (2 ** attempt) + random.uniform(0.5, 1.5)
                    logger.warning(f"Indeed returned status {response.status_code}. Backing off {backoff:.1f}s...")
                    time.sleep(backoff)
                else:
                    logger.error(f"Unexpected status code {response.status_code}: {response.text[:200]}")
                    break

            except httpx.RequestError as exc:
                backoff = (2 ** attempt) + random.uniform(0.5, 1.5)
                logger.warning(f"Request failed: {exc}. Retrying in {backoff:.1f}s...")
                time.sleep(backoff)

        logger.error(f"Failed to fetch jobs for '{search_term}' in '{location}' after {self.max_retries} attempts.")
        return [], None
