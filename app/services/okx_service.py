import hmac, base64, httpx
from datetime import datetime, timezone
from app.core.config import settings


def get_okx_timestamp() -> str:
    """Return UTC timestamp in ISO 8601 format with milliseconds (required by OKX)."""
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def okx_signature(secret_key: str, timestamp: str, method: str, request_path: str, body: str = "") -> str:
    """Generate OKX API signature."""
    message = f"{timestamp}{method}{request_path}{body}"
    print("🔑 Signing string:", message)  # Debug
    mac = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), digestmod="sha256")
    return base64.b64encode(mac.digest()).decode()


async def create_okx_deposit_address(user_id: int, amount: float, currency: str = "USDT"):
    """
    Calls OKX API to get a deposit address for a given currency.
    user_id and amount are internal only, not sent to OKX.
    """
    try:
        timestamp = get_okx_timestamp()
        method = "GET"
        request_path = f"/api/v5/asset/deposit-address?ccy={currency}"
        body = ""

        # ✅ Generate signature
        sign = okx_signature(settings.OKX_SECRET_KEY, timestamp, method, request_path, body)

        headers = {
            "OK-ACCESS-KEY": settings.OKX_API_KEY,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": settings.OKX_PASSPHRASE,
            "Content-Type": "application/json",
        }

        print("📩 Headers:", headers)  # Debug
        print("🌍 URL:", f"{settings.OKX_BASE_URL}{request_path}")  # Debug

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.OKX_BASE_URL}{request_path}",
                headers=headers,
                timeout=30
            )

            print("📤 Response status:", response.status_code)  # Debug
            print("📤 Response body:", response.text)          # Debug

            response.raise_for_status()
            return response.json()

    except Exception as e:
        raise Exception(f"OKX deposit error: {e}")
