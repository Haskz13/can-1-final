#!/usr/bin/env python3
"""
Test script to verify that circular import issues are resolved
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test all module imports to ensure no circular dependencies"""
    print("Testing module imports...")
    
    try:
        # Test config module
        print("✓ Testing config module...")
        from config import PORTAL_CONFIGS, TKA_COURSES, DATABASE_URL
        print(f"  - Found {len(PORTAL_CONFIGS)} portal configurations")
        print(f"  - Found {len(TKA_COURSES)} training courses")
        print(f"  - Database URL: {DATABASE_URL}")
        
        # Test matcher module
        print("✓ Testing matcher module...")
        from matcher import TenderMatcher
        matcher = TenderMatcher()
        print("  - TenderMatcher class imported successfully")
        
        # Test models module
        print("✓ Testing models module...")
        from models import Base, SessionLocal, Tender, save_tender_to_db, get_db
        print("  - Database models imported successfully")
        
        # Test selenium_utils module
        print("✓ Testing selenium_utils module...")
        from selenium_utils import selenium_manager
        print("  - Selenium manager imported successfully")
        
        # Test scrapers module
        print("✓ Testing scrapers module...")
        from scrapers import (
            ProvincialScrapers,
            MunicipalScrapers,
            SpecializedScrapers,
            HealthEducationScrapers
        )
        print("  - Scraper classes imported successfully")
        
        # Test tasks module (this was the main circular import issue)
        print("✓ Testing tasks module...")
        from tasks import app as celery_app
        print("  - Celery app imported successfully")
        
        # Test main module (this should now work without circular imports)
        print("✓ Testing main module...")
        from main import ProcurementScanner, app as fastapi_app
        print("  - FastAPI app and ProcurementScanner imported successfully")
        
        print("\n✅ All imports successful! No circular dependencies detected.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_configuration():
    """Test that all configurations are properly loaded"""
    print("\nTesting configuration...")
    
    try:
        from config import PORTAL_CONFIGS, TKA_COURSES
        
        # Test portal configurations
        required_portals = ['canadabuys', 'merx', 'bcbid', 'seao']
        for portal in required_portals:
            if portal in PORTAL_CONFIGS:
                print(f"✓ Portal '{portal}' configured")
            else:
                print(f"❌ Portal '{portal}' missing from configuration")
                return False
        
        # Test training courses
        if len(TKA_COURSES) > 0:
            print(f"✓ {len(TKA_COURSES)} training courses configured")
        else:
            print("❌ No training courses configured")
            return False
            
        print("✅ Configuration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    
    try:
        from models import SessionLocal
        
        # Try to create a session
        db = SessionLocal()
        db.close()
        print("✅ Database connection test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def main():
    """Main test function"""
    print("=== Circular Import Resolution Test ===\n")
    
    # Run all tests
    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_configuration),
        ("Database Connection", test_database_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = test_func()
        results.append((test_name, result))
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Circular import issues are resolved.")
        return 0
    else:
        print("💥 Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 