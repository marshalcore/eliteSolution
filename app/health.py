from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.db.database import get_db
from app.core.redis import redis_client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def add_health_endpoint(app: FastAPI):
    @app.get("/health", summary="Health Check", tags=["Health"])
    async def health_check():
        try:
            # Check database connection
            db_healthy = False
            try:
                db = next(get_db())
                db.execute(text("SELECT 1"))
                db_healthy = True
                logger.info("Database connection: OK")
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                db_healthy = False

            # Check Redis connection
            redis_healthy = redis_client.health_check()
            if redis_healthy:
                logger.info("Redis connection: OK")
            else:
                logger.warning("Redis connection: Failed")

            # Overall status
            overall_healthy = db_healthy and redis_healthy
            
            status_code = 200 if overall_healthy else 503
            
            return JSONResponse(
                status_code=status_code,
                content={
                    "status": "healthy" if overall_healthy else "unhealthy",
                    "database": "connected" if db_healthy else "disconnected",
                    "redis": "connected" if redis_healthy else "disconnected",
                    "timestamp": datetime.utcnow().isoformat(),
                    "service": "elitesolution-financial-api",
                    "version": "1.0.0"
                }
            )
            
        except Exception as e:
            logger.error(f"Health check endpoint error: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    @app.get("/", summary="Root Endpoint", tags=["Health"])
    async def root():
        return {
            "message": "EliteSolution Financial API",
            "status": "operational",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }
