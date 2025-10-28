# app/services/marqeta_service.py - UPDATED
import httpx
import json
from app.core.config import settings

class MarqetaService:
    def __init__(self):
        self.base_url = settings.MARQETA_BASE_URL.rstrip('/')  # Remove trailing slash
        self.app_token = settings.MARQETA_APPLICATION_TOKEN
        self.access_token = settings.MARQETA_MASTER_ACCESS_TOKEN
        
    async def create_user(self, user_data: dict):
        """Create user in Marqeta system"""
        url = f"{self.base_url}/users"
        payload = {
            "token": f"user_{user_data['user_id']}",
            "first_name": user_data['first_name'],
            "last_name": user_data['last_name'],
            "email": user_data['email'],
            "active": True
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                auth=(self.app_token, self.access_token)
            )
            if response.status_code != 201:
                raise Exception(f"Marqeta user creation failed: {response.text}")
            return response.json()
    
    async def get_card_products(self):
        """Get available card products to find program token"""
        url = f"{self.base_url}/cardproducts"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                auth=(self.app_token, self.access_token)
            )
            if response.status_code != 200:
                raise Exception(f"Failed to get card products: {response.text}")
            data = response.json()
            
            # Return the first card product token
            if data.get('data') and len(data['data']) > 0:
                return data['data'][0]['token']
            else:
                raise Exception("No card products available in Marqeta")
    
    async def create_virtual_card(self, user_token: str, card_data: dict):
        """Create virtual card for user"""
        # First, get a card product token
        card_product_token = await self.get_card_products()
        
        url = f"{self.base_url}/cards"
        payload = {
            "user_token": user_token,
            "card_product_token": card_product_token,
            "fulfillment": {
                "shipping": {
                    "first_name": card_data['first_name'],
                    "last_name": card_data['last_name']
                }
            },
            "metadata": {
                "internal_user_id": card_data['user_id']
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                auth=(self.app_token, self.access_token)
            )
            if response.status_code != 201:
                raise Exception(f"Marqeta card creation failed: {response.text}")
            return response.json()
    
    async def get_card_balance(self, card_token: str):
        """Get card balance"""
        url = f"{self.base_url}/cards/{card_token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                auth=(self.app_token, self.access_token)
            )
            if response.status_code != 200:
                raise Exception(f"Failed to get card balance: {response.text}")
            return response.json()
    
    async def simulate_card_funding(self, card_token: str, amount: float, currency: str = "USD"):
        """Simulate funding card (for testing - replace with real funding)"""
        # In sandbox, we can simulate funding via GPA orders
        url = f"{self.base_url}/simulate/financial"
        payload = {
            "card_token": card_token,
            "amount": amount,
            "currency_code": currency,
            "state": "PENDING",
            "type": "authorization"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                auth=(self.app_token, self.access_token)
            )
            if response.status_code != 201:
                raise Exception(f"Card funding simulation failed: {response.text}")
            return response.json()

    async def test_connection(self):
        """Test Marqeta API connection"""
        url = f"{self.base_url}/ping"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                auth=(self.app_token, self.access_token)
            )
            return response.status_code == 200