# tests/verify_trading_models.py
#!/usr/bin/env python3
"""
Verification script for trading models
Run with: python tests/verify_trading_models.py
"""

import os
import sys

# Add app to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

def verify_trading_models():
    """Verify trading models match the test expectations"""
    print("🔍 Verifying Trading Models...")
    
    try:
        from app.models.trading import TradingBot, Trade
        
        # Check TradingBot model
        print("📊 Checking TradingBot model...")
        bot = TradingBot()
        
        # Required fields for tests
        bot_fields = [
            'user_id', 'strategy', 'status', 'amount_cents', 'initial_amount',
            'current_balance', 'profit_loss', 'currency_pair', 'leverage'
        ]
        
        missing_bot_fields = []
        for field in bot_fields:
            if hasattr(bot, field):
                print(f"   ✅ {field}")
            else:
                print(f"   ❌ {field} - MISSING")
                missing_bot_fields.append(field)
        
        # Check Trade model  
        print("\n📊 Checking Trade model...")
        trade = Trade()
        
        trade_fields = [
            'bot_id', 'type', 'amount', 'amount_cents', 'price', 
            'currency_pair', 'profit_loss', 'profit_cents', 'timestamp'
        ]
        
        missing_trade_fields = []
        for field in trade_fields:
            if hasattr(trade, field):
                print(f"   ✅ {field}")
            else:
                print(f"   ❌ {field} - MISSING")
                missing_trade_fields.append(field)
        
        # Check relationships
        print("\n🔗 Checking relationships...")
        try:
            from app.models.user import User
            user = User()
            if hasattr(user, 'trading_bots'):
                print("   ✅ User.trading_bots relationship")
            else:
                print("   ❌ User.trading_bots relationship - MISSING")
        except Exception as e:
            print(f"   ❌ User relationship check failed: {e}")
        
        return len(missing_bot_fields) == 0 and len(missing_trade_fields) == 0
        
    except Exception as e:
        print(f"❌ Error verifying trading models: {e}")
        return False

def test_model_creation():
    """Test creating actual model instances"""
    print("\n🧪 Testing model creation...")
    
    try:
        from app.models.trading import TradingBot, Trade
        
        # Test TradingBot creation
        bot = TradingBot(
            user_id=1,
            strategy="conservative",
            amount_cents=100000,
            initial_amount=1000.0,
            current_balance=1050.0,
            status="active",
            currency_pair="BTC-USDT",
            leverage=1
        )
        print("✅ TradingBot instance created successfully")
        
        # Test Trade creation
        trade = Trade(
            bot_id=1,
            type="buy",
            amount=100.0,
            amount_cents=10000,
            price=45000.0,
            currency_pair="BTC-USDT",
            profit_loss=50.0,
            profit_cents=5000
        )
        print("✅ Trade instance created successfully")
        
        # Test properties
        print(f"✅ TradingBot.amount property: {bot.amount}")
        print(f"✅ Trade.executed_price property: {trade.executed_price}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model creation test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 EliteSolution Trading Models Verification")
    print("=" * 50)
    
    models_ok = verify_trading_models()
    creation_ok = test_model_creation()
    
    print("\n" + "=" * 50)
    if models_ok and creation_ok:
        print("🎉 All model verifications passed!")
        print("📋 You can now run the trading tests:")
        print("   python -m pytest tests/test_trading.py -v")
    else:
        print("❌ Some model verifications failed.")
        print("🔧 Please check your model definitions.")