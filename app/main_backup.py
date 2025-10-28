# app/main.py - COMPLETE UPDATED CODE

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
import time
import logging
from sqlalchemy import text  # ✅ ADD THIS IMPORT

from app.db import Base, engine, SessionLocal
from app.core.config import settings
from app.core.i18n import AdvancedLocalizationMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # ✅ FIXED: Enhanced CORS configuration
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3001",
    ]

    # If you have settings.CORS_ORIGINS, use this instead:
    # origins = settings.CORS_ORIGINS
    # if isinstance(origins, str):
    #     origins = [origin.strip() for origin in origins.split(",")]
    
    logger.info(f"🔄 Configuring CORS for origins: {origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
        expose_headers=["*"]   # Expose all headers
    )

    # Enhanced Localization Middleware
    app.add_middleware(AdvancedLocalizationMiddleware)

    # Static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": time.time()}

    @app.get("/api/v1/health")
    async def api_health_check():
        return {"status": "API healthy", "timestamp": time.time()}

    # Import routers
    from app.api.auth import router as auth_router
    from app.api.admin import router as admin_router
    from app.api.accounts import router as accounts_router
    from app.api.transactions import router as transactions_router
    from app.api.deposit import router as deposit_router
    from app.api.otp import router as otp_router
    from app.api.webhooks import router as webhooks_router
    from app.api.utils import router as utils_router
    from app.api.admin_routes.kyc import router as admin_kyc_router
    from app.api.kyc import router as kyc_router
    from app.api.account_management import router as account_management_router
    from app.api.trading import router as trading_router
    # ✅ FIXED: Import the PIN router
    from app.api.pin import router as pin_router

    # Include routers
    app.include_router(auth_router, prefix=settings.API_V1_STR)
    app.include_router(admin_router, prefix=settings.API_V1_STR)
    app.include_router(accounts_router, prefix=settings.API_V1_STR)
    app.include_router(transactions_router, prefix=settings.API_V1_STR)
    app.include_router(deposit_router, prefix=settings.API_V1_STR)
    app.include_router(otp_router, prefix=settings.API_V1_STR)
    app.include_router(webhooks_router, prefix=settings.API_V1_STR)
    app.include_router(utils_router, prefix=settings.API_V1_STR)
    app.include_router(admin_kyc_router, prefix=settings.API_V1_STR)
    app.include_router(kyc_router, prefix=settings.API_V1_STR)
    app.include_router(account_management_router, prefix=settings.API_V1_STR)
    app.include_router(trading_router, prefix=settings.API_V1_STR)
    # ✅ FIXED: Include the PIN router
    app.include_router(pin_router, prefix=settings.API_V1_STR)

    # Custom OpenAPI
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=settings.PROJECT_NAME,
            version="1.0.0",
            description="API docs with Bearer token authentication",
            routes=app.routes,
        )
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
        for path in openapi_schema["paths"].values():
            for method in path.values():
                method.setdefault("security", [{"BearerAuth": []}])
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    @app.on_event("startup")
    async def startup_event():
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with engine.connect() as conn:
                    # ✅ FIXED: Use text() to create executable SQL
                    conn.execute(text("SELECT 1"))
                logger.info("✅ Database connection successful!")
                break
            except Exception as e:
                logger.warning(f"❌ Database connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error("💥 All database connection attempts failed!")
                    # Don't raise the exception, just log it and continue
                    # The app might still work if tables already exist
                    logger.info("🔄 Continuing startup despite database connection issues...")
                time.sleep(2)

    return app

# Create tables with retry logic
def create_tables_with_retry():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created/verified successfully!")
            break
        except Exception as e:
            logger.warning(f"❌ Table creation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.error("💥 All table creation attempts failed!")
                # Don't raise, just log and continue
                logger.info("🔄 Continuing despite table creation issues...")
            time.sleep(2)

create_tables_with_retry()

app = create_app()