import httpx
from app.core.config import settings

async def initialize_flutterwave_payment(email: str, amount: float, currency: str = "NGN") -> dict:
    """
    Initialize a Flutterwave transaction.
    """
    url = "https://api.flutterwave.com/v3/payments"
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "tx_ref": f"txn-{email}",
        "amount": str(amount),
        "currency": currency,
        "redirect_url": "https://yourbankapp.com/payment/callback",
        "customer": {"email": email},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise ValueError(f"Flutterwave init failed: {response.text}")

    return response.json()
