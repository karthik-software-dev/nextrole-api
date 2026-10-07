from pydantic import BaseModel, Field


class UserProfileOut(BaseModel):
    """Candidate profile output schema."""

    id: int
    name: str
    email: str
    target_role: str
    skills: list[str] = [
        "Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Redis",
        "RabbitMQ", "Celery", "System Design", "Scalability",
        "Data Structures & Algorithms", "Linear DSA", "Problem Solving",
        "Clean Code & SOLID", "REST APIs", "Docker", "Git"
    ]


class UserProfileUpdate(BaseModel):
    """Candidate profile update schema."""

    name: str | None = Field(None, min_length=1, max_length=150)
    email: str | None = Field(None, min_length=3, max_length=255)
    target_role: str | None = Field(None, min_length=1, max_length=150)
    skills: list[str] | None = None


class SearchScoringOut(BaseModel):
    """Job search & scoring preferences schema."""

    min_experience: int = 1
    max_experience: int = 5
    min_score: float = 8.0
    min_salary_lpa: float = 4.0
    target_salary_min_lpa: float = 5.0
    target_salary_max_lpa: float = 15.0
    target_locations: list[str] = ["Bangalore", "Chennai", "Remote"]


class SearchScoringUpdate(BaseModel):
    """Job search & scoring update input schema."""

    min_experience: int | None = Field(None, ge=0, le=20)
    max_experience: int | None = Field(None, ge=0, le=30)
    min_score: float | None = Field(None, ge=0.0, le=50.0)
    min_salary_lpa: float | None = Field(None, ge=0.0, le=100.0)
    target_salary_min_lpa: float | None = Field(None, ge=0.0, le=100.0)
    target_salary_max_lpa: float | None = Field(None, ge=0.0, le=100.0)
    target_locations: list[str] | None = None


class IntegrationsOut(BaseModel):
    """External API & scraper integrations schema."""

    apify_api_token: str | None = None
    is_apify_configured: bool = False


class IntegrationsUpdate(BaseModel):
    """External API & scraper integrations update schema."""

    apify_api_token: str | None = None


class ApifyTestIn(BaseModel):
    """Payload to test Apify API token."""

    token: str = Field(..., min_length=5)


class ApifyTestOut(BaseModel):
    """Result of Apify token validation check."""

    valid: bool
    username: str | None = None
    message: str


class SettingsOut(BaseModel):
    """Aggregated settings payload for the Settings page."""

    profile: UserProfileOut
    scoring: SearchScoringOut
    integrations: IntegrationsOut


class SettingsUpdateIn(BaseModel):
    """Update payload for Settings page."""

    profile: UserProfileUpdate | None = None
    scoring: SearchScoringUpdate | None = None
    integrations: IntegrationsUpdate | None = None
