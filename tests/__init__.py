# tests/__init__.py
import os
import sys
import asyncio
import pytest

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

# Test configuration
TEST_CONFIG = {
    "database_url": "sqlite:///./test.db",
    "test_timeout": 30,
    "max_retries": 3
}