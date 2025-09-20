# main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.db import Base, engine
from app.api import auth, admin, accounts, transactions, deposit, otp, webhooks
from app.api import utils
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # Routers
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(accounts.router)
    app.include_router(transactions.router)
    app.include_router(deposit.router)
    app.include_router(otp.router)
    app.include_router(webhooks.router)
    app.include_router(utils.router)

    # ✅ Custom OpenAPI for JWT Bearer
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
        # Apply security globally
        for path in openapi_schema["paths"].values():
            for method in path.values():
                method.setdefault("security", [{"BearerAuth": []}])
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app


# ✅ Create DB tables if not existing
Base.metadata.create_all(bind=engine)
app = create_app()
