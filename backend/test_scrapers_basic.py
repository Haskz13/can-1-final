#!/usr/bin/env python3
"""
Basic test script for main scrapers without database dependencies
"""
import asyncio
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import scrapers directly to avoid database dependencies
from scrapers import ProvincialScrapers, MunicipalScrapers, SpecializedScrapers, HealthEducationScrapers

async def test_scraper(scraper_name: str, scraper_func, *args):
    """Test a single scraper function"""
    logger.info(f"Testing {scraper_name}...")
    start_time = time.time()
    
    try:
        # Create a mock session for testing
        import aiohttp
        async with aiohttp.ClientSession() as session:
            if asyncio.iscoroutinefunction(scraper_func):
                result = await scraper_func(session)
            else:
                # For non-async functions, run in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, scraper_func, session)
        
        duration = time.time() - start_time
        
        if result and isinstance(result, list):
            logger.info(f"✓ {scraper_name}: Found {len(result)} tenders in {duration:.2f}s")
            # Show first few tenders as examples
            for i, tender in enumerate(result[:3]):
                logger.info(f"  Tender {i+1}: {tender.get('title', 'No title')[:50]}...")
            return len(result), duration
        else:
            logger.warning(f"✗ {scraper_name}: No results or invalid format in {duration:.2f}s")
            return 0, duration
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"✗ {scraper_name}: Error after {duration:.2f}s - {e}")
        return 0, duration

async def main():
    """Test the main scrapers"""
    logger.info("Starting basic scraper tests...")
    logger.info("=" * 60)
    
    # Test session-only scrapers (these don't need Selenium)
    test_scrapers = [
        ("Manitoba Tenders", ProvincialScrapers.scan_manitoba_tenders),
        ("Winnipeg Bids", MunicipalScrapers.scan_winnipeg_bids),
        ("PEI Tenders", SpecializedScrapers.scan_pei_tenders),
        ("NL Procurement", SpecializedScrapers.scan_nl_procurement),
    ]
    
    results = {}
    total_tenders = 0
    working_scrapers = 0
    
    for scraper_name, scraper_func in test_scrapers:
        count, duration = await test_scraper(scraper_name, scraper_func)
        results[scraper_name] = {'count': count, 'duration': duration}
        
        if count > 0:
            working_scrapers += 1
            total_tenders += count
        
        logger.info("-" * 40)
    
    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY:")
    logger.info("=" * 60)
    
    for scraper_name, result in results.items():
        if result['count'] > 0:
            logger.info(f"✓ {scraper_name}: {result['count']} tenders ({result['duration']:.2f}s)")
        else:
            logger.info(f"✗ {scraper_name}: No tenders found ({result['duration']:.2f}s)")
    
    logger.info("=" * 60)
    logger.info(f"Working scrapers: {working_scrapers}/{len(test_scrapers)}")
    logger.info(f"Total tenders found: {total_tenders}")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main()) 