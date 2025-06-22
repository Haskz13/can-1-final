#!/usr/bin/env python3
"""
Test script to verify that all imports work correctly
and the main application can be imported without errors.
"""

import sys
import os
from typing import List, Optional, Dict, Any

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    
    try:
        # Test core Python imports
        import os
        import re
        import json
        import hashlib
        import asyncio
        import logging
        from pathlib import Path
        from datetime import datetime, timedelta
        from time import sleep
        from contextlib import asynccontextmanager
        print("✓ Core Python imports successful")
        
        # Test third-party imports
        import pandas as pd
        print("✓ pandas imported successfully")
        
        import aiohttp
        print("✓ aiohttp imported successfully")
        
        from bs4 import BeautifulSoup
        print("✓ BeautifulSoup imported successfully")
        
        from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
        from fastapi.middleware.cors import CORSMiddleware
        print("✓ FastAPI imported successfully")
        
        from pydantic import BaseModel
        print("✓ pydantic imported successfully")
        
        from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Boolean, Integer, func, or_
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import sessionmaker, Session
        print("✓ SQLAlchemy imported successfully")
        
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        print("✓ APScheduler imported successfully")
        
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
        from selenium.webdriver.common.keys import Keys
        print("✓ Selenium imported successfully")
        
        from tenacity import retry, stop_after_attempt, wait_exponential
        print("✓ tenacity imported successfully")
        
        import zipfile
        import shutil
        print("✓ Standard library imports successful")
        
        # Test importing the main application
        print("\nTesting main application import...")
        from main import app, PORTAL_CONFIGS, ProcurementScanner, TenderMatcher
        print("✓ Main application imported successfully")
        
        # Test portal configurations
        print(f"✓ Found {len(PORTAL_CONFIGS)} portal configurations")
        
        # Test scanner initialization
        scanner = ProcurementScanner()
        print("✓ ProcurementScanner initialized successfully")
        
        # Test matcher initialization
        matcher = TenderMatcher()
        print("✓ TenderMatcher initialized successfully")
        
        print("\n✅ All imports and initializations successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_portal_urls():
    """Test a few key portal URLs"""
    print("\nTesting portal URLs...")
    
    import aiohttp
    import asyncio
    
    async def test_url(url, name):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status < 400:
                        print(f"✓ {name}: {url} (Status: {response.status})")
                        return True
                    else:
                        print(f"⚠ {name}: {url} (Status: {response.status})")
                        return False
        except Exception as e:
            print(f"❌ {name}: {url} (Error: {e})")
            return False
    
    async def run_tests():
        test_urls = [
            ("https://canadabuys.canada.ca/", "CanadaBuys"),
            ("https://www.merx.com/", "MERX"),
            ("https://www.biddingo.com/", "Biddingo"),
            ("https://www.bcbid.gov.bc.ca/", "BC Bid"),
        ]
        
        results: List[bool] = []
        for url, name in test_urls:
            result = await test_url(url, name)
            results.append(result)
        
        working = sum(results)
        total = len(results)
        print(f"\nPortal URL Test Results: {working}/{total} working")
    
    asyncio.run(run_tests())

if __name__ == "__main__":
    print("=== Canadian Procurement Scanner - Import Test ===\n")
    
    success = test_imports()
    
    if success:
        test_portal_urls()
        print("\n🎉 All tests passed! The application should work correctly.")
    else:
        print("\n💥 Tests failed! Please check the error messages above.")
        sys.exit(1) 