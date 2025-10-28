# app/core/config.py - FIXED
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "eliteSolution"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OTP Settings
    OTP_EXPIRY_MINUTES: int = 10
    OTP_LENGTH: int = 6
    MAX_OTP_DAILY: int = 10

    # ✅ FIXED: Email Configuration - Match email_service.py expectations
    SMTP_HOST: str  # Changed from EMAIL_HOST to SMTP_HOST
    SMTP_PORT: int = 587  # Default port
    SMTP_USER: str  # Changed from EMAIL_HOST_USER
    SMTP_PASSWORD: str  # Changed from EMAIL_HOST_PASSWORD
    FROM_EMAIL: str  # Changed from EMAIL_FROM

    # Payment gateways
    PAYSTACK_SECRET_KEY: str
    FLUTTERWAVE_SECRET_KEY: str

    # OKX API
    OKX_API_KEY: str
    OKX_SECRET_KEY: str
    OKX_PASSPHRASE: str
    OKX_BASE_URL: str = "https://www.okx.com"

    # Marqeta Configuration
    MARQETA_BASE_URL: str = "https://sandbox-api.marqeta.com/v3"
    MARQETA_APPLICATION_TOKEN: str
    MARQETA_MASTER_ACCESS_TOKEN: str

    # Currency & Internationalization with Crypto
    DEFAULT_CURRENCY: str = "USD"
    SUPPORTED_CURRENCIES: list = [
        "USD", "EUR", "GBP", "NGN", "CAD", "AUD",
        "CNY", "JPY", "THB", "BTC", "ETH", "USDT",
    ]
    
    # Trading Configuration
    TRADING_MIN_AMOUNT: float = 10.00
    TRADING_PROFIT_RATES: dict = {
        "conservative": 0.02,
        "moderate": 0.05,  
        "aggressive": 0.08
    }

    # Backend URL
    BACKEND_URL: str = "http://127.0.0.1:8000"

    # CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000", 
        "http://localhost:3001",
        "http://10.91.94.97:3001",
        "https://elitesolution.onrender.com",
    ]

    # Debug mode
    DEBUG: bool = True

    class Config:
        env_file = ".env"

settings = Settings()