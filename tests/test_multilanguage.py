# tests/test_multilanguage.py
import pytest
from fastapi import status
from fastapi.testclient import TestClient

class TestMultiLanguage:
    """Multi-language system testing"""
    
    def test_language_detection_header(self, client):
        """Test language detection from Accept-Language header"""
        headers = {"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
        response = client.get("/api/v1/auth/login", headers=headers)
        
        # Should detect Spanish from header
        assert response.headers.get("content-language") == "es"
    
    def test_language_query_parameter(self, client):
        """Test language override via query parameter"""
        response = client.get("/api/v1/auth/login?lang=fr")
        assert response.headers.get("content-language") == "fr"
    
    def test_unsupported_language_fallback(self, client):
        """Test fallback for unsupported languages"""
        response = client.get("/api/v1/auth/login?lang=xx")
        assert response.headers.get("content-language") == "en"  # Fallback to English
    
    def test_user_language_preference(self, client, test_user, auth_headers):
        """Test user language preference persistence"""
        # Set user language preference
        response = client.put("/api/v1/account/language-preference", 
                            params={"language": "de"}, 
                            headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        
        # Verify preference is used in subsequent requests
        response = client.get("/api/v1/auth/profile", headers=auth_headers)
        assert response.headers.get("content-language") == "de"
    
    def test_language_consistency(self, client, auth_headers):
        """Test language consistency across endpoints"""
        languages = ["en", "es", "fr", "de"]
        
        for lang in languages:
            # Set language
            client.put("/api/v1/account/language-preference", 
                      params={"language": lang}, 
                      headers=auth_headers)
            
            # Check multiple endpoints
            endpoints = [
                "/api/v1/auth/profile",
                "/api/v1/auth/dashboard",
                "/api/v1/trading/bots"
            ]
            
            for endpoint in endpoints:
                response = client.get(endpoint, headers=auth_headers)
                assert response.headers.get("content-language") == lang