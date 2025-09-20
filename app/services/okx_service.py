# app/services/okx_service.py

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
import httpx
from app.core.config import settings


def _okx_timestamp() -> str:
    """Generate ISO8601 UTC timestamp with milliseconds (preferred by OKX)."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _okx_headers(method: str, request_path: str, body: dict = None):
    """Generate OKX authentication headers."""
    timestamp = _okx_timestamp()
    body_str = json.dumps(body) if body else ""

    message = f"{timestamp}{method}{request_path}{body_str}"
    sign = hmac.new(
        settings.OKX_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    sign_b64 = base64.b64encode(sign).decode()

    return {
        "OK-ACCESS-KEY": settings.OKX_API_KEY,
        "OK-ACCESS-SIGN": sign_b64,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": settings.OKX_PASSPHRASE,
        "Content-Type": "application/json"
    }


async def create_okx_deposit_address(currency: str = "USDT"):
    """Request a deposit address from OKX."""
    endpoint = f"/api/v5/asset/deposit-address?ccy={currency}"
    url = f"{settings.OKX_BASE_URL}{endpoint}"
    headers = _okx_headers("GET", endpoint)

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            raise Exception(f"OKX deposit error: {r.text}")
        return r.json()


async def proxy_okx_request(method: str, endpoint: str, body: dict = None):
    """General proxy for OKX API requests."""
    url = f"{settings.OKX_BASE_URL}{endpoint}"
    headers = _okx_headers(method, endpoint, body)

    async with httpx.AsyncClient(timeout=10) as client:
        if method == "GET":
            r = await client.get(url, headers=headers)
        else:
            r = await client.post(url, headers=headers, json=body or {})

        if r.status_code != 200:
            raise Exception(f"OKX request error: {r.text}")
        return r.json()
