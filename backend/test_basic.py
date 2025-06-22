#!/usr/bin/env python3
"""
Basic tests for the procurement scanner
"""

import pytest
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from models import Base, SessionLocal, Tender, save_tender_to_db, get_db
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import models: {e}")
    
    try:
        from selenium_utils import selenium_manager
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import selenium_utils: {e}")

def test_basic_functionality():
    """Test basic functionality"""
    assert True  # Placeholder test

if __name__ == "__main__":
    pytest.main([__file__]) 