from sqlalchemy import select
from sqlalchemy.orm import Session

from processing.deduplication import normalize_company
from storage.models.company import Company


class CompanyRepository:
    """Data access repository for Company entities."""

    @staticmethod
    def get_or_create_company(
        session: Session,
        name: str,
        website: str | None = None,
        career_url: str | None = None,
        ats_provider: str | None = None,
        is_target: bool = False,
    ) -> Company:
        """Finds an existing company by normalized name or creates a new record."""
        display_name = (name or "Unknown Company").strip()
        norm_name = normalize_company(display_name)
        if not norm_name:
            norm_name = display_name.lower()

        stmt = select(Company).where(Company.normalized_name == norm_name)
        company = session.scalar(stmt)

        if company:
            # Update attributes if newly discovered
            if website and not company.website:
                company.website = website
            if career_url and not company.career_url:
                company.career_url = career_url
            if ats_provider and not company.ats_provider:
                company.ats_provider = ats_provider
            if is_target and not company.is_target:
                company.is_target = True
            return company

        # Create new company
        company = Company(
            name=display_name,
            normalized_name=norm_name,
            website=website,
            career_url=career_url,
            ats_provider=ats_provider,
            is_target=is_target,
            is_active=True,
            metadata_json={},
        )
        session.add(company)
        session.flush()
        return company
