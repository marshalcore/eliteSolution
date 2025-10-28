# tests/test_account_management.py
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.models.user import User

class TestAccountManagement:
    """Account management system testing"""
    
    def test_change_password(self, client, test_user, auth_headers):
        """Test password change functionality"""
        password_data = {
            "current_password": "password",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!"
        }
        
        response = client.put("/api/v1/account/change-password", json=password_data, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
    
    def test_change_password_wrong_current(self, client, test_user, auth_headers):
        """Test password change with wrong current password"""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!"
        }
        
        response = client.put("/api/v1/account/change-password", json=password_data, headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_change_password_mismatch(self, client, test_user, auth_headers):
        """Test password change with mismatched new passwords"""
        password_data = {
            "current_password": "password",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "DifferentPassword123!"
        }
        
        response = client.put("/api/v1/account/change-password", json=password_data, headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_change_email(self, client, test_user, auth_headers):
        """Test email change request"""
        email_data = {
            "new_email": "newemail@example.com",
            "password": "password"
        }
        
        response = client.post("/api/v1/account/change-email", json=email_data, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
    
    def test_change_phone(self, client, test_user, auth_headers):
        """Test phone change request"""
        phone_data = {
            "new_phone": "+1987654321",
            "password": "password"
        }
        
        response = client.post("/api/v1/account/change-phone", json=phone_data, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
    
    def test_language_preference_update(self, client, auth_headers):
        """Test language preference update"""
        response = client.put("/api/v1/account/language-preference", 
                            params={"language": "es"}, 
                            headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
    
    def test_invalid_language_preference(self, client, auth_headers):
        """Test invalid language preference"""
        response = client.put("/api/v1/account/language-preference", 
                            params={"language": "invalid_lang"}, 
                            headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_two_factor_toggle(self, client, auth_headers):
        """Test two-factor authentication toggle"""
        response = client.put("/api/v1/account/toggle-two-factor", 
                            params={"enable": True}, 
                            headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
    
    def test_account_status(self, client, auth_headers):
        """Test account status retrieval"""
        response = client.get("/api/v1/account/status", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        
        status_data = response.json()
        expected_fields = [
            "email_verified", "phone_verified", "kyc_status",
            "two_factor_enabled", "language_preference"
        ]
        
        for field in expected_fields:
            assert field in status_data
    
    def test_security_settings(self, client, auth_headers):
        """Test security settings retrieval"""
        response = client.get("/api/v1/account/security-settings", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        
        settings = response.json()
        expected_fields = [
            "two_factor_enabled", "login_alerts", "security_questions_set"
        ]
        
        for field in expected_fields:
            assert field in settings