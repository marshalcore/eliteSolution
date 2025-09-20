# run.py

import logging
import uvicorn
import os
from app.db import Base, engine

# 🔇 Silence SQLAlchemy noisy logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)

# Create tables if they don't already exist
def init_db():
    Base.metadata.create_all(bind=engine)

# Use the PORT environment variable provided by Render
port = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    init_db()  # Ensure DB tables exist before starting the server
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"   # keep uvicorn logs
    )
