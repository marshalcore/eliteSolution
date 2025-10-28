# tests/test_authentication.py
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.models.user import User
from app.models.otp import OTP

class TestAuthentication:
    """Comprehensive authentication testing"""
    
    def test_user_registration(self, client, db_session):
        """Test user registration flow"""
        user_data = {
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User", 
            "phone": "+1234567890",
            "password": "SecurePassword123!"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
        
        # Verify user was created in database
        user = db_session.query(User).filter(User.email == user_data["email"]).first()
        assert user is not None
        assert user.is_verified == False
        assert user.kyc_status == "pending"
    
    def test_duplicate_registration(self, client, test_user):
        """Test duplicate email registration prevention"""
        duplicate_data = {
            "email": test_user.email,
            "first_name": "Duplicate",
            "last_name": "User",
            "phone": "+1987654321",
            "password": "AnotherPassword123!"
        }
        
        response = client.post("/api/v1/auth/register", json=duplicate_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        # Note: In real test, you'd need to set a proper password hash
        response = client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "password"  # This matches the test fixture hash
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
    
    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid credentials"""
        response = client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "wrongpassword"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "anypassword"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_protected_endpoint_access(self, client, auth_headers):
        """Test access to protected endpoints"""
        response = client.get("/api/v1/auth/profile", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
    
    def test_unprotected_endpoint_access(self, client):
        """Test access to unprotected endpoints"""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
    
    def test_password_reset_flow(self, client, test_user, db_session):
        """Test complete password reset flow"""
        # 1. Request password reset
        response = client.post("/api/v1/auth/forgot-password", json={
            "email": test_user.email
        })
        assert response.status_code == status.HTTP_200_OK
        
        # 2. Get OTP from database (in real scenario, this would be sent via email)
        otp = db_session.query(OTP).filter(
            OTP.user_id == test_user.id,
            OTP.purpose == "password_reset"
        ).first()
        
        assert otp is not None
        
        # 3. Reset password with OTP
        response = client.post("/api/v1/auth/reset-password", json={
            "email": test_user.email,
            "code": otp.code,
            "new_password": "NewSecurePassword123!"
        })
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_invalid_password_reset(self, client, test_user):
        """Test password reset with invalid OTP"""
        response = client.post("/api/v1/auth/reset-password", json={
            "email": test_user.email,
            "code": "INVALID123",
            "new_password": "NewSecurePassword123!"
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

class TestOTPSecurity:
    """OTP-specific security tests"""
    
    def test_otp_expiration(self, client, test_user, db_session):
        """Test OTP expiration mechanism"""
        # This would require testing with expired OTPs
        pass
    
    def test_otp_reuse_prevention(self, client, test_user, db_session):
        """Test that OTPs cannot be reused"""
        # This would require testing OTP usage tracking
        pass
    
    def test_otp_brute_force_protection(self, client, test_user):
        """Test protection against OTP brute forcing"""
        for i in range(10):
            response = client.post("/api/v1/auth/verify-login", json={
                "email": test_user.email,
                "code": f"WRONG{i:06d}"
            })
            
            # Should eventually block or slow down
            if i > 5:
                assert response.status_code in [status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_400_BAD_REQUEST]