import os

class Settings:
    # === DATABASE ===
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # === JWT ===
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # === EMAIL (SMTP) ===
    EMAIL_HOST: str = os.getenv("EMAIL_HOST")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST_USER: str = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD: str = os.getenv("EMAIL_HOST_PASSWORD")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM")
    EMAIL_USE_TLS: bool = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
    
    # === PAYMENT KEYS ===
    PAYSTACK_SECRET_KEY: str = os.getenv("PAYSTACK_SECRET_KEY")
    FLUTTERWAVE_SECRET_KEY: str = os.getenv("FLUTTERWAVE_SECRET_KEY", "")

    # === OKX API KEYS ===
    OKX_API_KEY: str = os.getenv("OKX_API_KEY", "")
    OKX_SECRET_KEY: str = os.getenv("OKX_SECRET_KEY", "")
    OKX_PASSPHRASE: str = os.getenv("OKX_PASSPHRASE", "")

    # === BACKEND URLS ===
    # Default to localhost, override in Render environment
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    OKX_BASE_URL: str = os.getenv("OKX_BASE_URL", "https://www.okx.com")

    # === DEBUG MODE ===
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    def validate(self):
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable is required")
        if not self.PAYSTACK_SECRET_KEY:
            raise ValueError("PAYSTACK_SECRET_KEY environment variable is required")
        if not self.FLUTTERWAVE_SECRET_KEY:
            raise ValueError("FLUTTERWAVE_SECRET_KEY environment variable is required")
        if not self.OKX_API_KEY or not self.OKX_SECRET_KEY or not self.OKX_PASSPHRASE:
            raise ValueError("OKX_API_KEY, OKX_SECRET_KEY and OKX_PASSPHRASE are required for OKX payments")
        if not self.EMAIL_HOST or not self.EMAIL_PORT or not self.EMAIL_HOST_USER or not self.EMAIL_HOST_PASSWORD:
            raise ValueError("SMTP Email configuration (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD) is required")
        if not self.EMAIL_FROM:
            raise ValueError("EMAIL_FROM environment variable is required for sending emails")


settings = Settings()
settings.validate()
