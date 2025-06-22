# main.py - Main application with FastAPI
# type: ignore[reportUnknownVariableType, attr-defined, arg-type, reportAttributeAccessIssue]
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import json
import hashlib
import aiohttp

# FastAPI imports
from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Database imports
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

# Selenium imports
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import from our new modules
from models import Base, SessionLocal, Tender, save_tender_to_db, get_db  # type: ignore[reportAny]
from selenium_utils import selenium_manager

# Import scrapers
from scrapers import (
    ProvincialScrapers,
    MunicipalScrapers,
    SpecializedScrapers,
    HealthEducationScrapers
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=SessionLocal().bind)  # type: ignore[reportAny]

# Portal configurations
PORTAL_CONFIGS = {
    'canadabuys': {
        'name': 'CanadaBuys',
        'type': 'api',
        'url': 'https://canadabuys.canada.ca',
        'priority': 'high'
    },
    'merx': {
        'name': 'MERX',
        'type': 'web',
        'url': 'https://www.merx.com',
        'priority': 'high'
    },
    'bcbid': {
        'name': 'BC Bid',
        'type': 'web',
        'url': 'https://www.bcbid.gov.bc.ca',
        'priority': 'high'
    },
    'seao': {
        'name': 'SEAO Quebec',
        'type': 'web',
        'url': 'https://seao.gouv.qc.ca',
        'priority': 'high'
    },
    'biddingo': {
        'name': 'Biddingo',
        'type': 'web',
        'url': 'https://www.biddingo.com',
        'priority': 'medium'
    },
    'bidsandtenders': {
        'name': 'Bids&Tenders',
        'type': 'web',
        'url': 'https://www.bidsandtenders.ca',
        'priority': 'medium'
    },
    # Provincial Portals
    'albertapurchasing': {
        'name': 'Alberta Purchasing Connection',
        'type': 'web',
        'url': 'https://www.alberta.ca/purchasing-connection.aspx',
        'priority': 'high'
    },
    'sasktenders': {
        'name': 'Saskatchewan Tenders',
        'type': 'web',
        'url': 'https://www.sasktenders.ca',
        'priority': 'high'
    },
    'manitoba': {
        'name': 'Manitoba Tenders',
        'type': 'web',
        'url': 'https://www.gov.mb.ca/tenders',
        'priority': 'high'
    },
    'ontario': {
        'name': 'Ontario Tenders',
        'type': 'web',
        'url': 'https://www.ontario.ca/tenders',
        'priority': 'high'
    },
    'ns': {
        'name': 'Nova Scotia Tenders',
        'type': 'web',
        'url': 'https://novascotia.ca/tenders',
        'priority': 'high'
    },
    # Municipal Portals
    'calgary': {
        'name': 'City of Calgary Procurement',
        'type': 'web',
        'url': 'https://www.calgary.ca/procurement',
        'priority': 'medium'
    },
    'winnipeg': {
        'name': 'City of Winnipeg Bids',
        'type': 'web',
        'url': 'https://www.winnipeg.ca/bids',
        'priority': 'medium'
    },
    'vancouver': {
        'name': 'City of Vancouver Procurement',
        'type': 'web',
        'url': 'https://vancouver.ca/procurement',
        'priority': 'medium'
    },
    'halifax': {
        'name': 'City of Halifax Procurement',
        'type': 'web',
        'url': 'https://www.halifax.ca/procurement',
        'priority': 'medium'
    },
    'regina': {
        'name': 'City of Regina Procurement',
        'type': 'web',
        'url': 'https://www.regina.ca/procurement',
        'priority': 'medium'
    },
    # Specialized Portals
    'nbon': {
        'name': 'NBON New Brunswick',
        'type': 'web',
        'url': 'https://www.nbon.ca',
        'priority': 'medium'
    },
    'pei': {
        'name': 'PEI Tenders',
        'type': 'web',
        'url': 'https://www.princeedwardisland.ca/tenders',
        'priority': 'medium'
    },
    'nl': {
        'name': 'Newfoundland Procurement',
        'type': 'web',
        'url': 'https://www.gov.nl.ca/procurement',
        'priority': 'medium'
    },
    # Health & Education Portals
    'buybc': {
        'name': 'BuyBC Health',
        'type': 'web',
        'url': 'https://www.buybc.ca/health',
        'priority': 'medium'
    },
    'mohltc': {
        'name': 'Ontario Health',
        'type': 'web',
        'url': 'https://www.ontariohealth.ca/procurement',
        'priority': 'medium'
    },
    # Bids&Tenders Platform Cities
    'edmonton': {
        'name': 'City of Edmonton',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.ca',
        'search_url': 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=AB',
        'priority': 'medium'
    },
    'ottawa': {
        'name': 'City of Ottawa',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.ca',
        'search_url': 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=ON',
        'priority': 'medium'
    },
    'london': {
        'name': 'City of London',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.ca',
        'search_url': 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=ON',
        'priority': 'medium'
    },
    'hamilton': {
        'name': 'City of Hamilton',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.ca',
        'search_url': 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=ON',
        'priority': 'medium'
    },
    'kitchener': {
        'name': 'City of Kitchener',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.ca',
        'search_url': 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=ON',
        'priority': 'medium'
    }
}

# Training courses for matching
TKA_COURSES = [
    "Project Management", "Leadership", "Communication", "Negotiation",
    "Contract Management", "Procurement", "Supply Chain", "Risk Management",
    "Strategic Planning", "Change Management", "Team Building", "Conflict Resolution",
    "Time Management", "Problem Solving", "Decision Making", "Financial Management",
    "Human Resources", "Marketing", "Sales", "Customer Service", "Quality Management",
    "Process Improvement", "Innovation", "Digital Transformation", "Data Analysis",
    "Business Intelligence", "Cybersecurity", "Cloud Computing", "Agile", "Scrum",
    "Lean Six Sigma", "ISO Standards", "Compliance", "Regulatory Affairs",
    "Environmental Management", "Sustainability", "Corporate Social Responsibility"
]

class TenderMatcher:
    """Match tenders to training courses and calculate priority"""
    
    @staticmethod
    def match_courses(tender: Dict) -> list[str]:
        """Match tender to relevant training courses"""
        text = f"{tender.get('title', '')} {tender.get('description', '')}".lower()
        matched_courses = []
        
        for course in TKA_COURSES:
            if course.lower() in text:
                matched_courses.append(course)
        
        return matched_courses
    
    @staticmethod
    def calculate_priority(tender: Dict) -> str:
        """Calculate tender priority based on various factors"""
        score = 0
        
        # Value-based scoring
        value = tender.get('value', 0)
        if value > 1000000:
            score += 5
        elif value > 500000:
            score += 3
        elif value > 100000:
            score += 2
        elif value > 50000:
            score += 1
        
        # Time-based scoring
        closing_date = tender.get('closing_date')
        if closing_date:
            days_until_closing = (closing_date - datetime.utcnow()).days
            if days_until_closing <= 7:
                score += 5
            elif days_until_closing <= 14:
                score += 3
            elif days_until_closing <= 30:
                score += 1
        
        # Portal-based scoring
        portal = tender.get('portal', '').lower()
        if 'canadabuys' in portal:
            score += 3
        elif 'merx' in portal:
            score += 2
        elif 'bcbid' in portal:
            score += 2
        
        # Course matching scoring
        if tender.get('matching_courses'):
            score += len(tender['matching_courses']) * 2
        
        # Determine priority
        if score >= 8:
            return 'high'
        elif score >= 5:
            return 'medium'
        else:
            return 'low'

class ProcurementScanner:
    """Main procurement scanner class"""
    
    def __init__(self):
        self.selenium = selenium_manager
    
    async def get_driver(self):
        """Get Selenium WebDriver with health checks"""
        return self.selenium.create_driver()
    
    async def scan_canadabuys(self) -> list[Dict]:
        """Scan CanadaBuys portal via API"""
        tenders = []
        
        try:
            logger.info("Scanning CanadaBuys via API...")
            
            # CanadaBuys API endpoints
            endpoints = [
                "https://canadabuys.canada.ca/api/v1/opportunities",
                "https://canadabuys.canada.ca/api/v1/contracts"
            ]
            
            async with aiohttp.ClientSession() as session:
                for endpoint in endpoints:
                    try:
                        async with session.get(endpoint) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                for item in data.get('opportunities', [])[:100]:  # Limit results
                                    tender_data = self._parse_canadabuys_item(item, endpoint)
                                    if tender_data:
                                        tenders.append(tender_data)
                                        
                    except Exception as e:
                        logger.error(f"Error fetching from {endpoint}: {e}")
                        continue
            
            logger.info(f"Found {len(tenders)} tenders from CanadaBuys")
                                
        except Exception as e:
            logger.error(f"Error scanning CanadaBuys: {e}")
            
        return tenders
    
    def _parse_canadabuys_item(self, item: Dict, endpoint_type: str) -> Optional[Dict]:
        """Parse CanadaBuys API item"""
        try:
            tender_id = item.get('id', '')
            title = item.get('title', '')
            organization = item.get('organization', {}).get('name', 'Government of Canada')
            
            # Parse dates
            closing_date = None
            if item.get('closing_date'):
                try:
                    closing_date = datetime.fromisoformat(item['closing_date'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    pass
            
            # Parse value
            value = 0.0
            if item.get('estimated_value'):
                try:
                    value = float(item['estimated_value'])
                except (ValueError, TypeError):
                    pass
            
            return {
                'tender_id': f"CB_{tender_id}",
                'title': title,
                'organization': organization,
                'portal': 'CanadaBuys',
                'portal_url': 'https://canadabuys.canada.ca',
                'value': value,
                'closing_date': closing_date,
                'posted_date': datetime.utcnow(),
                'description': item.get('description', ''),
                'location': item.get('location', ''),
                'categories': [],
                'keywords': [],
                'tender_url': item.get('url', ''),
                'documents_url': item.get('documents_url', ''),
                'is_active': True
            }
            
        except Exception as e:
            logger.warning(f"Error parsing CanadaBuys item: {e}")
            return None
    
    async def scan_merx(self) -> list[Dict]:
        """Scan MERX portal for training tenders"""
        final_tenders: list[Dict] = []
        tenders: list[Dict] = []
        driver = None
        
        try:
            driver = await self.get_driver()
            if not driver:
                logger.error("Could not get driver for MERX")
                return final_tenders
            
            logger.info("Scanning MERX portal for training tenders...")
            
            # Navigate to MERX open solicitations page (more reliable than search)
            base_url = "https://www.merx.com/public/solicitations/open?"
            if not self.selenium.stealth_navigation(driver, base_url):
                logger.error("Failed to navigate to MERX open solicitations page")
                return final_tenders
            
            # Handle cookie consent if present
            try:
                cookie_button = driver.find_element(By.CSS_SELECTOR, ".cookie-consent-buttons button, .accept-cookies, .cookie-accept")
                if cookie_button:
                    cookie_button.click()
                    await asyncio.sleep(2)
                    logger.info("Accepted cookies")
            except Exception:
                pass  # No cookie banner found
            
            # Training-related keywords to filter for (focus on services, not equipment/supplies)
            training_keywords = [
                # Core training and education services
                "training", "education", "professional development", "learning",
                "workshop", "seminar", "course", "curriculum", "instruction",
                "teaching", "facilitation", "mentoring", "coaching", "certification",
                "accreditation", "workshop", "conference", "symposium", "webinar",
                "e-learning", "online learning", "distance learning", "virtual training",
                
                # Educational services and programs
                "educational services", "training program", "learning program",
                "professional training", "skill development", "capacity building",
                "leadership development", "management training", "technical training",
                "safety training", "compliance training", "regulatory training",
                
                # Education institutions (services they provide)
                "school board", "school district", "university", "college", "academy",
                "institute", "campus", "academic services", "educational consulting",
                "curriculum development", "instructional design", "assessment",
                "evaluation", "accreditation", "certification program",
                
                # Government education services
                "ministry of education", "department of education", "education authority",
                "public education", "post-secondary", "higher education",
                "continuing education", "adult education", "vocational training",
                "apprenticeship", "skills training", "workforce development",
                
                # Training delivery methods
                "instructor", "trainer", "facilitator", "consultant", "coach",
                "mentor", "tutor", "educator", "teacher", "professor",
                "presenter", "speaker", "moderator", "coordinator"
            ]
            
            # Keywords to EXCLUDE (equipment, supplies, physical materials)
            exclude_keywords = [
                "equipment", "supplies", "materials", "furniture", "textbooks",
                "books", "computers", "software", "hardware", "devices",
                "instruments", "tools", "machinery", "vehicles", "construction",
                "building", "maintenance", "repair", "installation", "purchase",
                "procurement", "acquisition", "buy", "purchase", "lease",
                "rental", "equipment rental", "supply contract", "materials contract"
            ]
            
            # Process multiple pages to find training tenders
            max_pages = 50  # Increased from 10 to 50 to get more results
            page_tenders = []
            
            for page_num in range(1, max_pages + 1):
                try:
                    logger.info(f"Processing MERX page {page_num}")
                    
                    # Wait for page to load
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "table, .results, .solicitation-item, tr"))
                    )
                    
                    # Find tender elements on current page
                    tender_elements = []
                    selectors = [
                        "tr[data-solicitation-id]",  # Table rows with solicitation data
                        ".solicitation-item",         # Solicitation items
                        ".opportunity-item",          # Opportunity items
                        "tr:has(td)",                 # Table rows with cells
                        ".result-item",               # Result items
                        "a[href*='/solicitations/']", # Solicitation links
                        "tr"                          # Any table row as fallback
                    ]
                    
                    for selector in selectors:
                        elements = self.selenium.find_elements_safe(driver, By.CSS_SELECTOR, selector, timeout=5)  # type: ignore[arg-type]
                        if elements:
                            tender_elements = elements
                            logger.info(f"Found {len(elements)} elements using selector: {selector}")
                            break
                    
                    # Parse tenders on current page and filter for training content
                    page_count = 0
                    training_count = 0
                    
                    for element in tender_elements:
                        try:
                            tender_data = self._parse_merx_opportunity(element)
                            if tender_data:
                                page_count += 1
                                
                                # Check if this tender is training-related
                                title_lower = tender_data['title'].lower()
                                description_lower = tender_data.get('description', '').lower()
                                
                                # First check if it contains training keywords
                                is_training = any(keyword in title_lower or keyword in description_lower 
                                                 for keyword in training_keywords)
                                
                                # Then check if it should be excluded (equipment/supplies)
                                should_exclude = any(exclude_keyword in title_lower or exclude_keyword in description_lower 
                                                    for exclude_keyword in exclude_keywords)
                                
                                if is_training and not should_exclude:
                                    # Add training keywords to the tender
                                    found_keywords = [kw for kw in training_keywords 
                                                     if kw in title_lower or kw in description_lower]
                                    tender_data['keywords'] = found_keywords
                                    tender_data['categories'] = ['Training', 'Education', 'Professional Development']
                                    page_tenders.append(tender_data)
                                    training_count += 1
                                    
                        except Exception as e:
                            logger.warning(f"Error parsing MERX opportunity: {e}")
                            continue
                    
                    logger.info(f"Page {page_num}: Found {page_count} total tenders, {training_count} training-related")
                    
                    # If we found no tenders on this page, we might be at the end
                    if page_count == 0:
                        logger.info("No tenders found on this page, stopping pagination")
                        break
                    
                    # Try to go to next page
                    if page_num < max_pages:
                        next_button = self.selenium.find_element_safe(
                            driver, By.CSS_SELECTOR,  # type: ignore[arg-type]
                            "a[rel='next'], .next, .pagination-next"
                        )
                        
                        if next_button and next_button.is_enabled():
                            next_button.click()
                            # Wait for page transition
                            await asyncio.sleep(3)
                        else:
                            # Try alternative pagination methods
                            try:
                                # Look for page number links
                                next_page_link = driver.find_element(By.CSS_SELECTOR, f"a[href*='page={page_num + 1}'], a[href*='p={page_num + 1}']")
                                if next_page_link:
                                    next_page_link.click()
                                    await asyncio.sleep(3)
                                    continue
                            except Exception:
                                pass
                            
                            logger.info("No more pages available")
                        break
                    else:
                        logger.info(f"Reached max pages ({max_pages})")
                    break
                        
                except Exception as e:
                    logger.warning(f"Error processing page {page_num}: {e}")
                    break
            
            # Remove duplicates based on tender_id
            unique_tenders = {}
            for tender in page_tenders:
                unique_tenders[tender['tender_id']] = tender
            
            final_tenders = list(unique_tenders.values())
            logger.info(f"Found {len(final_tenders)} unique training tenders from MERX")
                    
        except Exception as e:
            logger.error(f"Error scanning MERX: {e}")
        finally:
            self.selenium.safe_quit_driver(driver)
        
        return final_tenders
    
    def _parse_merx_opportunity(self, element) -> Optional[Dict]:
        """Parse MERX opportunity element with enhanced data extraction"""
        try:
            # Try to extract title from various possible locations
            title = ""
            title_selectors = [
                "a", "h3", "h4", ".title", ".solicitation-title", 
                "td:nth-child(1)", "td:nth-child(2)", ".result-title"
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title:
                        break
                except Exception:
                    continue
            
            if not title:
                # Fallback: get text from the element itself
                title = element.text.strip()[:100]  # First 100 chars
            
            # Skip if title is too short or empty
            if len(title) < 5:
                return None
    
            # Extract organization
            organization = "MERX"
            org_selectors = [".organization", ".org", "td:nth-child(3)", ".result-org"]
            for selector in org_selectors:
                try:
                    org_elem = element.find_element(By.CSS_SELECTOR, selector)
                    org_text = org_elem.text.strip()
                    if org_text:
                        organization = org_text
                        break
                except Exception:
                    continue
            
            # Extract URL
            tender_url = ""
            try:
                link = element.find_element(By.CSS_SELECTOR, "a")
                tender_url = link.get_attribute("href")
            except:
                # If no link found, construct a base URL
                tender_url = "https://www.merx.com/public/solicitations/open?"
            
            # Extract additional data if available
            location = ""
            try:
                location_elem = element.find_element(By.CSS_SELECTOR, ".location, td:nth-child(4)")
                location = location_elem.text.strip()
            except:
                pass
            
            # Extract closing date if available
            closing_date = None
            try:
                date_elem = element.find_element(By.CSS_SELECTOR, ".closing-date, .date, td:nth-child(5)")
                date_text = date_elem.text.strip()
                if date_text:
                    # Try to parse the date
                    try:
                        closing_date = datetime.strptime(date_text, "%Y/%m/%d")
                    except:
                        pass
            except:
                pass
            
            # Generate unique ID
            tender_id = f"MERX_{hashlib.md5((title + tender_url).encode()).hexdigest()[:8]}"
            
            return {
                'tender_id': tender_id,
                'title': title,
                'organization': organization,
                'portal': 'MERX',
                'portal_url': 'https://www.merx.com',
                'value': 0.0,
                'closing_date': closing_date,
                'posted_date': datetime.utcnow(),
                'description': f"Tender from MERX portal",
                'location': location,
                'categories': [],
                'keywords': [],
                'tender_url': tender_url,
                'documents_url': tender_url,
                'is_active': True
            }
            
        except Exception as e:
            logger.warning(f"Error parsing MERX opportunity: {e}")
            return None
    
    async def scan_bcbid(self) -> list[Dict]:
        """Scan BC Bid portal"""
        tenders: list[Dict] = []
        driver = None
        
        try:
            driver = await self.get_driver()
            if not driver:
                logger.error("Could not get driver for BC Bid")
                return tenders
            
            logger.info("Scanning BC Bid portal...")
            
            if not self.selenium.stealth_navigation(driver, "https://www.bcbid.gov.bc.ca"):
                logger.error("Failed to navigate to BC Bid")
                return tenders
            
            # Find opportunities
            opportunity_elements = self.selenium.find_elements_safe(
                driver, By.CSS_SELECTOR, ".opportunity, .tender-item"  # type: ignore[arg-type]
            )
            
            for element in opportunity_elements[:50]:
                try:
                    tender_data = self._parse_bcbid_opportunity(element)
                    if tender_data:
                        tenders.append(tender_data)
                except Exception as e:
                    logger.warning(f"Error parsing BC Bid opportunity: {e}")
                    continue
            
            logger.info(f"Found {len(tenders)} tenders from BC Bid")
                        
        except Exception as e:
            logger.error(f"Error scanning BC Bid: {e}")
        finally:
            self.selenium.safe_quit_driver(driver)
                
        return tenders
    
    def _parse_bcbid_opportunity(self, element) -> Optional[Dict]:
        """Parse BC Bid opportunity element"""
        try:
            title = element.find_element(By.CSS_SELECTOR, ".title, h3").text.strip()
            organization = "BC Government"
            
            link = element.find_element(By.CSS_SELECTOR, "a")
            tender_url = link.get_attribute("href")
            
            tender_id = f"BCBID_{hashlib.md5((title + tender_url).encode()).hexdigest()[:8]}"
            
            return {
                'tender_id': tender_id,
                'title': title,
                'organization': organization,
                'portal': 'BC Bid',
                'portal_url': 'https://www.bcbid.gov.bc.ca',
                'value': 0.0,
                'closing_date': None,
                'posted_date': datetime.utcnow(),
                'description': '',
                'location': 'British Columbia',
                'categories': [],
                'keywords': [],
                'tender_url': tender_url,
                'documents_url': tender_url,
                'is_active': True
            }
            
        except Exception as e:
            logger.warning(f"Error parsing BC Bid opportunity: {e}")
            return None
    
    async def scan_seao_web(self) -> list[Dict]:
        """Scan SEAO Quebec web portal"""
        tenders: list[Dict] = []
        driver = None
        
        try:
            driver = await self.get_driver()
            if not driver:
                logger.error("Could not get driver for SEAO")
                return tenders
            
            logger.info("Scanning SEAO Quebec web portal...")
            
            if not self.selenium.stealth_navigation(driver, "https://seao.gouv.qc.ca"):
                logger.error("Failed to navigate to SEAO")
                return tenders
            
            opportunity_elements = self.selenium.find_elements_safe(
                driver, By.CSS_SELECTOR, ".opportunity, .appel-item"  # type: ignore[arg-type]
            )
            
            for element in opportunity_elements[:50]:
                try:
                    tender_data = self._parse_seao_opportunity(element)
                    if tender_data:
                        tenders.append(tender_data)
                except Exception as e:
                    logger.warning(f"Error parsing SEAO opportunity: {e}")
                    continue
            
            logger.info(f"Found {len(tenders)} tenders from SEAO")
                    
        except Exception as e:
            logger.error(f"Error scanning SEAO: {e}")
        finally:
            self.selenium.safe_quit_driver(driver)
                
        return tenders
    
    def _parse_seao_opportunity(self, element) -> Optional[Dict]:
        """Parse SEAO opportunity element"""
        try:
            title = element.find_element(By.CSS_SELECTOR, ".title, h3").text.strip()
            organization = "Quebec Government"
            
            link = element.find_element(By.CSS_SELECTOR, "a")
            tender_url = link.get_attribute("href")
            
            tender_id = f"SEAO_{hashlib.md5((title + tender_url).encode()).hexdigest()[:8]}"
            
            return {
                'tender_id': tender_id,
                'title': title,
                'organization': organization,
                'portal': 'SEAO Quebec',
                'portal_url': 'https://seao.gouv.qc.ca',
                'value': 0.0,
                'closing_date': None,
                'posted_date': datetime.utcnow(),
                'description': '',
                'location': 'Quebec',
                'categories': [],
                'keywords': [],
                'tender_url': tender_url,
                'documents_url': tender_url,
                'is_active': True
            }
            
        except Exception as e:
            logger.warning(f"Error parsing SEAO opportunity: {e}")
            return None
    
    async def scan_seao_api(self) -> list[Dict]:
        """Scan SEAO Quebec API"""
        tenders: list[Dict] = []
        
        try:
            logger.info("Scanning SEAO Quebec API...")
            
            # SEAO API endpoint
            api_url = "https://seao.gouv.qc.ca/api/opportunities"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data.get('opportunities', [])[:50]:
                            tender_data = self._parse_seao_api_item(item)
                            if tender_data:
                                tenders.append(tender_data)
                    else:
                        logger.warning("SEAO API endpoints are not working, skipping API scan")
                                        
            logger.info(f"Found {len(tenders)} tenders from SEAO API")
                    
        except Exception as e:
            logger.error(f"Error scanning SEAO API: {e}")
            
        return tenders
    
    def _parse_seao_api_item(self, item: Dict) -> Optional[Dict]:
        """Parse SEAO API item"""
        try:
            tender_id = item.get('id', '')
            title = item.get('title', '')
            
            return {
                'tender_id': f"SEAO_API_{tender_id}",
                'title': title,
                'organization': 'Quebec Government',
                'portal': 'SEAO Quebec',
                'portal_url': 'https://seao.gouv.qc.ca',
                'value': 0.0,
                'closing_date': None,
                'posted_date': datetime.utcnow(),
                'description': item.get('description', ''),
                'location': 'Quebec',
                'categories': [],
                'keywords': [],
                'tender_url': item.get('url', ''),
                'documents_url': item.get('url', ''),
                'is_active': True
            }
            
        except Exception as e:
            logger.warning(f"Error parsing SEAO API item: {e}")
            return None
    
    async def scan_biddingo(self, portal_name: str, config: Dict) -> list[Dict]:
        """Scan Biddingo portal"""
        tenders: list[Dict] = []
        driver = None
        
        try:
            driver = await self.get_driver()
            if not driver:
                logger.error(f"Could not get driver for {portal_name}")
                return tenders
            
            logger.info(f"Scanning {portal_name}...")
            
            search_url = config.get('search_url', 'https://www.biddingo.com/')
            if not self.selenium.stealth_navigation(driver, search_url):
                logger.error(f"Failed to navigate to {portal_name}")
                return tenders
            
            opportunity_elements = self.selenium.find_elements_safe(
                driver, By.CSS_SELECTOR, ".opportunity, .bid-item"  # type: ignore[arg-type]
            )
            
            for element in opportunity_elements[:50]:
                try:
                    tender_data = self._parse_biddingo_opportunity(element, portal_name)
                    if tender_data:
                        tenders.append(tender_data)
                except Exception as e:
                    logger.warning(f"Error parsing {portal_name} opportunity: {e}")
                    continue
            
            logger.info(f"Found {len(tenders)} tenders from {portal_name}")
                    
        except Exception as e:
            logger.error(f"Error scanning {portal_name}: {e}")
        finally:
            self.selenium.safe_quit_driver(driver)
                
        return tenders
    
    def _parse_biddingo_opportunity(self, element, portal_name: str) -> Optional[Dict]:
        """Parse Biddingo opportunity element"""
        try:
            title = element.find_element(By.CSS_SELECTOR, ".title, h3").text.strip()
            
            link = element.find_element(By.CSS_SELECTOR, "a")
            tender_url = link.get_attribute("href")
            
            tender_id = f"BIDDINGO_{hashlib.md5((title + tender_url).encode()).hexdigest()[:8]}"
            
            return {
                'tender_id': tender_id,
                'title': title,
                'organization': portal_name,
                'portal': portal_name,
                'portal_url': 'https://www.biddingo.com',
                'value': 0.0,
                'closing_date': None,
                'posted_date': datetime.utcnow(),
                'description': '',
                'location': '',
                'categories': [],
                'keywords': [],
                'tender_url': tender_url,
                'documents_url': tender_url,
                'is_active': True
            }
            
        except Exception as e:
            logger.warning(f"Error parsing Biddingo opportunity: {e}")
            return None

    async def scan_bidsandtenders_portal(self, portal_name: str, search_url: str) -> list[Dict]:
        """Scan Bids&Tenders portal"""
        tenders: list[Dict] = []
        driver = None
        
        try:
            driver = await self.get_driver()
            if not driver:
                logger.error(f"Could not get driver for {portal_name}")
                return tenders
            
            logger.info(f"Scanning {portal_name}...")
            
            if not self.selenium.stealth_navigation(driver, search_url):
                logger.error(f"Failed to navigate to {portal_name}")
                return tenders
            
            opportunity_elements = self.selenium.find_elements_safe(
                driver, By.CSS_SELECTOR, ".opportunity, .bid-item"  # type: ignore[arg-type]
            )
            
            for element in opportunity_elements[:50]:
                try:
                    tender_data = self._parse_bidsandtenders_opportunity(element, portal_name)
                    if tender_data:
                        tenders.append(tender_data)
                except Exception as e:
                    logger.warning(f"Error parsing {portal_name} opportunity: {e}")
                    continue
            
            logger.info(f"Found {len(tenders)} tenders from {portal_name}")
            
        except Exception as e:
            logger.error(f"Error scanning {portal_name}: {e}")
        finally:
            self.selenium.safe_quit_driver(driver)
        
        return tenders
    
    def _parse_bidsandtenders_opportunity(self, element, portal_name: str) -> Optional[Dict]:
        """Parse Bids&Tenders opportunity element"""
        try:
            title = element.find_element(By.CSS_SELECTOR, ".title, h3").text.strip()
            
            link = element.find_element(By.CSS_SELECTOR, "a")
            tender_url = link.get_attribute("href")
            
            tender_id = f"BIDS_{hashlib.md5((title + tender_url).encode()).hexdigest()[:8]}"
            
            return {
                'tender_id': tender_id,
                'title': title,
                'organization': portal_name,
                'portal': portal_name,
                'portal_url': 'https://www.bidsandtenders.ca',
                'value': 0.0,
                'closing_date': None,
                'posted_date': datetime.utcnow(),
                'description': '',
                'location': '',
                'categories': [],
                'keywords': [],
                'tender_url': tender_url,
                'documents_url': tender_url,
                'is_active': True
            }
        
        except Exception as e:
            logger.warning(f"Error parsing Bids&Tenders opportunity: {e}")
            return None

# FastAPI app setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting procurement scanner...")
    
    # Wait for Selenium Grid to be ready
    if not selenium_manager.wait_for_grid_ready():
        logger.error("Selenium Grid failed to start, but continuing...")
    
    yield
    
    # Shutdown
    logger.info("Shutting down procurement scanner...")

app = FastAPI(lifespan=lifespan)  # type: ignore

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API endpoints
@app.get("/api/tenders")
async def get_tenders(
    skip: int = 0,
    limit: int = 100,
    portal: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get tenders with optional filtering"""
    query = db.query(Tender)
    
    # Only add portal filter if portal is not None
    if portal is not None:
        query = query.filter(Tender.portal == portal)
    query = query.filter(Tender.is_active.is_(True))
    query = query.order_by(desc(Tender.posted_date))
    
    total = query.count()
    tenders = list(query.offset(skip).limit(limit).all())
    
    return {
        "tenders": [
            {
                "id": t.id,
                "tender_id": t.tender_id,
                "title": t.title,
                "organization": t.organization,
                "portal": t.portal,
                "value": t.value,
                "closing_date": t.closing_date,
                "posted_date": t.posted_date,
                "description": t.description,
                "location": t.location,
                "categories": json.loads(str(t.categories)) if t.categories is not None else [],  # type: ignore[arg-type]
                "keywords": json.loads(str(t.keywords)) if t.keywords is not None else [],  # type: ignore[arg-type]
                "tender_url": t.tender_url,
                "matching_courses": json.loads(str(t.matching_courses)) if t.matching_courses is not None else [],  # type: ignore[arg-type]
                "priority": t.priority
            }
            for t in tenders
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@app.get("/api/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """Get system statistics"""
    total_tenders = db.query(Tender).filter(Tender.is_active.is_(True)).count()
    total_value = db.query(func.sum(Tender.value)).filter(Tender.is_active.is_(True)).scalar() or 0
    
    # Portal breakdown
    portal_stats = db.query(  # type: ignore[attr-defined]
        Tender.portal,  # type: ignore[arg-type]
        func.count(Tender.id).label('count'),
        func.sum(Tender.value).label('total_value')
    ).filter(Tender.is_active.is_(True)).group_by(Tender.portal).all()
    
    by_portal: list[Dict] = [
        {
            "portal": stat.portal,
            "count": stat.count,
            "total_value": float(stat.total_value or 0)
        }
        for stat in portal_stats
    ]
    
    # Closing soon (next 7 days)
    closing_soon = db.query(Tender).filter(
        Tender.closing_date.isnot(None),  # type: ignore[attr-defined]
        Tender.closing_date >= datetime.utcnow(),  # type: ignore[arg-type]
        Tender.closing_date <= datetime.utcnow() + timedelta(days=7),  # type: ignore[arg-type]
        Tender.is_active.is_(True)
    ).count()
    
    # New today
    today = datetime.utcnow().date()
    new_today = db.query(Tender).filter(
        Tender.posted_date.isnot(None),  # type: ignore[attr-defined]
        func.date(Tender.posted_date) == today,
        Tender.is_active.is_(True)
    ).count()
    
    return {
        "total_tenders": total_tenders,
        "total_value": float(total_value),
        "by_portal": by_portal,
        "closing_soon": closing_soon,
        "new_today": new_today,
        "last_scan": datetime.utcnow()
    }

@app.post("/api/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger a manual scan of all portals"""
    background_tasks.add_task(scan_all_portals)
    return {"message": "Scan initiated"}

async def scan_all_portals():
    """Scan all portals and save results"""
    scanner = ProcurementScanner()
    matcher = TenderMatcher()
    
    # Get all portal IDs from PORTAL_CONFIGS
    portal_ids = list(PORTAL_CONFIGS.keys())
    
    total_found = 0
    new_tenders = 0
    updated_tenders = 0
    
    # Scan all configured portals
    for portal_id in portal_ids:
        try:
            config = PORTAL_CONFIGS[portal_id]
            logger.info(f"Scanning {config['name']} ({portal_id})...")
            
            # Get the appropriate scan method based on portal type
            if config['type'] == 'api':
                # API-based portals
                if portal_id == 'canadabuys':
                    tenders = await scanner.scan_canadabuys()
                else:
                    logger.warning(f"No API scanner implemented for {portal_id}")
                    continue
            elif config['type'] == 'web':
                # Web-based portals
                if portal_id == 'merx':
                    tenders = await scanner.scan_merx()
                elif portal_id == 'bcbid':
                    tenders = await scanner.scan_bcbid()
                elif portal_id == 'seao':
                    tenders = await scanner.scan_seao_web()
                elif portal_id == 'biddingo':
                    tenders = await scanner.scan_biddingo(config['name'], config)
                else:
                    logger.warning(f"No web scanner implemented for {portal_id}")
                    continue
            elif config['type'] == 'bidsandtenders':
                # Bids&Tenders platform portals
                search_url = config.get('search_url', 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all')
                tenders = await scanner.scan_bidsandtenders_portal(config['name'], search_url)
            else:
                logger.warning(f"Unknown portal type '{config['type']}' for {portal_id}")
                continue
            
            if tenders and isinstance(tenders, list):
                # Process tenders
                db = SessionLocal()
                try:
                    for tender_data in tenders:
                        tender_data['matching_courses'] = matcher.match_courses(tender_data)
                        tender_data['priority'] = matcher.calculate_priority(tender_data)
                        
                        was_new = save_tender_to_db(db, tender_data)
                        if was_new:
                            new_tenders += 1
                        else:
                            updated_tenders += 1
                    
                    total_found += len(tenders)
                    logger.info(f"Processed {len(tenders)} tenders from {config['name']}")
                    
                finally:
                    db.close()
            else:
                logger.info(f"No tenders found from {config['name']}")
    
        except Exception as e:
            logger.error(f"Error scanning {portal_id}: {e}")
    
    logger.info(f"Scan complete. Found {total_found} tenders. New: {new_tenders}, Updated: {updated_tenders}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)