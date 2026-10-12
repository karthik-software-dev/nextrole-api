"""Centralized location normalization constants, city synonyms, and geographic classifiers."""

CITY_SYNONYMS: dict[str, list[str]] = {
    "Bengaluru": ["bengaluru", "bangalore"],
    "Chennai": ["chennai", "madras"],
    "Hyderabad": ["hyderabad"],
    "Pune": ["pune"],
    "Delhi NCR": ["gurgaon", "gurugram", "noida", "delhi"],
    "Mumbai": ["mumbai", "bombay"],
}

BANGALORE_KEYWORDS: list[str] = ["bengaluru", "bangalore", "karnataka"]
CHENNAI_KEYWORDS: list[str] = ["chennai", "tamil nadu", "madras"]
TARGET_ABROAD_HUBS: list[str] = ["dubai", "uae", "singapore", "emirates"]

FOREIGN_LOCATIONS: list[str] = [
    "london", "united kingdom", "uk",
    "new york", "ny", "united states", "usa", "san francisco", "california",
    "seattle", "washington", "toronto", "canada", "berlin", "germany",
    "sydney", "australia", "singapore", "dubai", "uae", "ireland", "dublin",
    "netherlands", "amsterdam", "paris", "france", "emea", "latam", "europe",
    "north america",
]

INDIA_LOCATIONS: list[str] = [
    "india", "bengaluru", "bangalore", "chennai", "hyderabad",
    "pune", "mumbai", "delhi", "noida", "gurgaon", "gurugram",
    "karnataka", "tamil nadu", "telangana", "maharashtra",
]

GLOBAL_REMOTE_KEYWORDS: list[str] = [
    "worldwide", "anywhere", "global", "all locations", "remote - any",
    "remote (worldwide)", "remote - worldwide", "remote, anywhere", "work from anywhere",
]

VISA_SPONSOR_KEYWORDS: list[str] = [
    "visa sponsorship", "sponsorship available", "sponsorship provided",
    "sponsors visa", "visa support", "relocation assistance", "relocation package",
    "relocation support", "relocation provided", "open to relocation",
    "we sponsor visas", "we sponsor work visas", "relocation to",
]


def extract_canonical_city(location: str | None) -> str | None:
    """Extracts prominent city from raw location string using standardized city synonyms.

    Falls back to the first comma-separated segment if no known city matches.
    """
    if not location:
        return None
    loc_lower = location.lower()
    for canonical_city, aliases in CITY_SYNONYMS.items():
        if any(alias in loc_lower for alias in aliases):
            return canonical_city
    parts = [p.strip() for p in location.split(",") if p.strip()]
    return parts[0] if parts else None
