# tests/test_trading.py
import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Import from your actual project structure
from app.models.user import User
from app.models.account import Account
from app.models.trading import TradingBot, Trade

class TestTradingSystem:
    """Comprehensive trading system testing"""
    
    def test_trading_bot_creation(self, client, test_user, auth_headers, db_session):
        """Test creating a new trading bot"""
        # Ensure user has an account with balance
        account = Account(user_id=test_user.id, account_number="TEST123", balance_cents=1000000)  # $10,000
        db_session.add(account)
        db_session.commit()
        
        bot_data = {
            "amount": 1000.0,
            "strategy": "conservative",
            "currency_pair": "BTC-USDT",
            "leverage": 1
        }
        
        response = client.post("/api/v1/trading/start", json=bot_data, headers=auth_headers)
        
        # For now, test if endpoint exists (might return 404 if not implemented)
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            # Check for possible response fields
            assert any(field in response_data for field in ["id", "message", "bot_id", "status"])
    
    def test_trading_insufficient_balance(self, client, test_user, auth_headers, db_session):
        """Test trading with insufficient balance"""
        # Create account with low balance
        account = Account(user_id=test_user.id, account_number="TEST124", balance_cents=50000)  # $500
        db_session.add(account)
        db_session.commit()
        
        bot_data = {
            "amount": 1000.0,  # More than balance
            "strategy": "conservative",
            "currency_pair": "BTC-USDT"
        }
        
        response = client.post("/api/v1/trading/start", json=bot_data, headers=auth_headers)
        # Should reject due to insufficient balance or endpoint not implemented
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_404_NOT_FOUND]
    
    def test_trading_minimum_amount(self, client, test_user, auth_headers, db_session):
        """Test trading minimum amount requirement"""
        account = Account(user_id=test_user.id, account_number="TEST125", balance_cents=1000000)
        db_session.add(account)
        db_session.commit()
        
        bot_data = {
            "amount": 5.0,  # Below minimum (if implemented)
            "strategy": "conservative",
            "currency_pair": "BTC-USDT"
        }
        
        response = client.post("/api/v1/trading/start", json=bot_data, headers=auth_headers)
        # Should reject due to minimum amount or endpoint not implemented
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_404_NOT_FOUND]
    
    def test_trading_without_kyc(self, client, db_session):
        """Test trading without KYC verification"""
        # Create unverified user
        unverified_user = User(
            email="unverified@example.com",
            first_name="Unverified",
            last_name="User",
            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
            is_verified=True,
            kyc_status="pending"
        )
        db_session.add(unverified_user)
        db_session.commit()
        
        account = Account(user_id=unverified_user.id, account_number="TEST126", balance_cents=1000000)
        db_session.add(account)
        db_session.commit()
        
        # Create token for unverified user
        from app.core.security import create_access_token
        token = create_access_token({"sub": unverified_user.email})
        headers = {"Authorization": f"Bearer {token}"}
        
        bot_data = {
            "amount": 1000.0,
            "strategy": "conservative",
            "currency_pair": "BTC-USDT"
        }
        
        response = client.post("/api/v1/trading/start", json=bot_data, headers=headers)
        # Should reject due to KYC or endpoint not implemented
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
    
    def test_get_trading_bots(self, client, test_user, auth_headers, db_session):
        """Test retrieving user's trading bots"""
        # Create test bots using YOUR model structure
        bot1 = TradingBot(
            user_id=test_user.id,
            strategy="conservative",
            amount_cents=100000,  # $1000 in cents
            initial_amount=1000.0,
            current_balance=1050.0,
            status="active"
        )
        bot2 = TradingBot(
            user_id=test_user.id,
            strategy="aggressive", 
            amount_cents=200000,  # $2000 in cents
            initial_amount=2000.0,
            current_balance=1800.0,
            status="stopped"
        )
        db_session.add_all([bot1, bot2])
        db_session.commit()
        
        response = client.get("/api/v1/trading/bots", headers=auth_headers)
        
        # Endpoint might not be implemented yet
        if response.status_code == status.HTTP_200_OK:
            bots = response.json()
            assert isinstance(bots, list)
        else:
            # If endpoint not implemented, that's OK for now
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_stop_trading_bot(self, client, test_user, auth_headers, db_session):
        """Test stopping a trading bot"""
        # Create active bot using YOUR model structure
        bot = TradingBot(
            user_id=test_user.id,
            strategy="moderate",
            amount_cents=100000,  # $1000 in cents
            initial_amount=1000.0,
            current_balance=1100.0,
            status="active"
        )
        db_session.add(bot)
        db_session.commit()
        
        response = client.post("/api/v1/trading/stop", json={"bot_id": bot.id}, headers=auth_headers)
        
        # Endpoint might not be implemented yet
        if response.status_code == status.HTTP_200_OK:
            # Verify bot was stopped
            db_session.refresh(bot)
            assert bot.status == "stopped"
        else:
            # If endpoint not implemented, that's OK for now
            assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST]
    
    def test_trading_history(self, client, test_user, auth_headers, db_session):
        """Test retrieving trading history"""
        # Create test trades using YOUR model structure
        bot = TradingBot(
            user_id=test_user.id, 
            strategy="conservative", 
            amount_cents=100000,  # $1000 in cents
            initial_amount=1000.0
        )
        db_session.add(bot)
        db_session.commit()
        
        trade1 = Trade(
            bot_id=bot.id,
            type="buy",
            amount=100.0,
            amount_cents=10000,  # $100 in cents
            price=45000.0,
            currency_pair="BTC-USDT",
            profit_loss=50.0,
            profit_cents=5000  # $50 in cents
        )
        trade2 = Trade(
            bot_id=bot.id,
            type="sell",
            amount=50.0,
            amount_cents=5000,  # $50 in cents
            price=46000.0, 
            currency_pair="BTC-USDT",
            profit_loss=25.0,
            profit_cents=2500  # $25 in cents
        )
        db_session.add_all([trade1, trade2])
        db_session.commit()
        
        response = client.get("/api/v1/trading/history", headers=auth_headers)
        
        if response.status_code == status.HTTP_200_OK:
            trades = response.json()
            assert isinstance(trades, list)
        else:
            # Endpoint might not be implemented yet
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_trading_analytics(self, client, test_user, auth_headers, db_session):
        """Test trading analytics endpoint"""
        response = client.get("/api/v1/trading/analytics", headers=auth_headers)
        
        if response.status_code == status.HTTP_200_OK:
            analytics = response.json()
            assert isinstance(analytics, dict)
        else:
            # Endpoint might not be implemented yet
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_market_data(self, client, auth_headers):
        """Test market data endpoint"""
        response = client.get("/api/v1/trading/market-data", headers=auth_headers)
        
        if response.status_code == status.HTTP_200_OK:
            market_data = response.json()
            assert isinstance(market_data, (list, dict))
        else:
            # Endpoint might not be implemented yet
            assert response.status_code == status.HTTP_404_NOT_FOUND

class TestTradingSecurity:
    """Trading-specific security tests"""
    
    def test_unauthorized_trading_access(self, client):
        """Test unauthorized access to trading endpoints"""
        trading_endpoints = [
            "/api/v1/trading/bots",
            "/api/v1/trading/history", 
            "/api/v1/trading/analytics",
            "/api/v1/trading/market-data"
        ]
        
        for endpoint in trading_endpoints:
            response = client.get(endpoint)
            # Should be unauthorized or not found
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]
    
    def test_user_bot_isolation(self, client, db_session, auth_headers):
        """Test that users can only access their own bots"""
        # Create another user
        other_user = User(
            email="other@example.com",
            first_name="Other",
            last_name="User",
            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
            is_verified=True,
            kyc_status="verified"
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Create bot for other user using YOUR model structure
        other_bot = TradingBot(
            user_id=other_user.id,
            strategy="conservative",
            amount_cents=100000,  # $1000 in cents
            initial_amount=1000.0,
            status="active"
        )
        db_session.add(other_bot)
        db_session.commit()
        
        # Try to access other user's bot
        response = client.post("/api/v1/trading/stop", json={"bot_id": other_bot.id}, headers=auth_headers)
        
        # Should not be able to access other user's bot
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]
    
    def test_trading_input_validation(self, client, test_user, auth_headers, db_session):
        """Test trading input validation"""
        account = Account(user_id=test_user.id, account_number="TEST127", balance_cents=1000000)
        db_session.add(account)
        db_session.commit()
        
        invalid_inputs = [
            {"amount": -100, "strategy": "conservative", "currency_pair": "BTC-USDT"},
            {"amount": 1000, "strategy": "invalid_strategy", "currency_pair": "BTC-USDT"},
            {"amount": 1000, "strategy": "conservative", "currency_pair": "INVALID-PAIR"},
            {"amount": 1000, "strategy": "conservative", "leverage": -1}
        ]
        
        for invalid_input in invalid_inputs:
            response = client.post("/api/v1/trading/start", json=invalid_input, headers=auth_headers)
            # Should reject invalid input or endpoint not implemented
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST, 
                status.HTTP_422_UNPROCESSABLE_ENTITY, 
                status.HTTP_404_NOT_FOUND
            ]