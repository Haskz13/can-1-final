#!/usr/bin/env python3
"""
Dependency checker for the procurement scanner
This script verifies that all required packages are available
"""

import sys
import importlib
from typing import List, Tuple

# List of required packages
REQUIRED_PACKAGES = [
    # Core Web Framework
    'fastapi',
    'uvicorn',
    'pydantic',
    'pydantic_settings',
    
    # Database
    'sqlalchemy',
    'psycopg2',
    'alembic',
    
    # Data Processing
    'pandas',
    'numpy',
    'openpyxl',
    
    # Web Scraping
    'aiohttp',
    'requests',
    'bs4',
    'lxml',
    'selenium',
    'httpx',
    
    # Task Queue and Caching
    'celery',
    'redis',
    'kombu',
    
    # Scheduling
    'apscheduler',
    
    # Utilities
    'dateutil',
    'multipart',
    'dotenv',
    'yaml',
    'tenacity',
    
    # Logging
    'loguru',
    
    # Development tools
    'pytest',
    'pytest_asyncio',
    'black',
    'flake8',
    
    # Monitoring
    'prometheus_client',
]

def check_package(package_name: str) -> Tuple[bool, str]:
    """Check if a package is available"""
    try:
        importlib.import_module(package_name)
        return True, f"✓ {package_name}"
    except ImportError as e:
        return False, f"✗ {package_name} - {e}"

def main():
    """Main function to check all dependencies"""
    print("Checking dependencies...")
    print("=" * 50)
    
    all_good = True
    results: List[Tuple[bool, str]] = []
    
    for package in REQUIRED_PACKAGES:
        success, message = check_package(package)
        results.append((success, message))
        if not success:
            all_good = False
    
    # Print results
    for success, message in results:
        print(message)
    
    print("=" * 50)
    
    if all_good:
        print("✅ All dependencies are available!")
        return 0
    else:
        print("❌ Some dependencies are missing!")
        print("\nTo install missing dependencies, run:")
        print("docker-compose exec backend pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 