# main.py - Main application with FastAPI
# type: ignore[reportUnknownVariableType, attr-defined, arg-type, reportAttributeAccessIssue]
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import json
import hashlib
import aiohttp
from selenium.webdriver.common.keys import Keys
import os

# FastAPI imports
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Database imports
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

# Selenium imports
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import from our modules
from models import Base, SessionLocal, Tender, save_tender_to_db, get_db  # type: ignore[reportAny]

# Import from selenium_utils module
from selenium_utils import SeleniumGridManager

from config import PORTAL_CONFIGS, TKA_COURSES
from matcher import TenderMatcher

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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=SessionLocal().bind)  # type: ignore[reportAny]

# Advanced search strategies for TKA business optimization
SEARCH_STRATEGIES = {
    'primary_keywords': [
        # Direct training terms - highest priority
        'training services', 'professional development services', 'education services',
        'learning development', 'skill development', 'capacity building',
        'workforce development', 'upskilling', 'reskilling',
        
        # Consulting with training components
        'consulting services', 'advisory services', 'implementation services',
        'change management', 'digital transformation', 'modernization',
        'process improvement', 'organizational development'
    ],
    
    'technical_skills': [
        # Cloud & DevOps - high demand
        'AWS training', 'Azure training', 'Google Cloud training', 'cloud migration',
        'DevOps training', 'Kubernetes training', 'Docker training', 'CI/CD training',
        
        # Cybersecurity - critical need
        'cybersecurity training', 'information security training', 'CISSP training',
        'ethical hacking training', 'security assessment', 'compliance training',
        
        # Data & Analytics - growing demand
        'data analytics training', 'business intelligence training', 'Power BI training',
        'Tableau training', 'data science training', 'machine learning training',
        
        # IT Infrastructure - foundational
        'ITIL training', 'IT service management', 'network security training',
        'system administration training', 'database management training'
    ],
    
    'management_skills': [
        # Project Management - core TKA offering
        'project management training', 'PMP training', 'PRINCE2 training', 
        'Agile training', 'Scrum training', 'program management training',
        
        # Leadership - executive focus
        'leadership development', 'management training', 'executive coaching',
        'team building training', 'organizational development',
        
        # Change Management - transformation focus
        'change management training', 'organizational change', 'transformation training',
        'process improvement training', 'lean six sigma training'
    ],
    
    'soft_skills': [
        # Communication - essential for all roles
        'communication skills training', 'presentation skills training', 
        'negotiation training', 'conflict resolution training',
        'emotional intelligence training', 'coaching training',
        'facilitation training', 'customer service training', 'sales training'
    ],
    
    'compliance_governance': [
        # Compliance - regulatory requirement
        'compliance training', 'regulatory compliance training', 'GDPR training',
        'risk management training', 'audit training', 'governance training',
        'ethics training', 'anti-money laundering training', 'privacy training'
    ]
}

def generate_search_queries():
    """Generate multiple search queries for comprehensive coverage"""
    
    # Strategy 1: Comprehensive training services search
    comprehensive_training = [
        # CanadaBuys: Multiple keywords in quotes
        '"training services" "professional development" "upskilling"',
        '"education services" "learning development" "skill development"',
        '"consulting services" "capacity building" "workforce development"',
        
        # MERX: Multiple keywords with AND
        'training AND services AND professional AND development',
        'education AND services AND learning AND development',
        'consulting AND services AND capacity AND building'
    ]
    
    # Strategy 2: Technology-focused comprehensive search
    tech_comprehensive = [
        # CanadaBuys: Tech training combinations
        '"cloud training" "AWS training" "Azure training" "cybersecurity training"',
        '"DevOps training" "data analytics training" "ITIL training"',
        '"project management training" "Agile training" "Scrum training"',
        
        # MERX: Tech training with AND
        'cloud AND training AND AWS AND Azure AND cybersecurity',
        'DevOps AND training AND data AND analytics AND ITIL',
        'project AND management AND training AND Agile AND Scrum'
    ]
    
    # Strategy 3: Implementation and transformation search
    implementation_comprehensive = [
        # CanadaBuys: Implementation combinations
        '"digital transformation consulting" "change management implementation"',
        '"system implementation training" "process improvement consulting"',
        '"organizational development" "transformation services"',
        
        # MERX: Implementation with AND
        'digital AND transformation AND consulting AND change AND management',
        'system AND implementation AND training AND process AND improvement',
        'organizational AND development AND transformation AND services'
    ]
    
    # Strategy 4: Certification and professional development
    certification_comprehensive = [
        # CanadaBuys: Certification combinations
        '"certification preparation" "professional certification" "PMP certification"',
        '"PRINCE2 certification" "CISSP training" "ITIL certification"',
        '"AWS certification" "Azure certification" "professional development"',
        
        # MERX: Certification with AND
        'certification AND preparation AND professional AND PMP',
        'PRINCE2 AND certification AND CISSP AND training AND ITIL',
        'AWS AND certification AND Azure AND professional AND development'
    ]
    
    # Strategy 5: Leadership and organizational development
    leadership_comprehensive = [
        # CanadaBuys: Leadership combinations
        '"leadership development program" "executive coaching services"',
        '"management development" "team effectiveness training"',
        '"change management training" "organizational development"',
        
        # MERX: Leadership with AND
        'leadership AND development AND program AND executive AND coaching',
        'management AND development AND team AND effectiveness AND training',
        'change AND management AND training AND organizational AND development'
    ]
    
    return {
        'comprehensive_training': comprehensive_training,
        'tech_comprehensive': tech_comprehensive,
        'implementation_comprehensive': implementation_comprehensive,
        'certification_comprehensive': certification_comprehensive,
        'leadership_comprehensive': leadership_comprehensive
    }

def format_search_query_for_portal(query: str, portal: str) -> str:
    """Format search query appropriately for each portal"""
    if portal.lower() == 'canadabuys':
        # CanadaBuys: Already formatted with quotes, return as-is
        return query
    elif portal.lower() == 'merx':
        # MERX: Already formatted with AND, return as-is
        return query
    else:
        # Default: return as-is
        return query

def score_tender_relevance(tender_data):
    """Score tender relevance based on multiple factors"""
    score = 0
    title = tender_data.get('title', '').lower()
    description = tender_data.get('description', '').lower()
    text = f"{title} {description}"
    
    # High-value keywords (worth more points)
    high_value_terms = {
        'training': 15, 'professional development': 20, 'certification': 15,
        'consulting': 10, 'implementation': 8, 'change management': 12,
        'AWS': 15, 'Azure': 15, 'cybersecurity': 15, 'project management': 15,
        'agile': 12, 'scrum': 12, 'leadership': 10, 'coaching': 10
    }
    
    # Medium-value keywords
    medium_value_terms = {
        'education': 8, 'learning': 8, 'development': 5, 'skills': 5,
        'workshop': 8, 'seminar': 8, 'course': 8, 'program': 5
    }
    
    # Negative indicators (reduce score)
    negative_terms = {
        'equipment': -10, 'construction': -15, 'manufacturing': -10,
        'supplies': -8, 'maintenance': -8, 'physical': -5
    }
    
    # Calculate score
    for term, value in {**high_value_terms, **medium_value_terms, **negative_terms}.items():
        if term in text:
            score += value
    
    # Bonus for multiple relevant terms
    relevant_count = sum(1 for term in high_value_terms if term in text)
    if relevant_count >= 2:
        score += 10
    
    # Value-based scoring
    tender_value = tender_data.get('value', 0)
    if 50000 <= tender_value <= 2000000:  # Sweet spot for training contracts
        score += 5
    
    return max(score, 0)

def deduplicate_tenders(tenders):
    """Remove duplicate tenders based on tender_id"""
    seen_ids = set()
    unique_tenders = []
    for tender in tenders:
        tender_id = tender.get('tender_id', '')
        if tender_id and tender_id not in seen_ids:
            seen_ids.add(tender_id)
            unique_tenders.append(tender)
    return unique_tenders

class ProcurementScanner:
    """Main procurement scanner class"""
    
    def __init__(self):
        """Initialize scanner with enhanced scrapers"""
        self.db = SessionLocal()
        self.selenium = SeleniumGridManager()
        
        # Get MERX login credentials from environment variables
        merx_username = os.getenv('MERX_USERNAME')
        merx_password = os.getenv('MERX_PASSWORD')
        
        # Initialize portal scanners
        self.portals = {
            'MERX': MERXScraper(username=os.getenv('MERX_USERNAME'), password=os.getenv('MERX_PASSWORD')),
            'CanadaBuys': CanadaBuysScraper(),
            'BCBid': None,  # Handled by specific scan method
            'SEAO': None,   # Handled by specific scan method
            'Biddingo': None,  # Handled by specific scan method
            'BidsAndTenders': None,  # Handled by specific scan method
        }
        
        logger.info(f"Initialized scanner with {len(self.portals)} portal configurations")
        if merx_username:
            logger.info("MERX login credentials provided")
        else:
            logger.info("No MERX login credentials provided - will use public access")
    
    async def get_driver(self):
        """Get Selenium WebDriver with health checks"""
        return self.selenium.create_driver()
    
    async def scan_canadabuys(self) -> list[Dict]:
        """Scan CanadaBuys portal via web scraping with multiple search strategies"""
        tenders = []
        driver = None
        
        try:
            logger.info("Scanning CanadaBuys via web scraping...")
            
            driver = await self.get_driver()
            if not driver:
                logger.error("Could not get driver for CanadaBuys")
                return tenders
            
            # Comprehensive search strategies to find many more tenders
            search_strategies = [
                {"term": "training", "description": "Training services"},
                {"term": "education", "description": "Education services"},
                {"term": "consulting", "description": "Consulting services"},
                {"term": "professional development", "description": "Professional development"},
                {"term": "workshop", "description": "Workshop services"},
                {"term": "services", "description": "General services"},
                {"term": "advisory", "description": "Advisory services"},
                {"term": "implementation", "description": "Implementation services"},
                {"term": "support", "description": "Support services"},
                {"term": "facilitation", "description": "Facilitation services"},
                {"term": "coaching", "description": "Coaching services"},
                {"term": "development", "description": "Development services"},
                {"term": "management", "description": "Management services"},
                {"term": "project", "description": "Project services"},
                {"term": "technical", "description": "Technical services"},
                {"term": "", "description": "All opportunities"}  # No search term to get all
            ]
            
            for strategy in search_strategies:
                try:
                    logger.info(f"CanadaBuys search strategy: {strategy['description']}")
                    
                    # Navigate to CanadaBuys tender opportunities page
                    base_url = "https://canadabuys.canada.ca/en/tender-opportunities"
                    if not self.selenium.stealth_navigation(driver, base_url):
                        logger.error("Failed to navigate to CanadaBuys tender opportunities page")
                        continue
                    
                    # Wait for page to load
                    await asyncio.sleep(5)
                    
                    # Try to interact with the search form to get results
                    if strategy['term']:
                        try:
                            # Look for search input and submit button
                            search_input = self.selenium.find_element_safe(driver, By.CSS_SELECTOR, "input[name='keys'], input[placeholder*='Search'], input[type='text']", timeout=10)
                            if search_input:
                                # Enter a search term to get results
                                search_input.clear()
                                search_input.send_keys(strategy['term'])
                                
                                # Find and click submit button
                                submit_button = self.selenium.find_element_safe(driver, By.CSS_SELECTOR, "input[type='submit'], button[type='submit'], .form-submit, button[class*='search']", timeout=5)
                                if submit_button:
                                    submit_button.click()
                                    await asyncio.sleep(3)
                                    logger.info(f"Submitted search form for: {strategy['term']}")
                                else:
                                    # Try pressing Enter
                                    search_input.send_keys(Keys.RETURN)
                                    await asyncio.sleep(3)
                                    logger.info(f"Submitted search with Enter key for: {strategy['term']}")
                                    
                        except Exception as e:
                            logger.warning(f"Could not interact with search form for {strategy['term']}: {e}")
                    
                    # Process multiple pages for this search strategy
                    page_num = 1
                    max_pages_per_strategy = 20  # Increased from 10 to 20 for more comprehensive coverage
                    
                    while page_num <= max_pages_per_strategy:
                        try:
                            logger.info(f"Processing CanadaBuys page {page_num} for search: {strategy['term']}")
                            
                            # Wait for page to load
                            await asyncio.sleep(3)
                            
                            # Look for tender listings with updated selectors
                            tender_elements = []
                            selectors = [
                                ".search-result",           # Common search result class
                                ".opportunity-item",        # Opportunity items
                                ".tender-result",           # Tender results
                                "article",                  # Article elements (common for listings)
                                ".result-item",             # Result items
                                "div[class*='result']",     # Any div with 'result' in class
                                "div[class*='opportunity']", # Any div with 'opportunity' in class
                                "a[href*='/tender-opportunities/']",  # Links to tender opportunities
                                ".tender-listing",          # Tender listings
                                ".opportunity-listing",     # Opportunity listings
                                "div[class*='listing']",    # Any listing div
                                "div[class*='item']"        # Any item div
                            ]
                            
                            for selector in selectors:
                                elements = self.selenium.find_elements_safe(driver, By.CSS_SELECTOR, selector, timeout=5)
                                if elements and len(elements) > 0:
                                    tender_elements = elements
                                    logger.info(f"Found {len(elements)} elements using selector: {selector}")
                                    break
                            
                            # If still no specific elements, try to find any links that might be tenders
                            if not tender_elements or len(tender_elements) < 5:
                                logger.info("No specific tender elements found, searching for general links...")
                                try:
                                    all_links = driver.find_elements(By.TAG_NAME, "a")
                                    tender_elements = []
                                    for link in all_links:
                                        try:
                                            href = link.get_attribute('href')
                                            if href and ('/tender-opportunities/' in href or 'opportunity' in href.lower()):
                                                tender_elements.append(link)
                                        except Exception as e:
                                            logger.warning(f"Error getting href from link: {e}")
                                            continue
                                    logger.info(f"Found {len(tender_elements)} potential tender links")
                                except Exception as e:
                                    logger.error(f"Error searching for general links: {e}")
                                    tender_elements = []
                            
                            # Parse found elements - Process ALL elements, no artificial limits
                            page_tenders = []
                            for element in tender_elements:  # Process ALL elements, not just first 50
                                try:
                                    tender_data = self._parse_canadabuys_element(element, strategy['term'])
                                    if tender_data:
                                        page_tenders.append(tender_data)
                                except Exception as e:
                                    logger.warning(f"Error parsing CanadaBuys element: {e}")
                                    continue
                            
                            logger.info(f"Page {page_num}: Found {len(page_tenders)} tenders for search '{strategy['term']}'")
                            tenders.extend(page_tenders)
                            
                            # Try to go to next page
                            if page_num < max_pages_per_strategy:
                                try:
                                    # Look for "Load More" button
                                    load_more_selectors = [
                                        "button[class*='load-more']",
                                        "button[class*='Load More']",
                                        "a[class*='load-more']",
                                        ".load-more",
                                        "button:contains('Load More')",
                                        "button:contains('Show More')",
                                        "a:contains('Load More')",
                                        "a:contains('Show More')"
                                    ]
                                    
                                    load_more_clicked = False
                                    for selector in load_more_selectors:
                                        try:
                                            load_more_btn = driver.find_element(By.CSS_SELECTOR, selector)
                                            if load_more_btn and load_more_btn.is_displayed():
                                                driver.execute_script("arguments[0].click();", load_more_btn)
                                                await asyncio.sleep(3)
                                                logger.info(f"Clicked 'Load More' button on page {page_num}")
                                                load_more_clicked = True
                                                break
                                        except:
                                            continue
                                    
                                    # If no "Load More" button, try pagination
                                    if not load_more_clicked:
                                        pagination_selectors = [
                                            "a[class*='next']",
                                            "a[class*='Next']",
                                            ".pagination .next",
                                            ".pagination a[href*='page']",
                                            "a[aria-label*='Next']",
                                            "a[title*='Next']"
                                        ]
                                        
                                        page_advanced = False
                                        for selector in pagination_selectors:
                                            try:
                                                next_btn = driver.find_element(By.CSS_SELECTOR, selector)
                                                if next_btn and next_btn.is_displayed() and next_btn.is_enabled():
                                                    driver.execute_script("arguments[0].click();", next_btn)
                                                    await asyncio.sleep(3)
                                                    logger.info(f"Clicked 'Next' button on page {page_num}")
                                                    page_advanced = True
                                                    break
                                            except:
                                                continue
                                        
                                        if not page_advanced:
                                            # If no pagination found, try to construct next page URL
                                            current_url = driver.current_url
                                            if 'page=' in current_url:
                                                # Replace page number
                                                next_url = current_url.replace(f'page={page_num}', f'page={page_num + 1}')
                                            else:
                                                # Add page parameter
                                                separator = '&' if '?' in current_url else '?'
                                                next_url = f"{current_url}{separator}page={page_num + 1}"
                                            
                                            driver.get(next_url)
                                            await asyncio.sleep(3)
                                            logger.info(f"Navigated to next page URL: {next_url}")
                                            page_advanced = True
                                        
                                        if not page_advanced:
                                            logger.info(f"No more pages available for search '{strategy['term']}'")
                                            break
                                    
                                except Exception as e:
                                    logger.warning(f"Error navigating to next page: {e}")
                                    break  # Stop if we can't navigate further
                            
                            page_num += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing CanadaBuys page {page_num}: {e}")
                            break
                    
                except Exception as e:
                    logger.error(f"Error with search strategy {strategy['description']}: {e}")
                    continue
            
            logger.info(f"Found {len(tenders)} total tenders from CanadaBuys")
            
        except Exception as e:
            logger.error(f"Error scanning CanadaBuys: {e}")
        finally:
            if driver:
                driver.quit()
            
        return tenders
    
    def _parse_canadabuys_element(self, element, search_term: str) -> Optional[Dict]:
        """Parse CanadaBuys web element"""
        try:
            # Get the href attribute first
            href = element.get_attribute('href')
            if not href or '/tender-opportunities/' not in href:
                return None
            
            # Extract tender ID from URL
            tender_id = ""
            if '/tender-opportunities/' in href:
                # Extract the tender ID from the URL
                url_parts = href.split('/tender-opportunities/')
                if len(url_parts) > 1:
                    tender_id = url_parts[1].split('/')[0].split('?')[0]
            
            # Try to get the title from the element text
            title = ""
            try:
                title = element.text.strip()
            except:
                pass
            
            # If no title from text, try to get it from child elements
            if not title or len(title) < 5:
                try:
                    # Look for title in child elements
                    title_elements = element.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, .title, .tender-title, .opportunity-title")
                    for title_elem in title_elements:
                        if title_elem.text.strip():
                            title = title_elem.text.strip()
                            break
                except:
                    pass
            
            # If still no title, try to get it from aria-label or title attribute
            if not title or len(title) < 5:
                try:
                    aria_label = element.get_attribute('aria-label')
                    title_attr = element.get_attribute('title')
                    title = aria_label or title_attr or ""
                except:
                    pass
            
            # If we still don't have a proper title, try to extract from the URL
            if not title or len(title) < 5:
                try:
                    # Try to extract title from URL path
                    url_path = href.split('/tender-opportunities/')[1]
                    title = url_path.replace('-', ' ').replace('_', ' ').title()
                except:
                    pass
            
            # If we can't get a proper title, skip this element
            if not title or len(title) < 5:
                return None
            
            # Check if this is training-related (be more lenient)
            title_lower = title.lower()
            training_keywords = [
                'training', 'education', 'professional development', 'workshop', 'seminar', 'course',
                'learning', 'instruction', 'teaching', 'mentoring', 'coaching', 'consulting',
                'advisory', 'support', 'services', 'expertise', 'knowledge', 'skills'
            ]
            
            # Check if any training keywords are in the title
            is_training = any(keyword in title_lower for keyword in training_keywords)
            
            # If not training-related, still include it but mark as low priority
            if not is_training:
                # For CanadaBuys, include all tenders but mark non-training ones as low priority
                pass
            
            # Create tender data
            tender_data = {
                'tender_id': f"CB_{tender_id}" if tender_id else f"CB_{hash(title)}",
                'title': title,
                'organization': 'Government of Canada',
                'portal': 'CanadaBuys',
                'portal_url': 'https://canadabuys.canada.ca',
                'value': 0.0,
                'closing_date': None,
                'posted_date': datetime.utcnow(),
                'description': title,
                'location': '',
                'categories': [],
                'keywords': [],
                'tender_url': href,
                'documents_url': '',
                'is_active': True,
                'priority': 'low' if not is_training else 'medium'
            }
            
            return tender_data
            
        except Exception as e:
            logger.warning(f"Error parsing CanadaBuys element: {e}")
            return None
    
    async def scan_merx(self) -> list[Dict]:
        """Scan MERX portal for training tenders with multiple search strategies"""
        final_tenders: list[Dict] = []
        
        try:
            logger.info("Scanning MERX portal for training tenders...")
            
            # Multiple search strategies to find more tenders
            search_strategies = [
                {"url": "https://www.merx.com/public/solicitations/open?", "description": "Open solicitations"},
                {"url": "https://www.merx.com/public/solicitations/open?keywords=training", "description": "Training keyword search"},
                {"url": "https://www.merx.com/public/solicitations/open?keywords=education", "description": "Education keyword search"},
                {"url": "https://www.merx.com/public/solicitations/open?keywords=consulting", "description": "Consulting keyword search"},
                {"url": "https://www.merx.com/public/solicitations/open?keywords=services", "description": "Services keyword search"},
                {"url": "https://www.merx.com/public/solicitations/open?keywords=professional", "description": "Professional keyword search"}
            ]
            
            # Get driver for Selenium
            driver = await self.get_driver()
            if not driver:
                logger.error("Could not get driver for MERX")
                return final_tenders
            
            # Create MERX scraper instance
            merx_scraper = MERXScraper()
            merx_scraper.driver = driver
            
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
                "presenter", "speaker", "moderator", "coordinator",
                
                # Additional service keywords
                "consulting", "advisory", "support", "services", "expertise",
                "knowledge", "skills", "development", "improvement", "enhancement"
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
            
            for strategy in search_strategies:
                try:
                    logger.info(f"MERX search strategy: {strategy['description']}")
                    
                    # Use the MERX scraper with the correct URL
                    search_query = "training AND services AND professional AND development AND upskilling"
                    tenders = await merx_scraper.search(search_query, max_pages=5, search_url=strategy['url'])
                    
                    # Filter tenders for training content
                    training_tenders = []
                    for tender_data in tenders:
                        try:
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
                                training_tenders.append(tender_data)
                        except Exception as e:
                            logger.warning(f"Error processing MERX tender: {e}")
                            continue
                    
                    logger.info(f"Strategy '{strategy['description']}': Found {len(tenders)} total tenders, {len(training_tenders)} training-related")
                    final_tenders.extend(training_tenders)
                    
                except Exception as e:
                    logger.error(f"Error in MERX search strategy '{strategy['description']}': {e}")
                    continue
            
            # Deduplicate results
            unique_tenders = []
            seen_ids = set()
            for tender in final_tenders:
                tender_id = tender.get('tender_id', '')
                if tender_id not in seen_ids:
                    seen_ids.add(tender_id)
                    unique_tenders.append(tender)
            
            logger.info(f"MERX scan complete: {len(final_tenders)} total tenders, {len(unique_tenders)} unique training tenders")
            return unique_tenders
            
        except Exception as e:
            logger.error(f"Error scanning MERX: {e}")
            return final_tenders
    
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

    async def scan(self):
        """Enhanced scan with multiple search strategies"""
        logger.info("Starting enhanced procurement scan with multiple strategies")
        
        all_tenders = []
        search_strategies = generate_search_queries()
        
        # Scan each portal with multiple strategies
        for portal_name, portal_scanner in self.portals.items():
            logger.info(f"Scanning {portal_name} with enhanced strategies")
            
            try:
                portal_tenders = []
                
                # Handle different portal types
                if portal_scanner is None:
                    # Use specific scan methods for portals without scraper instances
                    try:
                        if portal_name == 'BCBid':
                            logger.info("Scanning BC Bid using scan_bcbid method")
                            portal_tenders = await self.scan_bcbid()
                        elif portal_name == 'SEAO':
                            logger.info("Scanning SEAO using scan_seao_web method")
                            portal_tenders = await self.scan_seao_web()
                        elif portal_name == 'Biddingo':
                            logger.info("Scanning Biddingo using scan_biddingo method")
                            # Use a default config for Biddingo
                            config = {'name': 'Biddingo', 'url': 'https://www.biddingo.com'}
                            portal_tenders = await self.scan_biddingo('Biddingo', config)
                        elif portal_name == 'BidsAndTenders':
                            logger.info("Scanning Bids&Tenders using scan_bidsandtenders_portal method")
                            # Use a default search URL for Bids&Tenders
                            search_url = 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all'
                            portal_tenders = await self.scan_bidsandtenders_portal('Bids&Tenders', search_url)
                        else:
                            logger.warning(f"No scanner available for portal: {portal_name}")
                            continue
                    except Exception as e:
                        logger.error(f"Error scanning {portal_name} with specific method: {e}")
                        continue
                else:
                    # Use the scraper instance for portals with dedicated scrapers
                    # Execute multiple search strategies for each portal
                    for strategy_name, queries in search_strategies.items():
                        logger.info(f"Executing {strategy_name} strategy on {portal_name}")
                        
                        for query in queries:
                            try:
                                # Add timeout to prevent getting stuck
                                import asyncio
                                
                                # Select appropriate query format for each portal
                                if portal_name.lower() == 'canadabuys':
                                    # Use quoted searches for CanadaBuys
                                    if 'AND' not in query:  # Use quoted format
                                        formatted_query = query
                                    else:
                                        # Convert AND format to quoted format for CanadaBuys
                                        keywords = query.replace(' AND ', ' ').split()
                                        formatted_query = ' '.join([f'"{kw}"' for kw in keywords])
                                elif portal_name.lower() == 'merx':
                                    # Use AND searches for MERX
                                    if 'AND' in query:  # Use AND format
                                        formatted_query = query
                                    else:
                                        # Convert quoted format to AND format for MERX
                                        keywords = query.replace('"', '').split()
                                        formatted_query = ' AND '.join(keywords)
                                else:
                                    formatted_query = query
                                
                                logger.info(f"Searching {portal_name} with query: '{formatted_query}' (original: '{query}')")
                                
                                # Add timeout to search operation
                                search_task = asyncio.create_task(portal_scanner.search(formatted_query))
                                try:
                                    # Use shorter timeout for MERX to prevent blocking other portals
                                    timeout = 60 if portal_name.lower() == 'merx' else 180  # 1 minute for MERX, 3 minutes for others
                                    results = await asyncio.wait_for(search_task, timeout=timeout)
                                except asyncio.TimeoutError:
                                    logger.warning(f"Search for '{formatted_query}' on {portal_name} timed out - skipping")
                                    if not search_task.done():
                                        search_task.cancel()
                                    continue
                                
                                # Score and enhance results
                                scored_results = []
                                for result in results:
                                    scored_result = {
                                        **result,
                                        'relevance_score': score_tender_relevance(result),
                                        'search_strategy': strategy_name,
                                        'search_query': query
                                    }
                                    scored_results.append(scored_result)
                                
                                portal_tenders.extend(scored_results)
                                logger.info(f"Found {len(scored_results)} results for query '{formatted_query}' on {portal_name}")
                                
                            except Exception as e:
                                logger.warning(f"Search failed for '{query}' on {portal_name}: {e}")
                                continue
                
                # Deduplicate and sort by relevance for this portal
                unique_portal_tenders = deduplicate_tenders(portal_tenders)
                sorted_tenders = sorted(unique_portal_tenders, key=lambda x: x.get('relevance_score', 0), reverse=True)
                
                # Filter for minimum relevance score (remove low-quality matches)
                relevant_tenders = [t for t in sorted_tenders if t.get('relevance_score', 0) >= 5]
                
                logger.info(f"Portal {portal_name}: {len(portal_tenders)} total results, {len(unique_portal_tenders)} unique, {len(relevant_tenders)} relevant")
                all_tenders.extend(relevant_tenders)
                
            except Exception as e:
                logger.error(f"Error scanning {portal_name}: {e}")
                continue
        
        # Final deduplication across all portals
        final_tenders = deduplicate_tenders(all_tenders)
        final_tenders = sorted(final_tenders, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        logger.info(f"Enhanced scan complete: {len(all_tenders)} total results, {len(final_tenders)} unique relevant tenders")
        
        # Save to database
        saved_count = 0
        for tender_data in final_tenders:
            try:
                # Remove scoring fields before saving
                tender_data.pop('relevance_score', None)
                tender_data.pop('search_strategy', None)
                tender_data.pop('search_query', None)
                
                tender = Tender(**tender_data)
                self.db.add(tender)
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving tender {tender_data.get('tender_id', 'unknown')}: {e}")
                continue
        
        try:
            self.db.commit()
            logger.info(f"Successfully saved {saved_count} tenders to database")
        except Exception as e:
            logger.error(f"Error committing to database: {e}")
            self.db.rollback()
        
        return final_tenders

# FastAPI app setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting procurement scanner...")

    # Wait for Selenium Grid to be ready
    selenium_grid = SeleniumGridManager()
    if not selenium_grid.wait_for_grid_ready():
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
    # Use the existing scan method for now
    background_tasks.add_task(scan_all_portals)
    return {"message": "Scan initiated"}

async def scan_all_portals():
    """Enhanced scan using the new multi-strategy approach"""
    try:
        scanner = ProcurementScanner()
        logger.info("Starting enhanced procurement scan with multiple strategies")
        
        # Use the new enhanced scan method
        tenders = await scanner.scan()
        
        logger.info(f"Enhanced scan complete: {len(tenders)} tenders found")
        return tenders
        
    except Exception as e:
        logger.error(f"Error during enhanced scan: {e}")
        return []

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)