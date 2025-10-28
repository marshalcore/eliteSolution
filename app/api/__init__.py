# app/api/__init__.py - UPDATED
from fastapi import APIRouter
from app.api import auth, webhooks, payments, pin  # ✅ ADD pin import

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(pin.router, prefix="/pin", tags=["pin"])  # ✅ ADD PIN ROUTER

__all__ = ["auth", "webhooks", "payments", "pin"]  # ✅ ADD pin to exports