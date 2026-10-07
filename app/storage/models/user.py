from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.models.base import ActiveMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from storage.models.application import Application


class User(Base, TimestampMixin, ActiveMixin):
    """User account / job seeker profile."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    target_role: Mapped[str] = mapped_column(
        String(150),
        default="Python Backend Engineer",
        nullable=False,
    )
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferences_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


    # Relationships
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} name='{self.name}' email='{self.email}'>"
