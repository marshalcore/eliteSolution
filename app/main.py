from fastapi import FastAPI
from datetime import datetime
import os

app = FastAPI(
    title="EliteSolution Financial API",
    description="Enterprise-grade financial solution",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {
        "message": "EliteSolution Financial API", 
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "elitesolution-api",
        "version": "1.0.0"
    }

# Include your existing routers if they exist
try:
    from app.api import auth, accounts, admin, kyc, transactions, deposit, payments
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["Accounts"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(kyc.router, prefix="/api/v1/kyc", tags=["KYC"])
    app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
    app.include_router(deposit.router, prefix="/api/v1/deposit", tags=["Deposit"])
    app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
except ImportError as e:
    print(f"Some modules not available: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
