#!/usr/bin/env python3
"""
Simple test script to test only the CanadaBuys scraper
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers import CanadaBuysScraper
from selenium_utils import get_driver
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_canadabuys_scraper():
    """Test the CanadaBuys scraper in isolation"""
    logger.info("Starting CanadaBuys scraper test")
    
    try:
        # Test the import first
        logger.info("Testing import of get_driver...")
        driver = get_driver()
        logger.info("✅ get_driver import successful!")
        
        # Test the scraper
        logger.info("Creating CanadaBuys scraper...")
        scraper = CanadaBuysScraper()
        logger.info("✅ CanadaBuys scraper created successfully!")
        
        # Test a simple search
        logger.info("Testing CanadaBuys search with 'training services'...")
        results = await scraper.search("training services")
        logger.info(f"✅ CanadaBuys search completed! Found {len(results)} results")
        
        # Show some results
        for i, tender in enumerate(results[:3]):  # Show first 3 results
            logger.info(f"Result {i+1}: {tender.get('title', 'No title')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if 'driver' in locals():
                driver.quit()
                logger.info("WebDriver closed")
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(test_canadabuys_scraper())
    if success:
        logger.info("🎉 CanadaBuys scraper test PASSED!")
    else:
        logger.error("💥 CanadaBuys scraper test FAILED!")
        sys.exit(1) 