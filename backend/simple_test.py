#!/usr/bin/env python3
"""
Simple test script to check key portals
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import ProcurementScanner
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_portal(portal_name: str, scan_method, *args):
    """Test a specific portal and return results"""
    scanner = ProcurementScanner()
    
    try:
        logger.info(f"Testing {portal_name}...")
        start_time = asyncio.get_event_loop().time()
        
        if asyncio.iscoroutinefunction(scan_method):
            results = await scan_method(*args)
        else:
            results = scan_method(*args)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        logger.info(f"{portal_name}: Found {len(results)} tenders in {duration:.2f} seconds")
        
        if results:
            # Show first few results
            for i, tender in enumerate(results[:2]):
                logger.info(f"  {i+1}. {tender.get('title', 'No title')[:60]}...")
        
        return len(results), duration
        
    except Exception as e:
        logger.error(f"{portal_name}: Error - {e}")
        return 0, 0

async def main():
    """Test key portals"""
    scanner = ProcurementScanner()
    
    # Test just a few key portals
    portal_tests = [
        ("CanadaBuys", scanner.scan_canadabuys),
        ("MERX", scanner.scan_merx),
        ("BC Bid", scanner.scan_bcbid),
        ("SEAO Web", scanner.scan_seao_web),
    ]
    
    logger.info(f"Testing {len(portal_tests)} key portals...")
    logger.info("=" * 60)
    
    results = {}
    
    for test in portal_tests:
        portal_name = test[0]
        scan_method = test[1]
        
        count, duration = await test_portal(portal_name, scan_method)
        results[portal_name] = {'count': count, 'duration': duration}
        
        logger.info("-" * 30)
    
    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY:")
    logger.info("=" * 60)
    
    total_tenders = 0
    working_portals = 0
    
    for portal_name, result in results.items():
        if result['count'] > 0:
            working_portals += 1
            total_tenders += result['count']
            logger.info(f"✓ {portal_name}: {result['count']} tenders ({result['duration']:.2f}s)")
        else:
            logger.info(f"✗ {portal_name}: No tenders found ({result['duration']:.2f}s)")
    
    logger.info("=" * 60)
    logger.info(f"Working portals: {working_portals}/{len(portal_tests)}")
    logger.info(f"Total tenders: {total_tenders}")

if __name__ == "__main__":
    asyncio.run(main()) 