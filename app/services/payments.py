import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.core.config import settings
from app.models import User, Account, Transaction


# -------------------------------
# Paystack Verification
# -------------------------------
async def verify_paystack_payment(reference: str, amount: float, user_id: int, db: Session):
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Paystack verification failed")

    data = resp.json()
    if data.get("data", {}).get("status") != "success":
        raise HTTPException(status_code=400, detail="Transaction not successful")

    return credit_account(user_id, amount, "paystack", db)


# -------------------------------
# Flutterwave Verification
# -------------------------------
async def verify_flutterwave_payment(reference: str, amount: float, user_id: int, db: Session):
    url = f"https://api.flutterwave.com/v3/transactions/{reference}/verify"
    headers = {"Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Flutterwave verification failed")

    data = resp.json()
    if data.get("status") != "success" or data.get("data", {}).get("status") != "successful":
        raise HTTPException(status_code=400, detail="Transaction not successful")

    return credit_account(user_id, amount, "flutterwave", db)


# -------------------------------
# OKX Deposit Handler
# -------------------------------
async def verify_okx_payment(tx_id: str, amount: float, user_id: int, db: Session):
    """
    Verifies an OKX deposit transaction by transaction ID.
    """
    url = f"https://www.okx.com/api/v5/asset/deposit-history?txId={tx_id}"
    headers = {"OK-ACCESS-KEY": settings.OKX_API_KEY, "OK-ACCESS-SIGN": settings.OKX_SECRET_KEY}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="OKX verification failed")

    data = resp.json()
    if not data.get("data"):
        raise HTTPException(status_code=400, detail="Transaction not found")

    return credit_account(user_id, amount, "okx", db)


# -------------------------------
# Shared Account Crediting
# -------------------------------
def credit_account(user_id: int, amount: float, gateway: str, db: Session):
    account = db.query(Account).filter(Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Update balance
    account.balance += amount

    # Record transaction
    txn = Transaction(
        user_id=user_id,
        amount=amount,
        type="deposit",
        gateway=gateway,
        status="success"
    )
    db.add(txn)
    db.commit()
    db.refresh(account)

    return {
        "message": f"Deposit of {amount} via {gateway} successful",
        "new_balance": account.balance
    }
