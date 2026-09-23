from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.models.base import ActiveMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from storage.models.job import Job


class Company(Base, TimestampMixin, ActiveMixin):
    """Represents an employer / hiring company."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    career_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    ats_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_target: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} name='{self.name}' normalized='{self.normalized_name}'>"
