from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Replace with your actual DB connection string
# Example for SQLite (development):
DATABASE_URL = "postgresql://neondb_owner:npg_n9UeXrOA4Kaw@ep-green-credit-a19hsnai-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Example for PostgreSQL:
# DATABASE_URL = "postgresql://user:password@localhost:5432/mydb"

# Create SQLAlchemy engine
ENGINE = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ENGINE)

# Base class for models
Base = declarative_base()
