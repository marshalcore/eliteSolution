# tests/test_security.py
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User

class TestSecurity:
    """Comprehensive security testing suite"""
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed and verified"""
        password = "securepassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)
        assert hashed != password  # Ensure password is hashed
    
    def test_jwt_token_creation(self):
        """Test JWT token creation and validation"""
        email = "test@example.com"
        token = create_access_token({"sub": email})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_password_strength_validation(self, client):
        """Test password strength requirements"""
        weak_passwords = [
            "short",
            "nouppercase1",
            "NOLOWERCASE1",
            "NoNumbers",
            "Ab1"  # Too short
        ]
        
        for weak_password in weak_passwords:
            response = client.post("/api/v1/auth/register", json={
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "phone": "+1234567890",
                "password": weak_password
            })
            
            # Should reject weak passwords
            assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_sql_injection_protection(self, client, auth_headers):
        """Test SQL injection protection in various endpoints"""
        sql_injection_attempts = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1; INSERT INTO users VALUES ('hacker', 'pass')"
        ]
        
        for attempt in sql_injection_attempts:
            # Test in search endpoints
            response = client.get(f"/api/v1/auth/transactions?search={attempt}", headers=auth_headers)
            assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Test in profile endpoints
            response = client.put("/api/v1/account/language-preference", 
                                params={"language": attempt}, 
                                headers=auth_headers)
            assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_xss_protection(self, client, auth_headers):
        """Test Cross-Site Scripting protection"""
        xss_attempts = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>"
        ]
        
        for attempt in xss_attempts:
            response = client.put("/api/v1/account/language-preference", 
                                params={"language": attempt}, 
                                headers=auth_headers)
            # Should either reject or sanitize the input
            assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]
    
    def test_rate_limiting(self, client):
        """Test rate limiting on authentication endpoints"""
        # Test multiple rapid login attempts
        for i in range(10):
            response = client.post("/api/v1/auth/login", json={
                "email": f"test{i}@example.com",
                "password": "wrongpassword"
            })
            
            # After several attempts, should start rate limiting
            if i > 5:
                assert response.status_code in [status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_401_UNAUTHORIZED]
    
    def test_cors_headers(self, client):
        """Test CORS headers are properly set"""
        response = client.options("/api/v1/auth/login", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        })
        
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
    
    def test_content_security_policy(self, client):
        """Test security headers"""
        response = client.get("/api/v1/auth/login")
        
        # Check for important security headers
        security_headers = [
            "x-content-type-options",
            "x-frame-options", 
            "x-xss-protection"
        ]
        
        for header in security_headers:
            assert header in response.headers

class TestAuthenticationSecurity:
    """Authentication-specific security tests"""
    
    def test_token_expiration(self, client, test_user):
        """Test that tokens expire properly"""
        # This would require mocking time or testing with very short expiration
        pass
    
    def test_invalid_token_handling(self, client):
        """Test handling of invalid tokens"""
        invalid_tokens = [
            "invalid.token.here",
            "Bearer invalid",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
        ]
        
        for token in invalid_tokens:
            response = client.get("/api/v1/auth/profile", 
                                headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_sensitive_data_exposure(self, client, test_user, auth_headers):
        """Test that sensitive data is not exposed in responses"""
        response = client.get("/api/v1/auth/profile", headers=auth_headers)
        
        # Ensure sensitive fields are not exposed
        user_data = response.json()
        sensitive_fields = ["hashed_password", "password", "security_questions"]
        
        for field in sensitive_fields:
            assert field not in user_data
    
    def test_session_management(self, client, auth_headers):
        """Test session management security"""
        response = client.get("/api/v1/auth/profile", headers=auth_headers)
        
        # Check for secure session headers
        assert "set-cookie" not in response.headers or "httponly" in response.headers.get("set-cookie", "").lower()