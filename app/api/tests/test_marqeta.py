# test_marqeta.py - UPDATED (place in project root)
import asyncio
import os
import sys

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_marqeta():
    """Test Marqeta connection and basic operations"""
    print("🔍 Testing Marqeta integration...")
    
    try:
        from app.services.marqeta_service import MarqetaService
        marqeta = MarqetaService()
        
        # Test 1: API Connection
        print("1. Testing API connection...")
        connected = await marqeta.test_connection()
        if connected:
            print("✅ Marqeta API connection successful!")
        else:
            print("❌ Marqeta API connection failed!")
            return False
        
        # Test 2: Card Products
        print("2. Testing card products...")
        try:
            card_product_token = await marqeta.get_card_products()
            print(f"✅ Card products available. Token: {card_product_token}")
        except Exception as e:
            print(f"❌ Card products test failed: {e}")
            return False
        
        # Test 3: User Creation
        print("3. Testing user creation...")
        try:
            test_user = {
                "user_id": 999,
                "first_name": "Test",
                "last_name": "User", 
                "email": "test@example.com"
            }
            user = await marqeta.create_user(test_user)
            print(f"✅ User created successfully. Token: {user['token']}")
            
            # Test 4: Virtual Card Creation
            print("4. Testing virtual card creation...")
            card_data = {
                "user_id": 999,
                "first_name": "Test",
                "last_name": "User"
            }
            card = await marqeta.create_virtual_card(user['token'], card_data)
            print(f"✅ Virtual card created successfully. Token: {card['token']}")
            
            print(f"\n🎉 All Marqeta tests passed!")
            print(f"📊 Test User Token: {user['token']}")
            print(f"💳 Test Card Token: {card['token']}")
            
            return True
            
        except Exception as e:
            print(f"❌ User/card creation failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_currencies():
    """Test currency service with new currencies"""
    print("\n🔍 Testing Currency Service...")
    
    try:
        from app.services.currency_service import CurrencyService
        currency_service = CurrencyService()
        
        # Test exchange rates
        rates = await currency_service.get_exchange_rates()
        print("✅ Exchange rates fetched successfully")
        
        # Test conversion
        test_conversions = [
            (100, "USD", "BTC"),
            (100, "USD", "ETH"), 
            (1000, "CNY", "USD"),
            (5000, "JPY", "EUR")
        ]
        
        for amount, from_curr, to_curr in test_conversions:
            try:
                converted = await currency_service.convert_amount(amount, from_curr, to_curr)
                print(f"✅ {amount} {from_curr} → {converted} {to_curr}")
            except Exception as e:
                print(f"❌ Conversion failed for {from_curr}→{to_curr}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Currency test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting EliteSolution Integration Tests...\n")
    
    async def run_all_tests():
        marqeta_ok = await test_marqeta()
        currency_ok = await test_currencies()
        
        print(f"\n📊 Test Results:")
        print(f"Marqeta: {'✅ PASS' if marqeta_ok else '❌ FAIL'}")
        print(f"Currency: {'✅ PASS' if currency_ok else '❌ FAIL'}")
        
        if marqeta_ok and currency_ok:
            print("\n🎉 ALL TESTS PASSED! Your integration is ready.")
        else:
            print("\n⚠️ Some tests failed. Please check the configuration.")
    
    asyncio.run(run_all_tests())