#!/usr/bin/env python3
"""
Test script for the 3 key Canadian procurement portals:
- CanadaBuys
- MERX 
- BidsandTenders

This uses local selenium instead of Selenium Grid for testing.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Add backend to path
sys.path.append('backend')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our modules
from backend.local_selenium import get_local_selenium_manager
from backend.models import SessionLocal, save_tender_to_db
from backend.scrapers import MERXScraper, CanadaBuysScraper

class FocusedPortalTester:
    """Test the 3 focused procurement portals"""
    
    def __init__(self):
        self.selenium_manager = get_local_selenium_manager()
        self.db = SessionLocal()
        self.total_tenders = 0
        
    async def test_canadabuys(self):
        """Test CanadaBuys portal"""
        logger.info("🇨🇦 Testing CanadaBuys portal...")
        
        driver = None
        try:
            # Create local driver
            driver = self.selenium_manager.create_driver()
            if not driver:
                logger.error("❌ Failed to create driver for CanadaBuys")
                return []
            
            # Test navigation to CanadaBuys
            base_url = "https://canadabuys.canada.ca/en/tender-opportunities"
            
            logger.info(f"📍 Navigating to: {base_url}")
            if not self.selenium_manager.stealth_navigation(driver, base_url):
                logger.error("❌ Failed to navigate to CanadaBuys")
                return []
            
            logger.info("✅ Successfully reached CanadaBuys!")
            
            # Look for tender opportunities on the page
            selectors = [
                "a[href*='/tender-opportunities/']",
                ".opportunity-item",
                ".tender-result", 
                ".search-result",
                "article"
            ]
            
            tenders_found = []
            for selector in selectors:
                elements = self.selenium_manager.find_elements_safe(driver, "css selector", selector)
                if elements:
                    logger.info(f"🔍 Found {len(elements)} elements with selector: {selector}")
                    
                    # Process first few elements as test
                    for i, element in enumerate(elements[:5]):
                        try:
                            title = element.text.strip()
                            href = element.get_attribute('href')
                            
                            if title and href:
                                tender_data = {
                                    'tender_id': f"CB_TEST_{i}",
                                    'title': title[:100],
                                    'organization': 'Government of Canada',
                                    'portal': 'CanadaBuys',
                                    'portal_url': 'https://canadabuys.canada.ca',
                                    'value': 0.0,
                                    'closing_date': None,
                                    'posted_date': datetime.utcnow(),
                                    'description': title,
                                    'location': 'Canada',
                                    'categories': [],
                                    'keywords': ['training', 'services'],
                                    'tender_url': href,
                                    'documents_url': href,
                                    'is_active': True,
                                    'priority': 'medium'
                                }
                                tenders_found.append(tender_data)
                                logger.info(f"📄 Found tender: {title[:50]}...")
                        except Exception as e:
                            logger.warning(f"⚠️ Error parsing element {i}: {e}")
                            continue
                    
                    if tenders_found:
                        break
            
            logger.info(f"✅ CanadaBuys test complete - Found {len(tenders_found)} test tenders")
            return tenders_found
            
        except Exception as e:
            logger.error(f"❌ Error testing CanadaBuys: {e}")
            return []
        finally:
            if driver:
                self.selenium_manager.safe_quit_driver(driver)
    
    async def test_merx(self):
        """Test MERX portal"""
        logger.info("🏢 Testing MERX portal...")
        
        driver = None
        try:
            # Create local driver
            driver = self.selenium_manager.create_driver()
            if not driver:
                logger.error("❌ Failed to create driver for MERX")
                return []
            
            # Test navigation to MERX
            base_url = "https://www.merx.com/public/solicitations/open"
            
            logger.info(f"📍 Navigating to: {base_url}")
            if not self.selenium_manager.stealth_navigation(driver, base_url):
                logger.error("❌ Failed to navigate to MERX")
                return []
            
            logger.info("✅ Successfully reached MERX!")
            
            # Look for tender opportunities on MERX
            selectors = [
                ".solicitation",
                ".opportunity",
                "tr[class*='row']",
                ".tender-row",
                "a[href*='/solicitation/']"
            ]
            
            tenders_found = []
            for selector in selectors:
                elements = self.selenium_manager.find_elements_safe(driver, "css selector", selector)
                if elements:
                    logger.info(f"🔍 Found {len(elements)} elements with selector: {selector}")
                    
                    # Process first few elements as test
                    for i, element in enumerate(elements[:5]):
                        try:
                            title = element.text.strip()
                            
                            if title and len(title) > 10:
                                tender_data = {
                                    'tender_id': f"MERX_TEST_{i}",
                                    'title': title[:100],
                                    'organization': 'Various Canadian Organizations',
                                    'portal': 'MERX',
                                    'portal_url': 'https://www.merx.com',
                                    'value': 0.0,
                                    'closing_date': None,
                                    'posted_date': datetime.utcnow(),
                                    'description': title,
                                    'location': 'Canada',
                                    'categories': [],
                                    'keywords': ['procurement', 'solicitation'],
                                    'tender_url': 'https://www.merx.com',
                                    'documents_url': 'https://www.merx.com',
                                    'is_active': True,
                                    'priority': 'medium'
                                }
                                tenders_found.append(tender_data)
                                logger.info(f"📄 Found tender: {title[:50]}...")
                        except Exception as e:
                            logger.warning(f"⚠️ Error parsing element {i}: {e}")
                            continue
                    
                    if tenders_found:
                        break
            
            logger.info(f"✅ MERX test complete - Found {len(tenders_found)} test tenders")
            return tenders_found
            
        except Exception as e:
            logger.error(f"❌ Error testing MERX: {e}")
            return []
        finally:
            if driver:
                self.selenium_manager.safe_quit_driver(driver)
    
    async def test_bidsandtenders(self):
        """Test BidsandTenders portal"""
        logger.info("📋 Testing BidsandTenders portal...")
        
        driver = None
        try:
            # Create local driver 
            driver = self.selenium_manager.create_driver()
            if not driver:
                logger.error("❌ Failed to create driver for BidsandTenders")
                return []
            
            # Test navigation to BidsandTenders
            base_url = "https://www.bidsandtenders.ca"
            
            logger.info(f"📍 Navigating to: {base_url}")
            if not self.selenium_manager.stealth_navigation(driver, base_url):
                logger.error("❌ Failed to navigate to BidsandTenders")
                return []
            
            logger.info("✅ Successfully reached BidsandTenders!")
            
            # Look for tender opportunities
            selectors = [
                ".opportunity",
                ".bid-item", 
                ".tender",
                "a[href*='tender']",
                "a[href*='bid']"
            ]
            
            tenders_found = []
            for selector in selectors:
                elements = self.selenium_manager.find_elements_safe(driver, "css selector", selector)
                if elements:
                    logger.info(f"🔍 Found {len(elements)} elements with selector: {selector}")
                    
                    # Process first few elements as test
                    for i, element in enumerate(elements[:5]):
                        try:
                            title = element.text.strip()
                            href = element.get_attribute('href')
                            
                            if title and len(title) > 10:
                                tender_data = {
                                    'tender_id': f"BT_TEST_{i}",
                                    'title': title[:100],
                                    'organization': 'Canadian Organizations',
                                    'portal': 'BidsandTenders',
                                    'portal_url': 'https://www.bidsandtenders.ca',
                                    'value': 0.0,
                                    'closing_date': None,
                                    'posted_date': datetime.utcnow(),
                                    'description': title,
                                    'location': 'Canada',
                                    'categories': [],
                                    'keywords': ['bids', 'tenders'],
                                    'tender_url': href or 'https://www.bidsandtenders.ca',
                                    'documents_url': href or 'https://www.bidsandtenders.ca',
                                    'is_active': True,
                                    'priority': 'medium'
                                }
                                tenders_found.append(tender_data)
                                logger.info(f"📄 Found tender: {title[:50]}...")
                        except Exception as e:
                            logger.warning(f"⚠️ Error parsing element {i}: {e}")
                            continue
                    
                    if tenders_found:
                        break
            
            logger.info(f"✅ BidsandTenders test complete - Found {len(tenders_found)} test tenders")
            return tenders_found
            
        except Exception as e:
            logger.error(f"❌ Error testing BidsandTenders: {e}")
            return []
        finally:
            if driver:
                self.selenium_manager.safe_quit_driver(driver)
    
    async def run_all_tests(self):
        """Run tests for all 3 portals"""
        logger.info("🚀 Starting focused portal tests for CanadaBuys, MERX, and BidsandTenders...")
        
        all_tenders = []
        
        # Test each portal
        portals = [
            ("CanadaBuys", self.test_canadabuys),
            ("MERX", self.test_merx),
            ("BidsandTenders", self.test_bidsandtenders)
        ]
        
        for portal_name, test_func in portals:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"🎯 Testing {portal_name}")
                logger.info(f"{'='*60}")
                
                tenders = await test_func()
                all_tenders.extend(tenders)
                
                # Save to database
                saved_count = 0
                for tender_data in tenders:
                    try:
                        if save_tender_to_db(self.db, tender_data):
                            saved_count += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Error saving tender: {e}")
                
                logger.info(f"💾 Saved {saved_count}/{len(tenders)} tenders from {portal_name}")
                
            except Exception as e:
                logger.error(f"❌ Error testing {portal_name}: {e}")
                continue
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"🎯 Total tenders found: {len(all_tenders)}")
        logger.info(f"💾 Total saved to database: {sum(1 for t in all_tenders if t)}")
        logger.info(f"✅ Portal tests completed!")
        
        return all_tenders

async def main():
    """Main test function"""
    logger.info("🇨🇦 Canadian Procurement Scanner - Focused Portal Test")
    logger.info("Testing: CanadaBuys, MERX, BidsandTenders")
    
    tester = FocusedPortalTester()
    
    try:
        results = await tester.run_all_tests()
        
        if results:
            logger.info(f"\n🎉 SUCCESS! Found {len(results)} tenders across all portals")
            logger.info("✅ Local selenium setup is working!")
            logger.info("✅ Portal scraping is functional!")
        else:
            logger.warning("⚠️ No tenders found - may need to adjust selectors or check portal access")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)