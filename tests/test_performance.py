# tests/test_performance.py
import pytest
import time
from fastapi import status
from fastapi.testclient import TestClient

class TestPerformance:
    """Performance and load testing"""
    
    def test_response_times(self, client, auth_headers):
        """Test response times for critical endpoints"""
        endpoints = [
            "/api/v1/auth/profile",
            "/api/v1/auth/dashboard", 
            "/api/v1/trading/bots",
            "/api/v1/trading/market-data"
        ]
        
        max_response_time = 2.0  # 2 seconds maximum
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint, headers=auth_headers)
            end_time = time.time()
            
            response_time = end_time - start_time
            assert response_time < max_response_time, f"Endpoint {endpoint} took {response_time:.2f}s"
            assert response.status_code == status.HTTP_200_OK
    
    def test_concurrent_requests(self, client, auth_headers):
        """Test handling of concurrent requests"""
        import threading
        
        results = []
        errors = []
        
        def make_request():
            try:
                response = client.get("/api/v1/auth/profile", headers=auth_headers)
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests were successful
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert all(status_code == status.HTTP_200_OK for status_code in results)
    
    def test_database_performance(self, client, auth_headers, db_session):
        """Test database query performance"""
        import time
        
        # Test trading bots query performance
        start_time = time.time()
        response = client.get("/api/v1/trading/bots", headers=auth_headers)
        end_time = time.time()
        
        query_time = end_time - start_time
        assert query_time < 1.0, f"Trading bots query took {query_time:.2f}s"
        assert response.status_code == status.HTTP_200_OK
    
    def test_memory_usage(self, client, auth_headers):
        """Test memory usage under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make multiple requests
        for i in range(50):
            client.get("/api/v1/auth/profile", headers=auth_headers)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB"