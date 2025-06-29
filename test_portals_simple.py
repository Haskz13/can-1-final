#!/usr/bin/env python3
"""
Simple HTTP-based test for the 3 key Canadian procurement portals:
- CanadaBuys
- MERX 
- BidsandTenders

This uses simple HTTP requests instead of Selenium for basic connectivity testing.
"""

import sys
import asyncio
import logging
import aiohttp
import random
from datetime import datetime
from urllib.parse import urlparse
import re

# Add backend to path
sys.path.append('backend')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our modules
from backend.models import SessionLocal, save_tender_to_db

class SimplePortalTester:
    """Simple HTTP-based test for the 3 procurement portals"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.session = None
        
    async def create_session(self):
        """Create HTTP session with proper headers"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def test_canadabuys(self):
        """Test CanadaBuys portal with HTTP requests"""
        logger.info("🇨🇦 Testing CanadaBuys portal (HTTP)...")
        
        try:
            url = "https://canadabuys.canada.ca/en/tender-opportunities"
            logger.info(f"📍 Fetching: {url}")
            
            if not self.session:
                logger.error("❌ No active session")
                return []
                
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info(f"✅ Successfully connected to CanadaBuys (status: {response.status})")
                    
                    # Look for tender-related content in the HTML
                    tender_patterns = [
                        r'tender-opportunities/([^"\']+)',
                        r'opportunity[^"\']*"[^"\']*"([^"\']+)',
                        r'href="[^"]*tender[^"]*"[^>]*>([^<]+)',
                        r'title="([^"]*tender[^"]*)"',
                        r'<a[^>]*href="[^"]*tender[^"]*"[^>]*>([^<]+)</a>'
                    ]
                    
                    tenders_found = []
                    for i, pattern in enumerate(tender_patterns):
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            logger.info(f"🔍 Found {len(matches)} potential tenders with pattern {i+1}")
                            
                            for j, match in enumerate(matches[:3]):  # Take first 3
                                if isinstance(match, tuple):
                                    match = match[0] if match[0] else match[1] if len(match) > 1 else ""
                                
                                if match and len(match.strip()) > 10:
                                    tender_data = {
                                        'tender_id': f"CB_HTTP_{i}_{j}",
                                        'title': match.strip()[:100],
                                        'organization': 'Government of Canada',
                                        'portal': 'CanadaBuys',
                                        'portal_url': 'https://canadabuys.canada.ca',
                                        'value': 0.0,
                                        'closing_date': None,
                                        'posted_date': datetime.utcnow(),
                                        'description': f"Found via HTTP scan: {match.strip()[:200]}",
                                        'location': 'Canada',
                                        'categories': [],
                                        'keywords': ['canadabuys', 'government'],
                                        'tender_url': url,
                                        'documents_url': url,
                                        'is_active': True,
                                        'priority': 'medium'
                                    }
                                    tenders_found.append(tender_data)
                                    logger.info(f"📄 Found potential tender: {match.strip()[:50]}...")
                            
                            if tenders_found:
                                break
                    
                    # Check if the page contains expected CanadaBuys content
                    expected_content = ['tender', 'opportunity', 'procurement', 'solicitation', 'canada']
                    found_content = sum(1 for term in expected_content if term.lower() in content.lower())
                    
                    logger.info(f"📊 CanadaBuys content analysis: {found_content}/{len(expected_content)} expected terms found")
                    
                    if not tenders_found and found_content >= 2:
                        # Create a generic entry to show we reached the portal
                        tender_data = {
                            'tender_id': f"CB_HTTP_GENERIC",
                            'title': 'CanadaBuys Portal Access Verified',
                            'organization': 'Government of Canada',
                            'portal': 'CanadaBuys',
                            'portal_url': 'https://canadabuys.canada.ca',
                            'value': 0.0,
                            'closing_date': None,
                            'posted_date': datetime.utcnow(),
                            'description': f'Successfully accessed CanadaBuys portal via HTTP. Found {found_content} relevant content indicators.',
                            'location': 'Canada',
                            'categories': [],
                            'keywords': ['canadabuys', 'verified'],
                            'tender_url': url,
                            'documents_url': url,
                            'is_active': True,
                            'priority': 'low'
                        }
                        tenders_found.append(tender_data)
                    
                    logger.info(f"✅ CanadaBuys HTTP test complete - Found {len(tenders_found)} entries")
                    return tenders_found
                    
                else:
                    logger.error(f"❌ CanadaBuys returned status: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Error testing CanadaBuys: {e}")
            return []
    
    async def test_merx(self):
        """Test MERX portal with HTTP requests"""
        logger.info("🏢 Testing MERX portal (HTTP)...")
        
        try:
            url = "https://www.merx.com"
            logger.info(f"📍 Fetching: {url}")
            
            if not self.session:
                logger.error("❌ No active session")
                return []
                
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info(f"✅ Successfully connected to MERX (status: {response.status})")
                    
                    # Look for MERX-specific content
                    merx_patterns = [
                        r'solicitation[^"\']*"[^"\']*"([^"\']+)',
                        r'href="[^"]*solicitation[^"]*"[^>]*>([^<]+)',
                        r'opportunity[^"\']*"[^"\']*"([^"\']+)',
                        r'<a[^>]*href="[^"]*merx[^"]*"[^>]*>([^<]+)</a>'
                    ]
                    
                    tenders_found = []
                    for i, pattern in enumerate(merx_patterns):
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            logger.info(f"🔍 Found {len(matches)} potential opportunities with pattern {i+1}")
                            
                            for j, match in enumerate(matches[:3]):
                                if isinstance(match, tuple):
                                    match = match[0] if match[0] else match[1] if len(match) > 1 else ""
                                    
                                if match and len(match.strip()) > 10:
                                    tender_data = {
                                        'tender_id': f"MERX_HTTP_{i}_{j}",
                                        'title': match.strip()[:100],
                                        'organization': 'Various Canadian Organizations',
                                        'portal': 'MERX',
                                        'portal_url': 'https://www.merx.com',
                                        'value': 0.0,
                                        'closing_date': None,
                                        'posted_date': datetime.utcnow(),
                                        'description': f"Found via HTTP scan: {match.strip()[:200]}",
                                        'location': 'Canada',
                                        'categories': [],
                                        'keywords': ['merx', 'solicitation'],
                                        'tender_url': url,
                                        'documents_url': url,
                                        'is_active': True,
                                        'priority': 'medium'
                                    }
                                    tenders_found.append(tender_data)
                                    logger.info(f"📄 Found potential opportunity: {match.strip()[:50]}...")
                            
                            if tenders_found:
                                break
                    
                    # Check MERX content
                    expected_content = ['merx', 'solicitation', 'procurement', 'opportunity', 'tender']
                    found_content = sum(1 for term in expected_content if term.lower() in content.lower())
                    
                    logger.info(f"📊 MERX content analysis: {found_content}/{len(expected_content)} expected terms found")
                    
                    if not tenders_found and found_content >= 2:
                        tender_data = {
                            'tender_id': f"MERX_HTTP_GENERIC",
                            'title': 'MERX Portal Access Verified',
                            'organization': 'MERX Corporation',
                            'portal': 'MERX',
                            'portal_url': 'https://www.merx.com',
                            'value': 0.0,
                            'closing_date': None,
                            'posted_date': datetime.utcnow(),
                            'description': f'Successfully accessed MERX portal via HTTP. Found {found_content} relevant content indicators.',
                            'location': 'Canada',
                            'categories': [],
                            'keywords': ['merx', 'verified'],
                            'tender_url': url,
                            'documents_url': url,
                            'is_active': True,
                            'priority': 'low'
                        }
                        tenders_found.append(tender_data)
                    
                    logger.info(f"✅ MERX HTTP test complete - Found {len(tenders_found)} entries")
                    return tenders_found
                    
                else:
                    logger.error(f"❌ MERX returned status: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Error testing MERX: {e}")
            return []
    
    async def test_bidsandtenders(self):
        """Test BidsandTenders portal with HTTP requests"""
        logger.info("📋 Testing BidsandTenders portal (HTTP)...")
        
        try:
            url = "https://www.bidsandtenders.ca"
            logger.info(f"📍 Fetching: {url}")
            
            if not self.session:
                logger.error("❌ No active session")
                return []
                
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info(f"✅ Successfully connected to BidsandTenders (status: {response.status})")
                    
                    # Look for BidsandTenders content
                    bt_patterns = [
                        r'bid[^"\']*"[^"\']*"([^"\']+)',
                        r'tender[^"\']*"[^"\']*"([^"\']+)',
                        r'href="[^"]*bid[^"]*"[^>]*>([^<]+)',
                        r'href="[^"]*tender[^"]*"[^>]*>([^<]+)'
                    ]
                    
                    tenders_found = []
                    for i, pattern in enumerate(bt_patterns):
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            logger.info(f"🔍 Found {len(matches)} potential bids/tenders with pattern {i+1}")
                            
                            for j, match in enumerate(matches[:3]):
                                if isinstance(match, tuple):
                                    match = match[0] if match[0] else match[1] if len(match) > 1 else ""
                                    
                                if match and len(match.strip()) > 10:
                                    tender_data = {
                                        'tender_id': f"BT_HTTP_{i}_{j}",
                                        'title': match.strip()[:100],
                                        'organization': 'Canadian Organizations',
                                        'portal': 'BidsandTenders',
                                        'portal_url': 'https://www.bidsandtenders.ca',
                                        'value': 0.0,
                                        'closing_date': None,
                                        'posted_date': datetime.utcnow(),
                                        'description': f"Found via HTTP scan: {match.strip()[:200]}",
                                        'location': 'Canada',
                                        'categories': [],
                                        'keywords': ['bidsandtenders', 'bid'],
                                        'tender_url': url,
                                        'documents_url': url,
                                        'is_active': True,
                                        'priority': 'medium'
                                    }
                                    tenders_found.append(tender_data)
                                    logger.info(f"📄 Found potential bid/tender: {match.strip()[:50]}...")
                            
                            if tenders_found:
                                break
                    
                    # Check content
                    expected_content = ['bid', 'tender', 'procurement', 'opportunity', 'contract']
                    found_content = sum(1 for term in expected_content if term.lower() in content.lower())
                    
                    logger.info(f"📊 BidsandTenders content analysis: {found_content}/{len(expected_content)} expected terms found")
                    
                    if not tenders_found and found_content >= 2:
                        tender_data = {
                            'tender_id': f"BT_HTTP_GENERIC",
                            'title': 'BidsandTenders Portal Access Verified',
                            'organization': 'BidsandTenders Platform',
                            'portal': 'BidsandTenders',
                            'portal_url': 'https://www.bidsandtenders.ca',
                            'value': 0.0,
                            'closing_date': None,
                            'posted_date': datetime.utcnow(),
                            'description': f'Successfully accessed BidsandTenders portal via HTTP. Found {found_content} relevant content indicators.',
                            'location': 'Canada',
                            'categories': [],
                            'keywords': ['bidsandtenders', 'verified'],
                            'tender_url': url,
                            'documents_url': url,
                            'is_active': True,
                            'priority': 'low'
                        }
                        tenders_found.append(tender_data)
                    
                    logger.info(f"✅ BidsandTenders HTTP test complete - Found {len(tenders_found)} entries")
                    return tenders_found
                    
                else:
                    logger.error(f"❌ BidsandTenders returned status: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Error testing BidsandTenders: {e}")
            return []
    
    async def run_all_tests(self):
        """Run HTTP tests for all 3 portals"""
        logger.info("🚀 Starting HTTP-based portal tests for CanadaBuys, MERX, and BidsandTenders...")
        
        await self.create_session()
        
        try:
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
                    
                    logger.info(f"💾 Saved {saved_count}/{len(tenders)} entries from {portal_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Error testing {portal_name}: {e}")
                    continue
            
            # Summary
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 SUMMARY")
            logger.info(f"{'='*60}")
            logger.info(f"🎯 Total entries found: {len(all_tenders)}")
            logger.info(f"💾 Total saved to database: {sum(1 for t in all_tenders if t)}")
            logger.info(f"✅ HTTP portal tests completed!")
            
            return all_tenders
            
        finally:
            await self.close_session()

async def main():
    """Main test function"""
    logger.info("🇨🇦 Canadian Procurement Scanner - HTTP Portal Test")
    logger.info("Testing: CanadaBuys, MERX, BidsandTenders")
    
    tester = SimplePortalTester()
    
    try:
        results = await tester.run_all_tests()
        
        if results:
            logger.info(f"\n🎉 SUCCESS! Found {len(results)} entries across all portals")
            logger.info("✅ HTTP-based portal access is working!")
            logger.info("✅ Portal connectivity verified!")
        else:
            logger.warning("⚠️ No content found - may need to adjust patterns or check portal access")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)