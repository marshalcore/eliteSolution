from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "codeVerification"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7   # ✅ match .env

    # Email (SMTP) - dynamic ports handled in email_utils.py
    EMAIL_HOST: str
    EMAIL_HOST_USER: str
    EMAIL_HOST_PASSWORD: str
    EMAIL_FROM: str

    # Payment gateways
    PAYSTACK_SECRET_KEY: str
    FLUTTERWAVE_SECRET_KEY: str

    # OKX API
    OKX_API_KEY: str
    OKX_SECRET_KEY: str
    OKX_PASSPHRASE: str
    OKX_BASE_URL: str = "https://www.okx.com"

    # Debug mode
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
