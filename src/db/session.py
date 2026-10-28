from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import DATABASE_URL
from src.db.models import Base

# Database engine and session factory
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(bind_engine=engine) -> None:
    """Creates database tables if they do not exist."""
    Base.metadata.create_all(bind=bind_engine)


def get_db() -> Generator[Session, None, None]:
    """Provides a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
