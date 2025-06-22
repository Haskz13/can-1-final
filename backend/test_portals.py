#!/usr/bin/env python3
"""
Test script to run every portal individually and check results
"""

import asyncio
import sys
import os
import time
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
            for i, tender in enumerate(results[:2]):
                logger.info(f"  {i+1}. {tender.get('title', 'No title')[:60]}...")
        return len(results), duration
    except Exception as e:
        logger.error(f"{portal_name}: Error - {e}")
        return 0, 0
    finally:
        # Sleep to allow resources to be released
        time.sleep(2)

async def main():
    """Test all portals individually"""
    scanner = ProcurementScanner()
    # List of all portals to test (add/remove as needed)
    portal_tests = [
        # ("CanadaBuys", scanner.scan_canadabuys),  # SKIP CanadaBuys to avoid resource issues
        ("MERX", scanner.scan_merx),
        ("BC Bid", scanner.scan_bcbid),
        ("SEAO Web", scanner.scan_seao_web),
        ("SEAO API", scanner.scan_seao_api),
        ("Biddingo", scanner.scan_biddingo, "Biddingo", {'search_url': 'https://www.biddingo.com/' }),
        ("MERX Ottawa", scanner.scan_merx, "MERX Ottawa", {'search_url': 'https://www.merx.com/gov/ottawa/opportunities'}),
        ("MERX Winnipeg", scanner.scan_merx, "MERX Winnipeg", {'search_url': 'https://www.merx.com/gov/winnipeg/opportunities'}),
        ("MERX Calgary", scanner.scan_merx, "MERX Calgary", {'search_url': 'https://www.merx.com/gov/calgary/opportunities'}),
        ("Bids&Tenders Alberta", scanner.scan_bidsandtenders_portal, "Bids&Tenders Alberta", "https://www.bidsandtenders.ca/section.asp?section=2&sectionTypeId=3&ekfrm=6"),
        ("Bids&Tenders BC", scanner.scan_bidsandtenders_portal, "Bids&Tenders BC", "https://www.bidsandtenders.ca/section.asp?section=2&sectionTypeId=3&ekfrm=2"),
        ("Bids&Tenders Manitoba", scanner.scan_bidsandtenders_portal, "Bids&Tenders Manitoba", "https://www.bidsandtenders.ca/section.asp?section=2&sectionTypeId=3&ekfrm=3"),
        ("Bids&Tenders Ontario", scanner.scan_bidsandtenders_portal, "Bids&Tenders Ontario", "https://www.bidsandtenders.ca/section.asp?section=2&sectionTypeId=3&ekfrm=4"),
        ("Bids&Tenders Saskatchewan", scanner.scan_bidsandtenders_portal, "Bids&Tenders Saskatchewan", "https://www.bidsandtenders.ca/section.asp?section=2&sectionTypeId=3&ekfrm=5"),
        # TODO: Re-add Jaggaer and SciQuest portals if/when scan_jaggaer_portal and scan_sciquest_portal are implemented
        # ("Jaggaer Alberta", scanner.scan_jaggaer_portal, "Jaggaer Alberta", {'search_url': 'https://alberta.bonfirehub.com/opportunities'}),
        # ("Jaggaer BC", scanner.scan_jaggaer_portal, "Jaggaer BC", {'search_url': 'https://bc.bonfirehub.com/opportunities'}),
        # ("Jaggaer Manitoba", scanner.scan_jaggaer_portal, "Jaggaer Manitoba", {'search_url': 'https://manitoba.bonfirehub.com/opportunities'}),
        # ("Jaggaer Ontario", scanner.scan_jaggaer_portal, "Jaggaer Ontario", {'search_url': 'https://ontario.bonfirehub.com/opportunities'}),
        # ("Jaggaer Saskatchewan", scanner.scan_jaggaer_portal, "Jaggaer Saskatchewan", {'search_url': 'https://saskatchewan.bonfirehub.com/opportunities'}),
        # ("SciQuest Alberta", scanner.scan_sciquest_portal, "SciQuest Alberta", {'search_url': 'https://alberta.sciquest.com/apps/rfq/rq_search_results.asp'}),
        # ("SciQuest BC", scanner.scan_sciquest_portal, "SciQuest BC", {'search_url': 'https://bc.sciquest.com/apps/rfq/rq_search_results.asp'}),
        # ("SciQuest Manitoba", scanner.scan_sciquest_portal, "SciQuest Manitoba", {'search_url': 'https://manitoba.sciquest.com/apps/rfq/rq_search_results.asp'}),
        # ("SciQuest Ontario", scanner.scan_sciquest_portal, "SciQuest Ontario", {'search_url': 'https://ontario.sciquest.com/apps/rfq/rq_search_results.asp'}),
        # ("SciQuest Saskatchewan", scanner.scan_sciquest_portal, "SciQuest Saskatchewan", {'search_url': 'https://saskatchewan.sciquest.com/apps/rfq/rq_search_results.asp'}),
        # ("NATO", scanner.scan_nato_portal, "NATO", {'search_url': 'https://www.nato.int/cps/en/natohq/tenders.htm'}),
    ]
    logger.info(f"Testing {len(portal_tests)} portals...")
    logger.info("=" * 80)
    results = {}
    for test in portal_tests:
        portal_name = test[0]
        scan_method = test[1]
        args = test[2:] if len(test) > 2 else []
        count, duration = await test_portal(portal_name, scan_method, *args)
        results[portal_name] = {'count': count, 'duration': duration}
        logger.info("-" * 40)
    # Summary
    logger.info("=" * 80)
    logger.info("SUMMARY:")
    logger.info("=" * 80)
    total_tenders = 0
    working_portals = 0
    for portal_name, result in results.items():
        if result['count'] > 0:
            working_portals += 1
            total_tenders += result['count']
            logger.info(f"✓ {portal_name}: {result['count']} tenders ({result['duration']:.2f}s)")
        else:
            logger.info(f"✗ {portal_name}: No tenders found ({result['duration']:.2f}s)")
    logger.info("=" * 80)
    logger.info(f"Total working portals: {working_portals}/{len(portal_tests)}")
    logger.info(f"Total tenders found: {total_tenders}")

if __name__ == "__main__":
    asyncio.run(main()) 