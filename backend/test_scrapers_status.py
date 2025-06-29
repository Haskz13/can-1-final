#!/usr/bin/env python3
"""Test script to check which scrapers are implemented and available"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test imports
print("=== Testing Scraper Imports ===")

try:
    from scrapers import MERXScraper
    print("✓ MERXScraper imported successfully")
except Exception as e:
    print(f"✗ MERXScraper import failed: {e}")

try:
    from scrapers import CanadaBuysScraper
    print("✓ CanadaBuysScraper imported successfully")
except Exception as e:
    print(f"✗ CanadaBuysScraper import failed: {e}")

try:
    from scrapers import ProvincialScrapers
    print("✓ ProvincialScrapers imported successfully")
except Exception as e:
    print(f"✗ ProvincialScrapers import failed: {e}")

try:
    from scrapers import MunicipalScrapers
    print("✓ MunicipalScrapers imported successfully")
except Exception as e:
    print(f"✗ MunicipalScrapers import failed: {e}")

try:
    from scrapers import SpecializedScrapers
    print("✓ SpecializedScrapers imported successfully")
except Exception as e:
    print(f"✗ SpecializedScrapers import failed: {e}")

try:
    from scrapers import HealthEducationScrapers
    print("✓ HealthEducationScrapers imported successfully")
except Exception as e:
    print(f"✗ HealthEducationScrapers import failed: {e}")

try:
    from scrapers import BidsAndTendersScraper
    print("✓ BidsAndTendersScraper imported successfully")
except Exception as e:
    print(f"✗ BidsAndTendersScraper import failed: {e}")

try:
    from scrapers import BiddingoScraper
    print("✓ BiddingoScraper imported successfully")
except Exception as e:
    print(f"✗ BiddingoScraper import failed: {e}")

print("\n=== Checking Portal Configuration ===")

try:
    from config import PORTAL_CONFIGS
    print(f"✓ Found {len(PORTAL_CONFIGS)} portal configurations")
    for portal_name, config in PORTAL_CONFIGS.items():
        print(f"  - {portal_name}: {config.get('url', 'No URL')}")
except Exception as e:
    print(f"✗ Failed to load portal configurations: {e}")

print("\n=== Checking Main Scanner ===")

try:
    # Check if main.py has the scan methods for all portals
    with open('main.py', 'r') as f:
        content = f.read()
        
    scan_methods = [
        'scan_canadabuys',
        'scan_merx', 
        'scan_bcbid',
        'scan_seao_web',
        'scan_seao_api',
        'scan_biddingo',
        'scan_bidsandtenders_portal'
    ]
    
    print("Scan methods found in main.py:")
    for method in scan_methods:
        if f'async def {method}' in content:
            print(f"  ✓ {method}")
        else:
            print(f"  ✗ {method} NOT FOUND")
            
except Exception as e:
    print(f"✗ Failed to check main.py: {e}")

print("\n=== Summary ===")
print("The scrapers are implemented but require the following dependencies:")
print("- aiohttp")
print("- selenium")
print("- beautifulsoup4")
print("- pandas")
print("- sqlalchemy")
print("- fastapi")
print("\nTo fix the application, you need to:")
print("1. Create a virtual environment: python3 -m venv venv")
print("2. Activate it: source venv/bin/activate")
print("3. Install dependencies: pip install -r requirements.txt")