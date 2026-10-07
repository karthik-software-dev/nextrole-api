from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.security import decode_access_token
from storage.database import SessionLocal
from storage.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a managed database session."""
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> User:
    """FastAPI dependency requiring a valid JWT Bearer token and returning the authenticated User."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(auth.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or malformed authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload["sub"]
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists or is deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> Optional[User]:
    """FastAPI dependency providing optional authentication without raising 401 if unauthenticated."""
    if not auth or not auth.credentials:
        return None

    payload = decode_access_token(auth.credentials)
    if not payload or not payload.get("sub"):
        return None

    email = payload["sub"]
    return db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
