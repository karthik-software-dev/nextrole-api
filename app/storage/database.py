import logging
import os
from contextlib import contextmanager
from urllib.parse import urlparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from config import DATABASE_URL
from storage.models import Base, User

logger = logging.getLogger(__name__)


def ensure_database_exists(db_url: str = DATABASE_URL) -> None:
    """Connects to the default PostgreSQL maintenance database and creates the target database if it does not exist."""
    if not db_url.startswith("postgres"):
        return

    parsed = urlparse(db_url)
    target_db = parsed.path.lstrip("/").split("?")[0]
    if not target_db:
        return

    # If the target is already defaultdb / postgres or hosted on Aiven, bypass maintenance check
    if target_db in ("defaultdb", "postgres") or "aiven" in (parsed.hostname or "").lower():
        return

    # Connection parameters for PostgreSQL maintenance database
    user = parsed.username or "postgres"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432

    # Connect to the default 'postgres' database to check/create the target database
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        exists = cur.fetchone()

        if not exists:
            cur.execute(f'CREATE DATABASE "{target_db}" ENCODING \'UTF8\';')
            print(f"[DATABASE] Created PostgreSQL database '{target_db}' successfully.")

        cur.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Could not verify/create database '{target_db}' via maintenance connection: {e}")


# Helper to normalize URL scheme for SQLAlchemy compatibility
def _get_sqlalchemy_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


# Create SQLAlchemy Engine safely based on dialect
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        _get_sqlalchemy_url(DATABASE_URL),
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", "3" if os.getenv("RENDER") else "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "5" if os.getenv("RENDER") else "10")),
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_db_connection() -> bool:
    """Performs a lightweight ping check to verify database connectivity."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database health ping failed: {e}")
        return False


@contextmanager
def get_db():
    """Context manager for obtaining a database session."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def seed_default_user(session: Session) -> User:
    """Ensures default admin user profile exists with secure password hash for personal application tracking."""
    from config import ADMIN_EMAIL, ADMIN_INITIAL_PASSWORD
    from core.security import hash_password

    admin_user = session.scalar(select(User).where(User.email == ADMIN_EMAIL).limit(1))
    if not admin_user:
        legacy_user = session.scalar(select(User).limit(1))
        if legacy_user:
            legacy_user.email = ADMIN_EMAIL
            legacy_user.name = "Rahul Karthik"
            if ADMIN_INITIAL_PASSWORD:
                legacy_user.hashed_password = hash_password(ADMIN_INITIAL_PASSWORD)
            session.commit()
            session.refresh(legacy_user)
            return legacy_user
        else:
            admin_user = User(
                name="Rahul Karthik",
                email=ADMIN_EMAIL,
                target_role="Python Backend Engineer",
                is_active=True,
                hashed_password=hash_password(ADMIN_INITIAL_PASSWORD) if ADMIN_INITIAL_PASSWORD else None,
            )
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            return admin_user
    else:
        if not admin_user.hashed_password and ADMIN_INITIAL_PASSWORD:
            admin_user.hashed_password = hash_password(ADMIN_INITIAL_PASSWORD)
            session.commit()
            session.refresh(admin_user)
        return admin_user


def init_db() -> bool:
    """Initializes PostgreSQL database, executes DDL to create tables, and seeds initial data."""
    try:
        ensure_database_exists(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        if not DATABASE_URL.startswith("sqlite"):
            from sqlalchemy import text
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences_json JSONB DEFAULT '{}'::jsonb;"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);"))
        with get_db() as session:
            seed_default_user(session)
        print(f"[DATABASE] Connected & schema verified on '{DATABASE_URL.split('/')[-1]}'")
        return True
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        return False

