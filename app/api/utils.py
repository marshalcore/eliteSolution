from fastapi import APIRouter
import httpx

router = APIRouter(prefix="/utils", tags=["Utils"])

@router.get("/myip")
async def get_ip():
    """
    Returns the outbound IP of your Render instance.
    Useful for whitelisting with OKX.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://httpbin.org/ip")
        return resp.json()
