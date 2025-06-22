#!/usr/bin/env python3
"""
Test script to test MERX portal specifically
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

async def test_merx():
    """Test MERX portal specifically"""
    scanner = ProcurementScanner()
    
    try:
        logger.info("🚀 Testing MERX portal...")
        start_time = asyncio.get_event_loop().time()
        
        # Test MERX scanning
        tenders = await scanner.scan_merx()
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        logger.info(f"✅ MERX Test Complete!")
        logger.info(f"📊 Results:")
        logger.info(f"   - Found: {len(tenders)} tenders")
        logger.info(f"   - Duration: {duration:.2f} seconds")
        
        if tenders:
            logger.info(f"   - Sample tender: {tenders[0]['title'][:50]}...")
            logger.info(f"   - Sample URL: {tenders[0]['tender_url']}")
        
        return len(tenders)
        
    except Exception as e:
        logger.error(f"❌ MERX test failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    result = asyncio.run(test_merx())
    print(f"\n🎯 MERX Test Result: {result} tenders found") 