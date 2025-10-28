# run.py

import logging
import uvicorn
import os
import time
from sqlalchemy.exc import OperationalError
from app.db import Base, engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔇 Silence SQLAlchemy noisy logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)

def init_db():
    """Initialize database tables with retry logic and error handling"""
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Attempting to connect to database (Attempt {attempt + 1}/{max_retries})...")
            
            # Test connection first
            with engine.connect() as conn:
                logger.info("✅ Database connection successful!")
            
            # Create tables
            logger.info("🔄 Creating database tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created successfully!")
            return True
            
        except OperationalError as e:
            logger.error(f"❌ Database connection failed (Attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("🚨 All database connection attempts failed!")
                return False
                
        except Exception as e:
            logger.error(f"❌ Unexpected error during database initialization: {e}")
            return False

# Use the PORT environment variable provided by Render
port = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    # Try to initialize database, but don't crash if it fails
    db_success = init_db()
    
    if not db_success:
        logger.warning("⚠️  Starting server without database initialization...")
    else:
        logger.info("✅ Database initialized successfully!")
    
    # Start the server regardless of database status
    logger.info(f"🚀 Starting FastAPI server on port {port}...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )