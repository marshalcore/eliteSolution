# app/services/currency_service.py - UPDATED (No API Key Needed)
import httpx
from app.core.config import settings

class CurrencyService:
    def __init__(self):
        # No API key needed for free tier
        self.fiat_url = "https://api.exchangerate-api.com/v4/latest/USD"
        self.crypto_url = "https://api.coingecko.com/api/v3/simple/price"
    
    async def get_exchange_rates(self):
        """Get current exchange rates including cryptocurrencies"""
        try:
            # Get fiat rates - FREE API, no key needed
            async with httpx.AsyncClient() as client:
                fiat_response = await client.get(self.fiat_url)
                fiat_data = fiat_response.json()
                fiat_rates = fiat_data['rates']
            
            # Get crypto rates from CoinGecko (free, no key needed for low usage)
            crypto_ids = "bitcoin,ethereum,tether"
            async with httpx.AsyncClient() as client:
                crypto_response = await client.get(
                    f"{self.crypto_url}?ids={crypto_ids}&vs_currencies=usd"
                )
                crypto_data = crypto_response.json()
            
            # Combine rates
            combined_rates = {
                **fiat_rates,
                # Convert crypto to USD rates (1 BTC = X USD)
                "BTC": crypto_data['bitcoin']['usd'],
                "ETH": crypto_data['ethereum']['usd'], 
                "USDT": crypto_data['tether']['usd']
            }
            
            return combined_rates
            
        except Exception as e:
            print(f"API fetch failed, using fallback rates: {e}")
            # Fallback rates if API fails
            return self.get_fallback_rates()
    
    def get_fallback_rates(self):
        """Fallback rates when API is unavailable"""
        return {
            # Fiat Currencies
            "USD": 1.0,
            "EUR": 0.85,
            "GBP": 0.73,
            "NGN": 410.0,
            "CAD": 1.25,
            "AUD": 1.35,
            # Asian Currencies
            "CNY": 6.45,    # Chinese Yuan
            "JPY": 110.0,   # Japanese Yen
            "THB": 33.0,    # Thailand Baht
            # Cryptocurrencies (approximate rates)
            "BTC": 45000.0, # Bitcoin
            "ETH": 3000.0,  # Ethereum  
            "USDT": 1.0,    # Tether
        }
    
    
    async def convert_amount(self, amount: float, from_currency: str, to_currency: str):
        """Convert amount between currencies including crypto"""
        rates = await self.get_exchange_rates()
        
        # Convert to USD first, then to target currency
        amount_in_usd = amount / rates[from_currency]
        converted_amount = amount_in_usd * rates[to_currency]
        
        # For crypto, limit decimal places
        if to_currency in ["BTC", "ETH"]:
            return round(converted_amount, 8)  # More decimals for crypto
        elif to_currency in ["USDT"]:
            return round(converted_amount, 2)  # Stablecoin
        else:
            return round(converted_amount, 2)  # Fiat currencies
    
    async def get_supported_currencies(self):
        """Get list of supported currencies"""
        return settings.SUPPORTED_CURRENCIES
    
    async def get_currency_info(self, currency_code: str):
        """Get information about a specific currency"""
        currency_info = {
            "USD": {"name": "US Dollar", "symbol": "$", "type": "fiat"},
            "EUR": {"name": "Euro", "symbol": "€", "type": "fiat"},
            "GBP": {"name": "British Pound", "symbol": "£", "type": "fiat"},
            "NGN": {"name": "Nigerian Naira", "symbol": "₦", "type": "fiat"},
            "CAD": {"name": "Canadian Dollar", "symbol": "C$", "type": "fiat"},
            "AUD": {"name": "Australian Dollar", "symbol": "A$", "type": "fiat"},
            # ✅ NEW: Asian Currencies
            "CNY": {"name": "Chinese Yuan", "symbol": "¥", "type": "fiat"},
            "JPY": {"name": "Japanese Yen", "symbol": "¥", "type": "fiat"},
            "THB": {"name": "Thai Baht", "symbol": "฿", "type": "fiat"},
            # ✅ NEW: Cryptocurrencies
            "BTC": {"name": "Bitcoin", "symbol": "₿", "type": "crypto"},
            "ETH": {"name": "Ethereum", "symbol": "Ξ", "type": "crypto"},
            "USDT": {"name": "Tether", "symbol": "₮", "type": "crypto"},
        }
        
        return currency_info.get(currency_code, {"name": currency_code, "symbol": currency_code, "type": "unknown"})