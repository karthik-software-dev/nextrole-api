import json
import logging
import os
import urllib.error
import urllib.request
from sqlalchemy import select
from sqlalchemy.orm import Session

from schemas.settings import (
    ApifyTestOut,
    IntegrationsOut,
    SearchScoringOut,
    SettingsOut,
    SettingsUpdateIn,
    UserProfileOut,
)
from storage.database import seed_default_user
from storage.models.user import User

logger = logging.getLogger(__name__)

DEFAULT_SCORING_PREFERENCES = {
    "min_experience": 1,
    "max_experience": 5,
    "min_score": 8.0,
    "min_salary_lpa": 4.0,
    "target_salary_min_lpa": 5.0,
    "target_salary_max_lpa": 15.0,
    "target_locations": ["Bangalore", "Chennai", "Remote"],
}

DEFAULT_SKILLS = [
    "Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Redis",
    "RabbitMQ", "Celery", "System Design", "Scalability",
    "Data Structures & Algorithms", "Linear DSA", "Problem Solving",
    "Clean Code & SOLID", "REST APIs", "Docker", "Git"
]


class SettingsService:
    """Service managing candidate profile identity, scoring preferences, and API integrations."""

    @classmethod
    def get_or_create_user(cls, session: Session) -> User:
        """Retrieves the primary active user or seeds default if absent."""
        stmt = select(User).where(User.is_active.is_(True)).order_by(User.id.asc()).limit(1)
        user = session.scalar(stmt)
        if not user:
            user = seed_default_user(session)
        return user

    @classmethod
    def get_active_apify_token(cls, session: Session) -> str:
        """Retrieves active Apify API token from user preferences with .env fallback."""
        try:
            user = cls.get_or_create_user(session)
            prefs = dict(user.preferences_json or {})
            token = (prefs.get("apify_api_token") or "").strip()
            if token and token != "your_apify_api_token_here":
                return token
        except Exception as e:
            logger.warning("Could not read apify token from DB: %s", e)
        env_token = os.getenv("APIFY_API_TOKEN", "").strip()
        return env_token if env_token != "your_apify_api_token_here" else ""

    @classmethod
    def get_settings(cls, session: Session) -> SettingsOut:
        """Retrieves current user profile, search scoring preferences, and API integrations."""
        user = cls.get_or_create_user(session)
        prefs = dict(user.preferences_json or {})

        scoring = SearchScoringOut(
            min_experience=prefs.get("min_experience", DEFAULT_SCORING_PREFERENCES["min_experience"]),
            max_experience=prefs.get("max_experience", DEFAULT_SCORING_PREFERENCES["max_experience"]),
            min_score=float(prefs.get("min_score", DEFAULT_SCORING_PREFERENCES["min_score"])),
            target_locations=prefs.get("target_locations", list(DEFAULT_SCORING_PREFERENCES["target_locations"])),
        )

        profile = UserProfileOut(
            id=user.id,
            name=user.name,
            email=user.email,
            target_role=user.target_role,
            skills=prefs.get("skills", DEFAULT_SKILLS),
        )

        raw_token = prefs.get("apify_api_token") or os.getenv("APIFY_API_TOKEN") or ""
        token_clean = raw_token.strip() if raw_token and raw_token != "your_apify_api_token_here" else ""
        integrations = IntegrationsOut(
            apify_api_token=token_clean,
            is_apify_configured=bool(token_clean),
        )

        return SettingsOut(profile=profile, scoring=scoring, integrations=integrations)

    @classmethod
    def update_settings(cls, session: Session, payload: SettingsUpdateIn) -> SettingsOut:
        """Updates user profile, scoring preferences, and integrations atomically."""
        user = cls.get_or_create_user(session)
        current_prefs = dict(user.preferences_json or {})
        prefs_changed = False

        # 1. Update Profile Fields if provided
        if payload.profile:
            if payload.profile.name is not None and payload.profile.name.strip():
                user.name = payload.profile.name.strip()
            if payload.profile.email is not None and payload.profile.email.strip():
                user.email = payload.profile.email.strip()
            if payload.profile.target_role is not None and payload.profile.target_role.strip():
                user.target_role = payload.profile.target_role.strip()
            if payload.profile.skills is not None:
                clean_skills = [s.strip() for s in payload.profile.skills if s.strip()]
                current_prefs["skills"] = clean_skills
                prefs_changed = True

        # 2. Update Scoring Preferences if provided
        if payload.scoring:
            if payload.scoring.min_experience is not None:
                current_prefs["min_experience"] = payload.scoring.min_experience
                prefs_changed = True
            if payload.scoring.max_experience is not None:
                current_prefs["max_experience"] = payload.scoring.max_experience
                prefs_changed = True
            if payload.scoring.min_score is not None:
                current_prefs["min_score"] = round(payload.scoring.min_score, 1)
                prefs_changed = True
            if payload.scoring.target_locations is not None:
                clean_locs = [loc.strip() for loc in payload.scoring.target_locations if loc.strip()]
                current_prefs["target_locations"] = clean_locs
                prefs_changed = True

        # 3. Update Integrations if provided
        if payload.integrations:
            if payload.integrations.apify_api_token is not None:
                cleaned_token = payload.integrations.apify_api_token.strip()
                current_prefs["apify_api_token"] = cleaned_token
                prefs_changed = True
                # Also keep environment variable in sync for the active process
                os.environ["APIFY_API_TOKEN"] = cleaned_token

        if prefs_changed:
            user.preferences_json = dict(current_prefs)

        session.commit()
        session.refresh(user)

        return cls.get_settings(session)

    @classmethod
    def test_apify_token(cls, token: str) -> ApifyTestOut:
        """Directly pings Apify users API to validate authentication in real-time."""
        clean_token = token.strip()
        if not clean_token or clean_token == "your_apify_api_token_here":
            return ApifyTestOut(valid=False, message="Please provide a valid non-empty Apify API token.")

        url = f"https://api.apify.com/v2/users/me?token={clean_token}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JobScout/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                user_info = data.get("data", {})
                username = user_info.get("username") or user_info.get("id") or "Authenticated User"
                return ApifyTestOut(
                    valid=True,
                    username=username,
                    message=f"Successfully authenticated as Apify user '{username}'.",
                )
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return ApifyTestOut(
                    valid=False,
                    message="Authentication failed (HTTP 401). Invalid or revoked Apify API token.",
                )
            return ApifyTestOut(
                valid=False,
                message=f"Apify API returned HTTP {e.code}: {e.reason}",
            )
        except Exception as e:
            logger.warning("Failed to ping Apify API: %s", e)
            return ApifyTestOut(
                valid=False,
                message=f"Network or connection error while validating token: {str(e)}",
            )
