# tests/test_integration.py
import pytest
from fastapi import status
from fastapi.testclient import TestClient

class TestIntegration:
    """End-to-end integration testing"""
    
    def test_complete_user_journey(self, client, db_session):
        """Test complete user journey from registration to trading"""
        # 1. Register new user
        user_data = {
            "email": "journey@example.com",
            "first_name": "Journey",
            "last_name": "User",
            "phone": "+1234567890",
            "password": "SecurePassword123!"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == status.HTTP_200_OK
        
        # 2. Login (would need OTP verification in real scenario)
        # Skip OTP for test - directly create verified user
        from app.core.security import create_access_token
        token = create_access_token({"sub": user_data["email"]})
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Create account with balance
        from app.models.user import User
        from app.models.account import Account
        
        user = db_session.query(User).filter(User.email == user_data["email"]).first()
        user.is_verified = True
        user.kyc_status = "verified"
        
        account = Account(user_id=user.id, account_number="JOURNEY123", balance_cents=1000000)
        db_session.add(account)
        db_session.commit()
        
        # 4. Access profile
        response = client.get("/api/v1/auth/profile", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        # 5. Create trading bot
        bot_data = {
            "amount": 500.0,
            "strategy": "conservative",
            "currency_pair": "BTC-USDT"
        }
        
        response = client.post("/api/v1/trading/start", json=bot_data, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        # 6. Check trading bots
        response = client.get("/api/v1/trading/bots", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
        
        # 7. Check trading history
        response = client.get("/api/v1/trading/history", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        # 8. Update account settings
        response = client.put("/api/v1/account/language-preference", 
                            params={"language": "es"}, 
                            headers=headers)
        assert response.status_code == status.HTTP_200_OK
    
    def test_error_handling(self, client, auth_headers):
        """Test comprehensive error handling"""
        # Test various error scenarios
        invalid_endpoints = [
            "/api/v1/nonexistent",
            "/api/v1/auth/invalid",
            "/api/v1/trading/invalid-endpoint"
        ]
        
        for endpoint in invalid_endpoints:
            response = client.get(endpoint, headers=auth_headers)
            assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Test malformed requests
        malformed_requests = [
            ("/api/v1/auth/login", "invalid json"),
            ("/api/v1/trading/start", '{"invalid": json}'),
        ]
        
        for endpoint, data in malformed_requests:
            response = client.post(endpoint, data=data, headers=auth_headers)
            assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]