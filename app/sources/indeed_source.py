from apify_client import ApifyClient

from config import APIFY_API_TOKEN


ACTOR_ID = "misceres/indeed-scraper"


def fetch_indeed_jobs():
    client = ApifyClient(APIFY_API_TOKEN)

    run_input = {
        "position": "Python Backend Engineer",
        "maxItemsPerSearch": 50,
        "country": "IN",
        "location": "Bengaluru",
        "parseCompanyDetails": True,
        "saveOnlyUniqueItems": True,
    }

    run = client.actor(ACTOR_ID).call(
        run_input=run_input
    )

    jobs = list(
        client.dataset(
            run["defaultDatasetId"]
        ).iterate_items()
    )

    return jobs