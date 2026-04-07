from sqlalchemy import create_engine, make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Create the SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

# Read-only engine (credentials from environment variables)
readonly_url = make_url(settings.DATABASE_URL).set(
    username=settings.READONLY_DB_USER, password=settings.READONLY_DB_PASSWORD
)
readonly_engine = create_engine(
    readonly_url,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionReadOnly = sessionmaker(autocommit=False, autoflush=False, bind=readonly_engine)

Base = declarative_base()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_readonly_db():
    db = SessionReadOnly()
    try:
        yield db
    finally:
        db.close()
