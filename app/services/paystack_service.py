# backend/app/services/paystack_service.py
import requests
from app.core.config import settings

PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/{}"
HEADERS = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"} if settings.PAYSTACK_SECRET_KEY else {}

def init_paystack_payment(email: str, amount_cents: int, reference: str, callback_url: str | None = None):
    if not settings.PAYSTACK_SECRET_KEY:
        raise RuntimeError("Paystack not configured")
    payload = {"email": email, "amount": amount_cents, "reference": reference}
    if callback_url:
        payload["callback_url"] = callback_url
    resp = requests.post(PAYSTACK_INIT_URL, json=payload, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()["data"]

def verify_paystack_transaction(reference: str):
    if not settings.PAYSTACK_SECRET_KEY:
        raise RuntimeError("Paystack not configured")
    resp = requests.get(PAYSTACK_VERIFY_URL.format(reference), headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()["data"]

# ✅ Alias so deposit.py won’t break
initialize_paystack_payment = init_paystack_payment
