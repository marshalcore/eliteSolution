from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.core.config import settings

# Create the SQLAlchemy engine with safe DB URL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # ✅ reconnect if DB drops idle connections
    pool_size=10,         # ✅ base connection pool
    max_overflow=20       # ✅ allow temporary extra connections under load
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
