import pytest

from processing.location_normalizer import (
    extract_canonical_city,
    CITY_SYNONYMS,
    BANGALORE_KEYWORDS,
    CHENNAI_KEYWORDS,
    FOREIGN_LOCATIONS,
    INDIA_LOCATIONS,
)
from processing.prioritization import get_location_bucket
from models.job import Job


def test_extract_canonical_city_bengaluru():
    assert extract_canonical_city("Bengaluru, Karnataka") == "Bengaluru"
    assert extract_canonical_city("Bangalore Urban, India") == "Bengaluru"


def test_extract_canonical_city_chennai():
    assert extract_canonical_city("Chennai, Tamil Nadu") == "Chennai"
    assert extract_canonical_city("Madras, India") == "Chennai"


def test_extract_canonical_city_other_prominent():
    assert extract_canonical_city("Hyderabad, Telangana") == "Hyderabad"
    assert extract_canonical_city("Pune, Maharashtra") == "Pune"
    assert extract_canonical_city("Gurgaon, Haryana") == "Delhi NCR"
    assert extract_canonical_city("Noida, Uttar Pradesh") == "Delhi NCR"
    assert extract_canonical_city("Mumbai, Maharashtra") == "Mumbai"


def test_extract_canonical_city_fallback():
    assert extract_canonical_city("Coimbatore, Tamil Nadu") == "Coimbatore"
    assert extract_canonical_city(None) is None
    assert extract_canonical_city("") is None


def test_get_location_bucket_bangalore():
    job = Job(id="1", title="Backend Engineer", company="Acme", location="Bengaluru, Karnataka")
    assert get_location_bucket(job) == "BANGALORE"


def test_get_location_bucket_chennai():
    job = Job(id="2", title="Backend Engineer", company="Acme", location="Chennai, Tamil Nadu")
    assert get_location_bucket(job) == "CHENNAI"


def test_get_location_bucket_abroad_hub():
    job = Job(id="3", title="Backend Engineer", company="Acme", location="Dubai, UAE")
    assert get_location_bucket(job) == "ABROAD"


def test_get_location_bucket_remote_india():
    job = Job(id="4", title="Backend Engineer", company="Acme", location="Remote, India", is_remote=True)
    assert get_location_bucket(job) == "REMOTE_INDIA"


def test_get_location_bucket_foreign_unsponsored():
    job = Job(id="5", title="Backend Engineer", company="Acme", location="London, United Kingdom")
    assert get_location_bucket(job) == "FOREIGN"
