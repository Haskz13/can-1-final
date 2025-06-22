#!/usr/bin/env python3
"""
Comprehensive test script to test all 21 portals individually
"""

import asyncio
import sys
import os
import time
import traceback
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import ProcurementScanner
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('portal_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PortalTester:
    def __init__(self):
        self.scanner = ProcurementScanner()
        self.results = {}
        
    async def test_portal(self, portal_name: str, scan_method, *args):
        """Test a specific portal and return detailed results"""
        start_time = time.time()
        tenders_found = 0
        error_message = None
        success = False
        
        try:
            logger.info(f"🚀 Testing {portal_name}...")
            
            # Call the scan method
            if asyncio.iscoroutinefunction(scan_method):
                results = await scan_method(*args)
            else:
                results = scan_method(*args)
            
            # Process results
            if isinstance(results, list):
                tenders_found = len(results)
                success = True
                logger.info(f"✅ {portal_name}: Found {tenders_found} tenders")
            else:
                error_message = f"Unexpected result type: {type(results)}"
                logger.error(f"❌ {portal_name}: {error_message}")
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ {portal_name}: Error - {error_message}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            'portal': portal_name,
            'success': success,
            'tenders_found': tenders_found,
            'duration': duration,
            'error': error_message
        }
    
    async def run_all_tests(self):
        """Run tests for all portals"""
        logger.info("🎯 Starting comprehensive portal testing...")
        
        # Define all portal tests
        portal_tests = [
            # Core portals
            ("MERX", self.scanner.scan_merx),
            ("BC Bid", self.scanner.scan_bcbid),
            ("SEAO Web", self.scanner.scan_seao_web),
            ("SEAO API", self.scanner.scan_seao_api),
            ("Bids&Tenders", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all"),
            
            # Biddingo
            ("Biddingo", self.scanner.scan_biddingo, "Biddingo", {'search_url': 'https://www.biddingo.com/'}),
            
            # MERX Regional Portals (using the same method with different URLs)
            ("MERX Ottawa", self.scanner.scan_bidsandtenders_portal, "MERX Ottawa", "https://www.merx.com/gov/ottawa/opportunities"),
            ("MERX Winnipeg", self.scanner.scan_bidsandtenders_portal, "MERX Winnipeg", "https://www.merx.com/gov/winnipeg/opportunities"),
            ("MERX Calgary", self.scanner.scan_bidsandtenders_portal, "MERX Calgary", "https://www.merx.com/gov/calgary/opportunities"),
            
            # Bids&Tenders Regional Portals
            ("Bids&Tenders Alberta", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders Alberta", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=AB"),
            ("Bids&Tenders BC", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders BC", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=BC"),
            ("Bids&Tenders Manitoba", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders Manitoba", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=MB"),
            ("Bids&Tenders New Brunswick", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders New Brunswick", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=NB"),
            ("Bids&Tenders Newfoundland", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders Newfoundland", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=NL"),
            ("Bids&Tenders Nova Scotia", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders Nova Scotia", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=NS"),
            ("Bids&Tenders Ontario", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders Ontario", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=ON"),
            ("Bids&Tenders PEI", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders PEI", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=PE"),
            ("Bids&Tenders Quebec", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders Quebec", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=QC"),
            ("Bids&Tenders Saskatchewan", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders Saskatchewan", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=SK"),
            ("Bids&Tenders Yukon", self.scanner.scan_bidsandtenders_portal, "Bids&Tenders Yukon", "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=YT"),
        ]
        
        total_portals = len(portal_tests)
        successful_portals = 0
        total_tenders = 0
        
        logger.info(f"📊 Testing {total_portals} portals...")
        
        for i, test in enumerate(portal_tests, 1):
            portal_name = test[0]
            scan_method = test[1]
            args = test[2:] if len(test) > 2 else []
            
            logger.info(f"📋 [{i}/{total_portals}] Testing {portal_name}")
            
            result = await self.test_portal(portal_name, scan_method, *args)
            self.results[portal_name] = result
            
            if result['success']:
                successful_portals += 1
                tenders_found = int(result['tenders_found'] or 0)
                total_tenders += tenders_found
            
            # Small delay between tests to avoid overwhelming the system
            await asyncio.sleep(2)
        
        # Print summary
        self.print_summary(total_portals, successful_portals, total_tenders)
        
        return self.results
    
    def print_summary(self, total_portals, successful_portals, total_tenders):
        """Print comprehensive test summary"""
        logger.info("=" * 80)
        logger.info("🎯 COMPREHENSIVE PORTAL TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"📊 Total Portals Tested: {total_portals}")
        logger.info(f"✅ Successful Portals: {successful_portals}")
        logger.info(f"❌ Failed Portals: {total_portals - successful_portals}")
        logger.info(f"📈 Success Rate: {(successful_portals/total_portals)*100:.1f}%")
        logger.info(f"📋 Total Tenders Found: {total_tenders}")
        logger.info("=" * 80)
        
        # Detailed results
        logger.info("📋 DETAILED RESULTS:")
        logger.info("-" * 80)
        
        for portal_name, result in self.results.items():
            status = "✅" if result['success'] else "❌"
            tenders = result['tenders_found']
            duration = result['duration']
            error = result['error'] if result['error'] else "None"
            
            logger.info(f"{status} {portal_name}:")
            logger.info(f"   Tenders: {tenders}")
            logger.info(f"   Duration: {duration:.2f}s")
            if not result['success']:
                logger.info(f"   Error: {error}")
            logger.info("")

async def main():
    """Main test function"""
    tester = PortalTester()
    results = await tester.run_all_tests()
    
    # Save results to file
    with open('portal_test_results.txt', 'w') as f:
        f.write("PORTAL TEST RESULTS\n")
        f.write("=" * 50 + "\n\n")
        
        for portal_name, result in results.items():
            f.write(f"Portal: {portal_name}\n")
            f.write(f"Success: {result['success']}\n")
            f.write(f"Tenders Found: {result['tenders_found']}\n")
            f.write(f"Duration: {result['duration']:.2f}s\n")
            if result['error']:
                f.write(f"Error: {result['error']}\n")
            f.write("-" * 30 + "\n")
    
    logger.info("💾 Results saved to portal_test_results.txt")

if __name__ == "__main__":
    asyncio.run(main()) 