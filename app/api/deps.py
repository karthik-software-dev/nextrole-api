from typing import Generator
from sqlalchemy.orm import Session

from storage.database import SessionLocal


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a managed database session."""
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
