from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.core.redis import redis_client
import logging

# Add this to your existing main.py
@app.get("/health")
async def health_check():
    try:
        # Check database connection
        from app.db.database import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        
        # Check Redis connection
        redis_healthy = redis_client.health_check()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "database": "connected",
                "redis": "connected" if redis_healthy else "disconnected",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
