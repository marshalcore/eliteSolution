#  app/db/session.py
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import OperationalError, DisconnectionError
from app.core.config import settings
import time

# Determine if we're using SQLite or PostgreSQL
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# ✅ FIXED: Enhanced database connection with better error handling and reconnection
if is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
        pool_timeout=30,
        echo=False  # Set to True for debugging
    )

# ✅ FIXED: Add connection validation
@event.listens_for(engine, "engine_connect")
def ping_connection(connection, branch):
    if branch:
        return
    try:
        connection.scalar("SELECT 1")
    except (OperationalError, DisconnectionError):
        raise DisconnectionError()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except (OperationalError, DisconnectionError) as e:
        db.rollback()
        print(f"❌ Database connection error: {e}")
        raise
    finally:
        db.close()