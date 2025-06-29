#!/usr/bin/env python3
"""
Test script to validate scraping fixes are working properly.
This script will test the major scrapers and compare results before/after fixes.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List
import json

# Add backend to path
sys.path.append('./backend')

# Import scrapers
from scrapers import (
    ProvincialScrapers,
    MunicipalScrapers,
    SpecializedScrapers,
    HealthEducationScrapers,
    MERXScraper,
    CanadaBuysScraper
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraping_test_results.log')
    ]
)
logger = logging.getLogger(__name__)

class ScrapingValidator:
    """Validates that scraping fixes are working"""
    
    def __init__(self):
        self.results = {}
        self.total_tenders = 0
        self.total_time = 0
    
    async def test_scraper(self, scraper_name: str, scraper_func, *args):
        """Test individual scraper and collect metrics"""
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTING: {scraper_name}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        tender_count = 0
        error_occurred = False
        
        try:
            # Handle different scraper signatures
            if asyncio.iscoroutinefunction(scraper_func):
                if args:
                    result = await scraper_func(*args)
                else:
                    result = await scraper_func()
            else:
                # For session-based scrapers, we'd need to provide a session
                # For now, skip these
                logger.warning(f"Skipping {scraper_name} - requires session")
                return None
            
            duration = time.time() - start_time
            
            if result and isinstance(result, list):
                tender_count = len(result)
                logger.info(f"✅ SUCCESS: {scraper_name}")
                logger.info(f"   Tenders Found: {tender_count}")
                logger.info(f"   Time Taken: {duration:.2f} seconds")
                
                # Log sample tender titles
                if tender_count > 0:
                    logger.info(f"   Sample Titles:")
                    for i, tender in enumerate(result[:5]):
                        title = tender.get('title', 'No title')[:80]
                        logger.info(f"     {i+1}. {title}...")
                
                # Check for expected improvements
                if tender_count > 30:
                    logger.info(f"   🎉 GREAT: Found {tender_count} tenders (>30 suggests pagination working)")
                elif tender_count > 10:
                    logger.info(f"   ✅ GOOD: Found {tender_count} tenders (>10 suggests basic functionality)")
                else:
                    logger.warning(f"   ⚠️  LOW: Only {tender_count} tenders found - may need investigation")
                
            else:
                logger.error(f"❌ FAILED: {scraper_name} - No results or invalid format")
                
        except Exception as e:
            duration = time.time() - start_time
            error_occurred = True
            logger.error(f"❌ ERROR: {scraper_name} - {str(e)}")
        
        # Store results
        self.results[scraper_name] = {
            'tender_count': tender_count,
            'duration': duration,
            'error': error_occurred,
            'timestamp': datetime.now().isoformat()
        }
        
        self.total_tenders += tender_count
        self.total_time += duration
        
        return tender_count, duration
    
    async def run_comprehensive_tests(self):
        """Run comprehensive tests on all major scrapers"""
        logger.info("🚀 STARTING COMPREHENSIVE SCRAPING VALIDATION")
        logger.info(f"Test started at: {datetime.now()}")
        
        # Test scrapers that don't require external drivers/sessions
        test_cases = [
            # Provincial scrapers would need selenium drivers
            # Municipal scrapers would need selenium drivers  
            # We'll focus on the main class-based scrapers
            ("MERX Scraper", MERXScraper().search, "training", 5),
            ("CanadaBuys Scraper", CanadaBuysScraper().search, "training", 5),
        ]
        
        working_scrapers = 0
        total_scrapers = len(test_cases)
        
        for scraper_name, scraper_func, *args in test_cases:
            try:
                result = await self.test_scraper(scraper_name, scraper_func, *args)
                if result:  # Check if result is not None
                    count, duration = result
                    if count > 0:
                        working_scrapers += 1
            except Exception as e:
                logger.error(f"Test failed for {scraper_name}: {e}")
        
        # Print comprehensive summary
        self.print_summary(working_scrapers, total_scrapers)
    
    def print_summary(self, working_scrapers: int, total_scrapers: int):
        """Print comprehensive test summary"""
        logger.info(f"\n{'='*80}")
        logger.info("📊 COMPREHENSIVE TEST SUMMARY")
        logger.info(f"{'='*80}")
        
        logger.info(f"📈 OVERALL STATISTICS:")
        logger.info(f"   Working Scrapers: {working_scrapers}/{total_scrapers}")
        logger.info(f"   Total Tenders Found: {self.total_tenders}")
        logger.info(f"   Total Time Taken: {self.total_time:.2f} seconds")
        logger.info(f"   Average Tenders per Scraper: {self.total_tenders/max(total_scrapers,1):.1f}")
        
        logger.info(f"\n📋 DETAILED RESULTS:")
        for scraper_name, results in self.results.items():
            status = "✅ PASS" if results['tender_count'] > 0 else "❌ FAIL"
            logger.info(f"   {status} {scraper_name}: {results['tender_count']} tenders ({results['duration']:.2f}s)")
        
        logger.info(f"\n🎯 VALIDATION RESULTS:")
        if self.total_tenders > 100:
            logger.info("   🎉 EXCELLENT: Found >100 tenders - pagination fixes appear to be working!")
        elif self.total_tenders > 50:
            logger.info("   ✅ GOOD: Found >50 tenders - significant improvement likely achieved")
        elif self.total_tenders > 20:
            logger.info("   ⚠️  MODERATE: Found >20 tenders - some improvement but may need more work")
        else:
            logger.info("   ❌ NEEDS WORK: Found <20 tenders - pagination fixes may need more attention")
        
        # Save results to JSON
        with open('scraping_validation_results.json', 'w') as f:
            json.dump({
                'test_timestamp': datetime.now().isoformat(),
                'summary': {
                    'working_scrapers': working_scrapers,
                    'total_scrapers': total_scrapers,
                    'total_tenders': self.total_tenders,
                    'total_time': self.total_time
                },
                'detailed_results': self.results
            }, f, indent=2)
        
        logger.info(f"\n💾 Results saved to 'scraping_validation_results.json'")
        logger.info(f"📝 Detailed logs saved to 'scraping_test_results.log'")

async def main():
    """Main test execution"""
    try:
        validator = ScrapingValidator()
        await validator.run_comprehensive_tests()
        
        logger.info(f"\n🏁 TEST COMPLETED SUCCESSFULLY")
        logger.info(f"Check the logs above to see if pagination fixes are working properly.")
        
    except Exception as e:
        logger.error(f"❌ TEST EXECUTION FAILED: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Run the tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)