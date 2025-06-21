# main.py - FastAPI Backend Server for Canadian Procurement Scanner
import os
import re
import json
import hashlib
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from time import sleep
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import pandas as pd
import aiohttp
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Boolean, Integer, func, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.keys import Keys
from tenacity import retry, stop_after_attempt, wait_exponential
import zipfile
import shutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://procurement_user:procurement_pass@postgres:5432/procurement_scanner")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Tender(Base):
    __tablename__ = "tenders"
    
    id = Column(String, primary_key=True)
    tender_id = Column(String, unique=True, index=True)
    title = Column(String)
    organization = Column(String)
    portal = Column(String, index=True)
    portal_url = Column(String)
    value = Column(Float)
    closing_date = Column(DateTime, index=True)
    posted_date = Column(DateTime)
    description = Column(Text)
    location = Column(String)
    categories = Column(Text)  # JSON string
    keywords = Column(Text)  # JSON string
    contact_email = Column(String)
    contact_phone = Column(String)
    tender_url = Column(String)
    documents_url = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    hash = Column(String)  # To detect changes
    priority = Column(String)
    matching_courses = Column(Text)  # JSON string
    download_count = Column(Integer, default=0)
    attachments = Column(Text)  # JSON string of attachment info
    
Base.metadata.create_all(bind=engine)

# Pydantic models
class TenderResponse(BaseModel):
    id: str
    tender_id: str
    title: str
    organization: str
    portal: str
    value: float
    closing_date: datetime
    posted_date: datetime
    description: str
    location: str
    categories: List[str]
    keywords: List[str]
    tender_url: str
    matching_courses: List[str]
    priority: str

class StatsResponse(BaseModel):
    total_tenders: int
    total_value: float
    by_portal: List[Dict[str, Any]]
    by_category: Dict[str, int]
    closing_soon: int
    new_today: int
    last_scan: Optional[datetime]

# The Knowledge Academy course mapping
TKA_COURSES = {
    'project-management': {
        'keywords': ['prince2', 'pmp', 'project management', 'capm', 'msp', 'portfolio', 'program management', 'pmo', 'agile project', 'pmbok', 'pmi'],
        'courses': ['PRINCE2 Foundation', 'PRINCE2 Practitioner', 'PRINCE2 Agile', 'PMP Certification', 'CAPM', 'MSP', 'Portfolio Management', 'Program Management']
    },
    'it-technical': {
        'keywords': ['itil', 'cloud', 'aws', 'azure', 'devops', 'docker', 'kubernetes', 'linux', 'python', 'java', 'database', 'sql', 'cisco', 'vmware', 'microsoft', 'oracle', 'sap'],
        'courses': ['ITIL 4 Foundation', 'AWS Solutions Architect', 'Azure Fundamentals', 'DevOps Certification', 'Linux Administration', 'Python Programming', 'Java Development']
    },
    'cybersecurity': {
        'keywords': ['security', 'cyber', 'cissp', 'ethical hacking', 'penetration', 'iso 27001', 'gdpr', 'ceh', 'comptia security', 'firewall', 'soc', 'siem', 'incident response'],
        'courses': ['CISSP Certification', 'Ethical Hacking', 'ISO 27001', 'Security Awareness', 'CompTIA Security+', 'CEH', 'Penetration Testing']
    },
    'agile-scrum': {
        'keywords': ['agile', 'scrum', 'safe', 'kanban', 'sprint', 'product owner', 'scrum master', 'lean', 'jira', 'confluence', 'retrospective', 'backlog'],
        'courses': ['Scrum Master Certification', 'Product Owner Certification', 'SAFe Agilist', 'Agile Coach', 'Kanban Training']
    },
    'leadership': {
        'keywords': ['leadership', 'management', 'executive', 'coaching', 'change management', 'transformation', 'strategic', 'team building', 'communication', 'stakeholder'],
        'courses': ['Leadership Excellence', 'Executive Coaching', 'Change Management', 'Strategic Leadership', 'Team Leadership']
    },
    'data-analytics': {
        'keywords': ['data', 'analytics', 'power bi', 'tableau', 'excel', 'business intelligence', 'visualization', 'reporting', 'dashboard', 'kpi', 'metrics', 'sql'],
        'courses': ['Power BI Training', 'Tableau Certification', 'Advanced Excel', 'Data Analytics', 'Business Intelligence', 'SQL for Analytics']
    },
    'soft-skills': {
        'keywords': ['communication', 'presentation', 'negotiation', 'time management', 'emotional intelligence', 'conflict', 'teamwork', 'public speaking', 'writing'],
        'courses': ['Presentation Skills', 'Negotiation Skills', 'Time Management', 'Business Communication', 'Emotional Intelligence', 'Conflict Resolution']
    },
    'compliance': {
        'keywords': ['compliance', 'audit', 'risk management', 'governance', 'quality', 'iso', 'regulatory', 'health safety', 'privacy', 'sox', 'grc'],
        'courses': ['ISO 9001', 'Risk Management', 'Compliance Training', 'Internal Auditor', 'Health & Safety', 'GDPR Compliance']
    }
}

# Corrected Portal configurations with actual working URLs and API endpoints
PORTAL_CONFIGS = {
    # Federal Portals with Open Data APIs
    'canadabuys': {
        'name': 'CanadaBuys',
        'type': 'api',
        'apis': {
            'tenders_new': 'https://canadabuys.canada.ca/opendata/pub/newTenderNotice-nouvelAvisAppelOffres.csv',
            'tenders_open': 'https://canadabuys.canada.ca/opendata/pub/openTenderNotice-ouvertAvisAppelOffres.csv',
            'tenders_complete': 'https://canadabuys.canada.ca/opendata/pub/tenderNoticeComplete-avisAppelOffresComplet.csv',
            'awards': 'https://canadabuys.canada.ca/opendata/pub/awardNoticeComplete-avisAttributionComplet.csv',
            'contracts': 'https://canadabuys.canada.ca/opendata/pub/contractHistoryComplete-historiqueContratComplet.csv'
        }
    },
    'merx': {
        'name': 'MERX',
        'type': 'scrape',
        'url': 'https://www.merx.com/',
        'search_url': 'https://www.merx.com/search',
        'requires_selenium': True,
        'login_required': False
    },
    'biddingo': {
        'name': 'Biddingo',
        'type': 'scrape',
        'url': 'https://www.biddingo.com/',
        'search_url': 'https://www.biddingo.com/search',
        'requires_selenium': True
    },
    
    # Provincial Portals - Updated with correct URLs
    'bcbid': {
        'name': 'BC Bid',
        'type': 'scrape',
        'url': 'https://www.bcbid.gov.bc.ca/',
        'search_url': 'https://www.bcbid.gov.bc.ca/page.aspx/en/buy/homepage',
        'requires_selenium': True
    },
    'albertapurchasing': {
        'name': 'Alberta Purchasing Connection',
        'type': 'scrape',
        'url': 'https://vendor.purchasingconnection.ca/',
        'search_url': 'https://vendor.purchasingconnection.ca/Search.aspx',
        'requires_selenium': True
    },
    'sasktenders': {
        'name': 'SaskTenders',
        'type': 'scrape',
        'url': 'https://sasktenders.ca/',
        'search_url': 'https://sasktenders.ca/Content/Public/Search.aspx',
        'requires_selenium': True
    },
    'manitoba': {
        'name': 'Manitoba Tenders',
        'type': 'scrape',
        'url': 'https://www.gov.mb.ca/tenders/',
        'search_url': 'https://www.gov.mb.ca/tenders/',
        'requires_selenium': False
    },
    'ontario': {
        'name': 'Ontario Tenders Portal',
        'type': 'bidsandtenders',
        'url': 'https://ontariotenders.ca/',
        'search_url': 'https://ontariotenders.ca/page/public/buyer',
        'requires_selenium': True
    },
    'seao': {
        'name': 'SEAO Quebec',
        'type': 'api_and_scrape',
        'url': 'https://www.seao.ca/',
        'search_url': 'https://www.seao.ca/OpportunityPublication/rechercheAvancee.aspx',
        'api_endpoints': {
            'json_weekly': 'https://www.donneesquebec.ca/recherche/dataset/d23b2e02-085d-43e5-9e6e-e1d558ebfdd5/resource/*/download/hebdo_*.json',
            'json_monthly': 'https://www.donneesquebec.ca/recherche/dataset/d23b2e02-085d-43e5-9e6e-e1d558ebfdd5/resource/*/download/mensuel_*.json'
        },
        'requires_selenium': True,
        'api_working': False  # API endpoints return 404, will use web scraping only
    },
    'nbon': {
        'name': 'New Brunswick Opportunities Network',
        'type': 'scrape',
        'url': 'https://nbon.gnb.ca/',
        'search_url': 'https://nbon.gnb.ca/content/nbon/en/opportunities.html',
        'requires_selenium': True
    },
    'ns': {
        'name': 'Nova Scotia Tenders',
        'type': 'scrape',
        'url': 'https://beta.novascotia.ca/find-public-tender-notices',
        'search_url': 'https://beta.novascotia.ca/find-public-tender-notices',
        'requires_selenium': True
    },
    'pei': {
        'name': 'PEI Tenders',
        'type': 'scrape',
        'url': 'https://www.princeedwardisland.ca/en/topic/tenders',
        'search_url': 'https://www.princeedwardisland.ca/en/search/site?f%5B0%5D=type%3Atender',
        'requires_selenium': False
    },
    'nl': {
        'name': 'Newfoundland Procurement',
        'type': 'scrape',
        'url': 'https://www.gov.nl.ca/tenders/',
        'search_url': 'https://www.gov.nl.ca/tenders/',
        'requires_selenium': False
    },
    
    # Municipal Portals - Updated with working URLs
    'toronto': {
        'name': 'City of Toronto',
        'type': 'ariba',
        'url': 'https://www.toronto.ca/business-economy/doing-business-with-the-city/',
        'ariba_url': 'https://service.ariba.com/Discovery.aw/ad/profile?key=AN01050912625',
        'requires_selenium': True,
        'ariba_key': 'AN01050912625',
        'location': 'Toronto'
    },
    'vancouver': {
        'name': 'City of Vancouver',
        'type': 'scrape',
        'url': 'https://vancouver.ca/doing-business/selling-to-and-buying-from-the-city.aspx',
        'search_url': 'https://vancouver.ca/doing-business/open-bids.aspx',
        'requires_selenium': True
    },
    'montreal': {
        'name': 'City of Montreal',
        'type': 'seao',
        'url': 'https://montreal.ca/sujets/appels-doffres-et-soumissions',
        'seao_org_id': 'montreal',
        'requires_selenium': True
    },
    'calgary': {
        'name': 'City of Calgary',
        'type': 'scrape',
        'url': 'https://www.calgary.ca/cfod/supply/current-opportunities.html',
        'search_url': 'https://www.calgary.ca/cfod/supply/current-opportunities.html',
        'requires_selenium': True
    },
    'edmonton': {
        'name': 'City of Edmonton',
        'type': 'bidsandtenders',
        'url': 'https://www.edmonton.ca/business_economy/selling-to-the-city',
        'search_url': 'https://edmonton.bidsandtenders.ca/Module/Tenders/en',
        'requires_selenium': True,
        'working': False  # Returns 302 redirect to error page
    },
    'ottawa': {
        'name': 'City of Ottawa',
        'type': 'mixed',
        'url': 'https://ottawa.ca/en/business/procurement',
        'search_url': 'https://ottawa.bidsandtenders.ca/Module/Tenders/en',
        'merx_url': 'https://www.merx.com/',
        'ariba_url': 'https://service.ariba.com/',
        'requires_selenium': True
    },
    'winnipeg': {
        'name': 'City of Winnipeg',
        'type': 'scrape',
        'url': 'https://winnipeg.ca/matmgt/bidopp.asp',
        'search_url': 'https://winnipeg.ca/matmgt/bidopp.asp',
        'requires_selenium': False
    },
    'quebec_city': {
        'name': 'Quebec City',
        'type': 'seao',
        'url': 'https://www.ville.quebec.qc.ca/apropos/affaires/appels_offres/index.aspx',
        'seao_org_id': 'ville-quebec',
        'requires_selenium': True
    },
    'halifax': {
        'name': 'Halifax Regional Municipality',
        'type': 'scrape',
        'url': 'https://www.halifax.ca/business/selling-to-halifax',
        'search_url': 'https://apps.nsprocurement.novascotia.ca/tenders',
        'requires_selenium': True
    },
    'london': {
        'name': 'City of London',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.com/',
        'search_url': 'https://www.bidsandtenders.com/',
        'biddingo_org': 'london',
        'requires_selenium': True,
        'working': False  # Municipal portal broken, will use main site
    },
    'hamilton': {
        'name': 'City of Hamilton',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.com/',
        'search_url': 'https://www.bidsandtenders.com/',
        'biddingo_org': 'hamilton',
        'requires_selenium': True,
        'working': False  # Municipal portal broken, will use main site
    },
    'kitchener': {
        'name': 'City of Kitchener',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.com/',
        'search_url': 'https://www.bidsandtenders.com/',
        'biddingo_org': 'kitchener',
        'requires_selenium': True,
        'working': False  # Municipal portal broken, will use main site
    },
    'regina': {
        'name': 'City of Regina',
        'type': 'sasktenders',
        'url': 'https://www.regina.ca/business-development/bidding-purchasing-city/',
        'search_url': 'https://sasktenders.ca/',
        'sasktenders_org': 'City of Regina',
        'requires_selenium': True
    },
    'saskatoon': {
        'name': 'City of Saskatoon',
        'type': 'sasktenders',
        'url': 'https://www.saskatoon.ca/business-development/selling-city/bids-tenders',
        'search_url': 'https://sasktenders.ca/',
        'sasktenders_org': 'City of Saskatoon',
        'requires_selenium': True
    },
    
    # Other Public Sector - Updated URLs
    'buybc': {
        'name': 'BC Health Authorities',
        'type': 'scrape',
        'url': 'https://www.bcbid.gov.bc.ca/',
        'search_url': 'https://www.bcbid.gov.bc.ca/',
        'health_authority': True,
        'requires_selenium': True
    },
    'mohltc': {
        'name': 'Ontario Health',
        'type': 'merx',
        'url': 'https://www.ontariohealth.ca/',
        'merx_org': 'ontario-health',
        'requires_selenium': True
    },
    'bidsandtenders': {
        'name': 'bids&tenders Platform',
        'type': 'platform',
        'url': 'https://www.bidsandtenders.com/',
        'platform_clients': ['edmonton', 'ottawa', 'london', 'hamilton', 'kitchener'],
        'requires_selenium': True
    }
}

class SeleniumGridDriver:
    """Enhanced Selenium Grid driver with Toronto scraper techniques"""
    
    def __init__(self):
        self.hub_url = os.getenv('SELENIUM_HUB_URL', 'http://selenium-hub:4444/wd/hub')
        self.download_dir = Path("/app/data/downloads")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def get_options(self):
        """Chrome options optimized for scraping"""
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Set download directory
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        # User agent to avoid detection
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        return options
        
    def get_driver(self):
        """Get a new driver instance from Selenium Grid"""
        try:
            driver = webdriver.Remote(
                command_executor=self.hub_url,
                options=self.get_options()
            )
            driver.implicitly_wait(10)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            logger.error(f"Failed to connect to Selenium Grid: {e}")
            raise
    
    def patiently_click(self, driver, xpath_or_element, wait_after=0, timeout=120):
        """Patient clicking from Toronto scraper"""
        try:
            if isinstance(xpath_or_element, str):
                logger.info(f"Looking for element: {xpath_or_element}")
                element = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_or_element))
                )
            else:
                element = xpath_or_element
                
            logger.info("Clicking element")
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            sleep(0.5)
            element.click()
            
            if wait_after > 0:
                logger.info(f"Waiting {wait_after} seconds after click")
                sleep(wait_after)
                
        except TimeoutException:
            logger.error(f"Timeout waiting for element: {xpath_or_element}")
            raise
    
    def patiently_find_regex(self, driver, regex, max_wait=60):
        """Find content using regex pattern"""
        total_wait = 0
        results = []
        
        while len(results) == 0 and total_wait < max_wait:
            sleep(1)
            total_wait += 1
            try:
                results = re.findall(regex, driver.page_source)
            except:
                pass
                
        if len(results) == 0:
            return None
        return results[0]
    
    def wait_for_download(self, driver, action_func, max_wait=120):
        """Wait for download to complete"""
        initial_files = set(os.listdir(self.download_dir))
        action_func()
        
        total_wait = 0
        while total_wait < max_wait:
            sleep(1)
            total_wait += 1
            current_files = set(os.listdir(self.download_dir))
            new_files = current_files - initial_files
            
            # Check if any new file is complete (not .tmp or .crdownload)
            if new_files:
                for file in new_files:
                    if not file.endswith(('.tmp', '.crdownload', '.part')):
                        return True
                        
        return False

class AribaDriver:
    """Ariba-specific driver based on Toronto scraper"""
    
    def __init__(self, driver, profile_key):
        self.driver = driver
        self.profile_key = profile_key
        self.base_url = "https://service.ariba.com/Discovery.aw/ad/profile"
        
    def login(self, username=None, password=None):
        """Login to Ariba if required"""
        try:
            # Check if login is needed
            login_elements = self.driver.find_elements(By.CSS_SELECTOR, ".sap-icon--log")
            if len(login_elements) == 0:
                return True  # Already logged in
                
            # Find username field
            username_elem = self.driver.find_element(By.XPATH, "//input[@name='UserName'][@type='text']")
            password_elem = self.driver.find_element(By.XPATH, "//input[@name='Password'][@type='password']")
            
            if username and password:
                username_elem.send_keys(username)
                password_elem.send_keys(password)
                password_elem.send_keys(Keys.ENTER)
                sleep(5)
                return True
            else:
                logger.warning("Ariba login required but no credentials provided")
                return False
                
        except NoSuchElementException:
            logger.info("No login required or already logged in")
            return True
    
    def go_home(self):
        """Navigate to Ariba discovery page"""
        self.driver.get(f"{self.base_url}?key={self.profile_key}")
        sleep(3)

class ProcurementScanner:
    def __init__(self):
        self.selenium = SeleniumGridDriver()
        self.session = None
        self.download_dir = Path("/app/data/downloads")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = Path("/app/data/tenders")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    async def get_session(self):
        """Get aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def extract_zip_recursively(self, zip_path: Path, extract_to: Path):
        """Extract zip files recursively like Toronto scraper"""
        logger.info(f"Extracting {zip_path} to {extract_to}")
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_to)
            
        # Look for nested zips
        for item in extract_to.iterdir():
            if item.suffix.lower() == '.zip':
                nested_dir = item.with_suffix('')
                nested_dir.mkdir(exist_ok=True)
                self.extract_zip_recursively(item, nested_dir)
                item.unlink()  # Remove the nested zip
    
    async def scan_canadabuys(self) -> List[Dict]:
        """Scan CanadaBuys using open data API endpoints"""
        tenders = []
        session = await self.get_session()
        
        # Add headers to avoid 403 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        try:
            # Use the new open data endpoints
            endpoints = PORTAL_CONFIGS['canadabuys']['apis']
            
            for endpoint_name, url in endpoints.items():
                if 'tender' in endpoint_name:  # Focus on tender endpoints
                    logger.info(f"Fetching CanadaBuys {endpoint_name} from {url}")
                    
                    try:
                        async with session.get(url, headers=headers) as response:
                            if response.status == 200:
                                content = await response.text()
                                logger.info(f"Downloaded {len(content)} characters from {endpoint_name}")
                                
                                # Save CSV for processing
                                csv_file = self.download_dir / f"canadabuys_{endpoint_name}_{datetime.now().strftime('%Y%m%d')}.csv"
                                with open(csv_file, 'w', encoding='utf-8') as f:
                                    f.write(content)
                                
                                logger.info(f"Saved CSV to {csv_file}")
                                
                                # Read with pandas
                                try:
                                    df = pd.read_csv(csv_file, encoding='utf-8', low_memory=False)
                                    logger.info(f"Found {len(df)} records in {endpoint_name}")
                                    
                                    # Process each row
                                    processed_count = 0
                                    training_related_count = 0
                                    
                                    for _, row in df.iterrows():
                                        try:
                                            tender = self._parse_canadabuys_row(row, endpoint_name)
                                            processed_count += 1
                                            
                                            if tender and self._is_training_related(tender):
                                                tenders.append(tender)
                                                training_related_count += 1
                                        except Exception as e:
                                            logger.error(f"Error processing row {processed_count} in {endpoint_name}: {e}")
                                            continue
                                    
                                    logger.info(f"Processed {processed_count} rows, found {training_related_count} training-related tenders from {endpoint_name}")
                                    
                                except Exception as e:
                                    logger.error(f"Error reading CSV {endpoint_name}: {e}")
                                    continue
                            else:
                                logger.error(f"HTTP {response.status} for {endpoint_name}")
                    except Exception as e:
                        logger.error(f"Error fetching {endpoint_name}: {e}")
                        continue
                                
        except Exception as e:
            logger.error(f"Error scanning CanadaBuys: {e}")
            
        logger.info(f"CanadaBuys scan complete. Total tenders found: {len(tenders)}")
        return tenders
    
    def _parse_canadabuys_row(self, row, endpoint_type) -> Optional[Dict]:
        """Parse a row from CanadaBuys CSV - updated for new format"""
        try:
            # Correct column names from the actual CSV
            tender_id = str(row.get('solicitationNumber-numeroSollicitation', ''))
            title = str(row.get('title-titre-eng', ''))  # English title
            org = str(row.get('contractingEntityName-nomEntitContractante-eng', ''))
            value = row.get('contractValue-valeurContrat', 0)  # This column might not exist
            closing = row.get('tenderClosingDate-appelOffresDateCloture', '')
            posted = row.get('publicationDate-datePublication', '')
            desc = str(row.get('tenderDescription-descriptionAppelOffres-eng', ''))
            location = row.get('regionsOfDelivery-regionsLivraison-eng', 'Canada')
            categories = row.get('procurementCategory-categorieApprovisionnement', '')
                
            tender = {
                'tender_id': tender_id,
                'title': title,
                'organization': org,
                'portal': 'CanadaBuys',
                'portal_url': PORTAL_CONFIGS['canadabuys']['apis'][endpoint_type],
                'value': self._parse_value(value),
                'closing_date': self._parse_date(closing),
                'posted_date': self._parse_date(posted),
                'description': desc,
                'location': location,
                'tender_url': f"https://canadabuys.canada.ca/en/tender-opportunities/{tender_id}",
                'categories': self._extract_categories_from_text(f"{title} {desc} {categories}"),
                'keywords': self._extract_keywords_from_text(f"{title} {desc}")
            }
            
            return tender if tender['tender_id'] else None
            
        except Exception as e:
            logger.error(f"Error parsing CanadaBuys row: {e}")
            return None
    
    async def scan_ariba_portal(self, portal_name: str, config: Dict) -> List[Dict]:
        """Scan Ariba-based portals like Toronto"""
        tenders = []
        driver = None
        
        try:
            driver = self.selenium.get_driver()
            ariba = AribaDriver(driver, config['ariba_key'])
            
            # Navigate to discovery page
            ariba.go_home()
            
            # Check if login required
            username = os.getenv('ARIBA_USERNAME')
            password = os.getenv('ARIBA_PASSWORD')
            if username and password:
                ariba.login(username, password)
            
            # Look for open RFPs
            tender_elements = driver.find_elements(By.CLASS_NAME, "ADTableBodyWhite")
            tender_elements += driver.find_elements(By.CLASS_NAME, "ADHiliteBlock")
            
            logger.info(f"Found {len(tender_elements)} potential tenders on {portal_name}")
            
            for element in tender_elements[:20]:  # Limit to prevent long runs
                try:
                    title_elem = element.find_element(By.CLASS_NAME, "QuoteSearchResultTitle")
                    title = title_elem.text
                    
                    # Extract dates
                    date_elems = element.find_elements(By.CLASS_NAME, "paddingRight5")
                    closing_date = None
                    
                    for date_elem in date_elems:
                        parsed_date = self._parse_date_text(date_elem.text)
                        if parsed_date and (not closing_date or parsed_date > closing_date):
                            closing_date = parsed_date
                    
                    # Click to get details
                    title_elem.click()
                    sleep(2)
                    
                    # Get document ID
                    doc_id = self.selenium.patiently_find_regex(driver, r"(Doc\d{10})")
                    
                    # Get page content
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Extract details
                    tender = {
                        'tender_id': doc_id or f"ARIBA_{datetime.now().timestamp()}",
                        'title': title,
                        'organization': portal_name,
                        'portal': portal_name,
                        'portal_url': config['url'],
                        'value': 0,  # Ariba doesn't always show value
                        'closing_date': closing_date,
                        'posted_date': datetime.utcnow(),
                        'description': self._extract_description_from_soup(soup),
                        'location': config.get('location', 'Toronto'),
                        'tender_url': driver.current_url,
                        'categories': [],
                        'keywords': []
                    }
                    
                    # Extract categories and keywords
                    full_text = f"{tender['title']} {tender['description']}"
                    tender['categories'] = self._extract_categories_from_text(full_text)
                    tender['keywords'] = self._extract_keywords_from_text(full_text)
                    
                    # Check for attachments
                    self._download_ariba_attachments(driver, doc_id)
                    
                    # Go back to search results
                    driver.execute_script("window.history.go(-1)")
                    sleep(2)
                    
                    if self._is_training_related(tender):
                        tenders.append(tender)
                        
                except Exception as e:
                    logger.error(f"Error processing Ariba tender: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scanning Ariba portal {portal_name}: {e}")
        finally:
            if driver:
                driver.quit()
                
        return tenders
    
    def _download_ariba_attachments(self, driver, doc_id):
        """Download attachments from Ariba like Toronto scraper"""
        try:
            # Look for download button
            download_button = driver.find_element(By.XPATH, "//a[contains(@class, 'adsmallbutton') and contains(@class, 'adbuttonblock')]")
            if download_button:
                self.selenium.patiently_click(driver, download_button, wait_after=3)
                
                # Click download content
                content_button = driver.find_element(By.ID, "_xjqay")
                if content_button:
                    self.selenium.patiently_click(driver, content_button)
                    
                    # Click download attachments
                    attach_button = driver.find_element(By.ID, "_hgesab")
                    if attach_button:
                        self.selenium.patiently_click(driver, attach_button, wait_after=5)
                        
                        # Select all
                        select_all = driver.find_element(By.XPATH, '//*[@id="_h_l$m"]/span/div/label')
                        if select_all:
                            self.selenium.patiently_click(driver, select_all, wait_after=2)
                            
                            # Download
                            final_download = driver.find_element(By.ID, "_5wq_j")
                            if final_download:
                                self.selenium.wait_for_download(driver, lambda: final_download.click())
                                
        except NoSuchElementException:
            logger.info("No attachments found or download not available")
        except Exception as e:
            logger.error(f"Error downloading attachments: {e}")
    
    async def scan_merx(self) -> List[Dict]:
        """Scan MERX using Selenium Grid"""
        tenders = []
        driver = None
        
        try:
            driver = self.selenium.get_driver()
            driver.get(PORTAL_CONFIGS['merx']['url'])
            sleep(3)
            
            # Click on Search/Browse Opportunities
            search_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Search"))
            )
            search_link.click()
            sleep(2)
            
            # Enter search keywords
            search_box = driver.find_element(By.ID, "keyword")
            search_box.clear()
            search_box.send_keys("training development coaching certification professional education")
            
            # Submit search
            search_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            search_button.click()
            sleep(3)
            
            # Parse results
            page_count = 0
            while page_count < 5:  # Limit pages to prevent long runs
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Find all opportunity rows
                opportunities = soup.find_all('div', class_='row')
                
                for opp in opportunities:
                    tender = self._parse_merx_opportunity(opp)
                    if tender and self._is_training_related(tender):
                        tenders.append(tender)
                
                # Check for next page
                try:
                    next_button = driver.find_element(By.XPATH, "//a[contains(@class, 'next')]")
                    if 'disabled' not in next_button.get_attribute('class'):
                        next_button.click()
                        sleep(3)
                        page_count += 1
                    else:
                        break
                except NoSuchElementException:
                    break
                    
        except Exception as e:
            logger.error(f"Error scanning MERX: {e}")
        finally:
            if driver:
                driver.quit()
                
        return tenders
    
    def _parse_merx_opportunity(self, soup_element) -> Optional[Dict]:
        """Parse MERX opportunity from search results"""
        try:
            # Extract title and link
            title_link = soup_element.find('a', class_='search-result-title')
            if not title_link:
                return None
                
            title = title_link.text.strip()
            url = 'https://www.merx.com' + title_link.get('href', '')
            
            # Extract other details
            details = soup_element.find_all('div', class_='col-sm-12')
            
            tender = {
                'tender_id': '',
                'title': title,
                'organization': '',
                'portal': 'MERX',
                'portal_url': PORTAL_CONFIGS['merx']['url'],
                'value': 0,
                'closing_date': None,
                'posted_date': None,
                'description': '',
                'location': 'Canada',
                'tender_url': url,
                'categories': [],
                'keywords': []
            }
            
            # Parse details
            for detail in details:
                text = detail.text.strip()
                
                if 'Reference' in text:
                    tender['tender_id'] = text.split(':')[-1].strip()
                elif 'Published' in text:
                    date_str = text.split(':')[-1].strip()
                    tender['posted_date'] = self._parse_date(date_str)
                elif 'Closing' in text:
                    date_str = text.split(':')[-1].strip()
                    tender['closing_date'] = self._parse_date(date_str)
                elif 'Solicitation' in text:
                    tender['organization'] = text.split(':')[-1].strip()
                    
            # Set default ID if not found
            if not tender['tender_id']:
                tender['tender_id'] = f"MERX_{datetime.now().timestamp()}"
                
            # Extract categories and keywords
            tender['categories'] = self._extract_categories_from_text(title)
            tender['keywords'] = self._extract_keywords_from_text(title)
            
            return tender
            
        except Exception as e:
            logger.error(f"Error parsing MERX opportunity: {e}")
            return None
    
    async def scan_biddingo(self, portal_name: str, config: Dict) -> List[Dict]:
        """Scan Biddingo-based portals"""
        tenders = []
        driver = None
        
        try:
            driver = self.selenium.get_driver()
            driver.get('https://www.biddingo.com/')
            sleep(3)
            
            # Search for organization
            search_box = driver.find_element(By.ID, "search-input")
            search_box.send_keys(config.get('biddingo_org', portal_name))
            search_box.send_keys(Keys.ENTER)
            sleep(3)
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opportunities = soup.find_all('div', class_='opportunity-card')
            
            for opp in opportunities[:30]:
                tender = self._parse_biddingo_opportunity(opp, portal_name)
                if tender and self._is_training_related(tender):
                    tenders.append(tender)
                    
        except Exception as e:
            logger.error(f"Error scanning Biddingo for {portal_name}: {e}")
        finally:
            if driver:
                driver.quit()
                
        return tenders
    
    def _parse_biddingo_opportunity(self, soup_element, portal_name) -> Optional[Dict]:
        """Parse Biddingo opportunity"""
        try:
            title = soup_element.find('h3', class_='opportunity-title')
            if not title:
                return None
                
            tender = {
                'tender_id': soup_element.get('data-id', f"BIDDINGO_{datetime.now().timestamp()}"),
                'title': title.text.strip(),
                'organization': portal_name,
                'portal': portal_name,
                'portal_url': PORTAL_CONFIGS.get(portal_name.lower().replace(' ', '_'), {}).get('url', ''),
                'value': 0,
                'closing_date': None,
                'posted_date': None,
                'description': '',
                'location': portal_name.split()[-1],  # Extract city from portal name
                'tender_url': 'https://www.biddingo.com' + soup_element.find('a')['href'],
                'categories': [],
                'keywords': []
            }
            
            # Extract dates and other info
            info_items = soup_element.find_all('span', class_='info-item')
            for item in info_items:
                text = item.text.strip()
                if 'Closes' in text:
                    tender['closing_date'] = self._parse_date(text.split(':')[-1].strip())
                elif 'Posted' in text:
                    tender['posted_date'] = self._parse_date(text.split(':')[-1].strip())
                    
            # Extract description
            desc_elem = soup_element.find('p', class_='opportunity-description')
            if desc_elem:
                tender['description'] = desc_elem.text.strip()
                
            # Extract categories and keywords
            full_text = f"{tender['title']} {tender['description']}"
            tender['categories'] = self._extract_categories_from_text(full_text)
            tender['keywords'] = self._extract_keywords_from_text(full_text)
            
            return tender
            
        except Exception as e:
            logger.error(f"Error parsing Biddingo opportunity: {e}")
            return None
    
    async def scan_bcbid(self) -> List[Dict]:
        """Scan BC Bid portal"""
        tenders = []
        driver = None
        
        try:
            driver = self.selenium.get_driver()
            driver.get(PORTAL_CONFIGS['bcbid']['url'])
            sleep(3)
            
            # Click on opportunities
            opp_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Opportunities"))
            )
            opp_link.click()
            sleep(3)
            
            # Search for training
            search_input = driver.find_element(By.NAME, "txtKeyword")
            search_input.send_keys("training professional development education")
            
            # Submit search
            search_button = driver.find_element(By.NAME, "btnSearch")
            search_button.click()
            sleep(3)
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find opportunity table
            opp_table = soup.find('table', id='tblOpportunities')
            if opp_table and hasattr(opp_table, 'find_all'):  # Ensure it's a Tag, not NavigableString
                rows = opp_table.find_all('tr')[1:]  # Skip header
                
                for row in rows[:30]:
                    tender = self._parse_bcbid_row(row)
                    if tender and self._is_training_related(tender):
                        tenders.append(tender)
                        
        except Exception as e:
            logger.error(f"Error scanning BC Bid: {e}")
        finally:
            if driver:
                driver.quit()
                
        return tenders
    
    def _parse_bcbid_row(self, soup_element) -> Optional[Dict]:
        """Parse BC Bid table row"""
        try:
            cells = soup_element.find_all('td')
            if len(cells) < 4:
                return None
                
            tender = {
                'tender_id': cells[0].text.strip(),
                'title': cells[1].text.strip(),
                'organization': cells[2].text.strip() if len(cells) > 2 else 'BC Government',
                'portal': 'BC Bid',
                'portal_url': PORTAL_CONFIGS['bcbid']['url'],
                'value': 0,
                'closing_date': self._parse_date(cells[3].text.strip()) if len(cells) > 3 else None,
                'posted_date': datetime.utcnow(),
                'description': '',
                'location': 'British Columbia',
                'tender_url': PORTAL_CONFIGS['bcbid']['url'],
                'categories': [],
                'keywords': []
            }
            
            # Try to get link
            link = cells[1].find('a')
            if link:
                tender['tender_url'] = PORTAL_CONFIGS['bcbid']['url'] + link.get('href', '')
                
            # Extract categories and keywords
            tender['categories'] = self._extract_categories_from_text(tender['title'])
            tender['keywords'] = self._extract_keywords_from_text(tender['title'])
            
            return tender
            
        except Exception as e:
            logger.error(f"Error parsing BC Bid row: {e}")
            return None
    
    async def scan_seao(self) -> List[Dict]:
        """Scan SEAO Quebec portal"""
        tenders = []
        driver = None
        
        try:
            driver = self.selenium.get_driver()
            driver.get(PORTAL_CONFIGS['seao']['search_url'])
            sleep(3)
            
            # Enter search keywords
            keyword_input = driver.find_element(By.ID, "ctl00_ContenuPrincipal_rech_PublicWordsTxt")
            keyword_input.send_keys("formation développement professionnel training education")
            
            # Select categories related to training
            categories = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            for cat in categories:
                label_text = cat.get_attribute('aria-label') or ''
                if any(keyword in label_text.lower() for keyword in ['formation', 'éducation', 'training', 'service']):
                    cat.click()
            
            # Submit search
            search_button = driver.find_element(By.ID, "ctl00_ContenuPrincipal_rech_PublicRechercherBtn")
            search_button.click()
            sleep(3)
            
            # Parse results
            page_count = 0
            while page_count < 3:
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Find opportunity rows
                opportunities = soup.find_all('tr', class_='resultat')
                
                for opp in opportunities:
                    tender = self._parse_seao_opportunity(opp)
                    if tender and self._is_training_related(tender):
                        tenders.append(tender)
                
                # Next page
                try:
                    next_link = driver.find_element(By.LINK_TEXT, "Suivant")
                    next_link.click()
                    sleep(3)
                    page_count += 1
                except NoSuchElementException:
                    break
                    
        except Exception as e:
            logger.error(f"Error scanning SEAO: {e}")
        finally:
            if driver:
                driver.quit()
                
        return tenders
    
    def _parse_seao_opportunity(self, soup_element) -> Optional[Dict]:
        """Parse SEAO opportunity"""
        try:
            # Extract number and title
            num_elem = soup_element.find('td', class_='numero')
            title_elem = soup_element.find('td', class_='description')
            
            if not num_elem or not title_elem:
                return None
                
            tender = {
                'tender_id': num_elem.text.strip(),
                'title': title_elem.text.strip(),
                'organization': '',
                'portal': 'SEAO Quebec',
                'portal_url': PORTAL_CONFIGS['seao']['url'],
                'value': 0,
                'closing_date': None,
                'posted_date': None,
                'description': '',
                'location': 'Quebec',
                'tender_url': '',
                'categories': [],
                'keywords': []
            }
            
            # Get link
            link = title_elem.find('a')
            if link:
                tender['tender_url'] = 'https://www.seao.ca' + link.get('href', '')
                
            # Extract organization
            org_elem = soup_element.find('td', class_='organisme')
            if org_elem:
                tender['organization'] = org_elem.text.strip()
                
            # Extract dates
            date_elem = soup_element.find('td', class_='dateOuverture')
            if date_elem:
                tender['closing_date'] = self._parse_date(date_elem.text.strip())
                
            # Extract categories and keywords
            tender['categories'] = self._extract_categories_from_text(tender['title'])
            tender['keywords'] = self._extract_keywords_from_text(tender['title'])
            
            return tender
            
        except Exception as e:
            logger.error(f"Error parsing SEAO opportunity: {e}")
            return None
    
    async def scan_seao_api(self) -> List[Dict]:
        """Scan SEAO Quebec using their open data API"""
        tenders = []
        session = await self.get_session()
        
        try:
            # Check if API is working (based on configuration)
            if PORTAL_CONFIGS['seao'].get('api_working', False) == False:
                logger.warning("SEAO API endpoints are not working, skipping API scan")
                return tenders
            
            # Get current year and month for API endpoints
            current_date = datetime.now()
            year = current_date.year
            month = current_date.month
            
            # Try weekly and monthly endpoints
            api_endpoints = [
                f"https://www.donneesquebec.ca/recherche/dataset/d23b2e02-085d-43e5-9e6e-e1d558ebfdd5/resource/*/download/hebdo_{year}.json",
                f"https://www.donneesquebec.ca/recherche/dataset/d23b2e02-085d-43e5-9e6e-e1d558ebfdd5/resource/*/download/mensuel_{year}_{month:02d}.json"
            ]
            
            for endpoint in api_endpoints:
                try:
                    logger.info(f"Fetching SEAO API data from {endpoint}")
                    async with session.get(endpoint) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if isinstance(data, list):
                                for item in data:
                                    tender = self._parse_seao_api_item(item)
                                    if tender and self._is_training_related(tender):
                                        tenders.append(tender)
                            elif isinstance(data, dict) and 'results' in data:
                                for item in data['results']:
                                    tender = self._parse_seao_api_item(item)
                                    if tender and self._is_training_related(tender):
                                        tenders.append(tender)
                        else:
                            logger.warning(f"SEAO API endpoint {endpoint} returned status {response.status}")
                                        
                except Exception as e:
                    logger.error(f"Error fetching SEAO API endpoint {endpoint}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scanning SEAO API: {e}")
            
        return tenders
    
    def _parse_seao_api_item(self, item: Dict) -> Optional[Dict]:
        """Parse an item from SEAO API response"""
        try:
            tender = {
                'tender_id': str(item.get('numero', '')),
                'title': str(item.get('titre', '')),
                'organization': str(item.get('organisme', '')),
                'portal': 'SEAO Quebec',
                'portal_url': PORTAL_CONFIGS['seao']['url'],
                'value': self._parse_value(item.get('valeur_estimee', 0)),
                'closing_date': self._parse_date(item.get('date_fermeture', '')),
                'posted_date': self._parse_date(item.get('date_publication', '')),
                'description': str(item.get('description', '')),
                'location': str(item.get('region', 'Quebec')),
                'tender_url': f"https://www.seao.ca/OpportunityPublication/opportunite.aspx?no={item.get('numero', '')}",
                'categories': [],
                'keywords': []
            }
            
            # Extract categories and keywords
            full_text = f"{tender['title']} {tender['description']}"
            tender['categories'] = self._extract_categories_from_text(full_text)
            tender['keywords'] = self._extract_keywords_from_text(full_text)
            
            return tender if tender['tender_id'] else None
            
        except Exception as e:
            logger.error(f"Error parsing SEAO API item: {e}")
            return None
    
    def _extract_description_from_soup(self, soup) -> str:
        """Extract description from various portal formats"""
        description = ""
        
        # Try common description selectors
        selectors = [
            'div.description',
            'div.tender-description',
            'div.opportunity-description',
            'div.content',
            'div.details',
            'p.description',
            'td.description'
        ]
        
        for selector in selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                description = desc_elem.text.strip()
                break
                
        # If no description found, try to get first paragraph
        if not description:
            p_elem = soup.find('p')
            if p_elem:
                description = p_elem.text.strip()
                
        return description[:1000]  # Limit description length
    
    def _parse_date_text(self, date_text: str) -> Optional[datetime]:
        """Parse date text from various formats (Toronto scraper style)"""
        if not date_text:
            return None
            
        # Clean the date text
        date_text = date_text.strip()
        
        # Remove extra text
        date_parts = date_text.split()[:3]  # Usually "DD Mon YYYY"
        clean_date = ' '.join(date_parts)
        
        try:
            return datetime.strptime(clean_date, "%d %b %Y")
        except ValueError:
            # Try other formats
            return self._parse_date(date_text)
    
    def _is_training_related(self, tender: Dict) -> bool:
        """Enhanced training detection - temporarily less restrictive for testing"""
        text = f"{tender.get('title', '')} {tender.get('description', '')}".lower()
        
        # For testing, accept any tender that has a title and description
        if tender.get('title') and tender.get('description'):
            return True
            
        # Extended training keywords (original logic)
        training_keywords = [
            'training', 'formation', 'education', 'éducation', 'learning', 'apprentissage',
            'development', 'développement', 'coaching', 'certification', 'course', 'cours',
            'workshop', 'atelier', 'seminar', 'séminaire', 'instruction', 'enseignement',
            'professional development', 'développement professionnel', 'upskilling',
            'reskilling', 'curriculum', 'programme', 'instructor', 'instructeur',
            'facilitation', 'e-learning', 'mentoring', 'mentorat', 'tutorial', 'tutoriel',
            'capacity building', 'renforcement des capacités', 'skill', 'compétence'
        ]
        
        return any(keyword in text for keyword in training_keywords)
    
    def _extract_categories_from_text(self, text: str) -> List[str]:
        """Extract categories based on text content"""
        categories = []
        text_lower = text.lower()
        
        for category, config in TKA_COURSES.items():
            # Check if at least 2 keywords match
            matches = sum(1 for keyword in config['keywords'] if keyword in text_lower)
            if matches >= 2:
                categories.append(category)
                
        return categories
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract keywords from text"""
        text_lower = text.lower()
        keywords = []
        
        for category, config in TKA_COURSES.items():
            for keyword in config['keywords']:
                if keyword in text_lower and keyword not in keywords:
                    keywords.append(keyword)
                    
        return keywords[:10]  # Limit keywords
    
    def _parse_value(self, value_str) -> float:
        """Parse monetary value from string"""
        if not value_str:
            return 0.0
            
        value_str = str(value_str)
        
        # Remove currency symbols, commas, spaces, and text
        value_str = re.sub(r'[^0-9.,]', '', value_str)
        value_str = value_str.replace(',', '')
        
        try:
            return float(value_str)
        except:
            return 0.0
    
    def _parse_date(self, date_str) -> Optional[datetime]:
        """Parse date from various formats"""
        if not date_str:
            return None
            
        date_str = str(date_str).strip()
        
        # Common date formats in Canadian procurement
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y-%m-%d %H:%M:%S',
            '%d-%b-%Y',
            '%d %b %Y',
            '%B %d, %Y',
            '%d %B %Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%b %d, %Y',
            '%d %b %Y %I:%M %p'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
                
        # Try pandas parser as last resort
        try:
            return pd.to_datetime(date_str, errors='coerce')
        except:
            return None
    
    async def scan_bidsandtenders_portal(self, portal_name: str, search_url: str) -> List[Dict]:
        """Scan bids&tenders platform portals"""
        tenders = []
        driver = None
        
        try:
            driver = self.selenium.get_driver()
            driver.get(search_url)
            sleep(3)
            
            # Look for search functionality
            try:
                # Try to find search box
                search_selectors = [
                    "input[type='text']",
                    "input[name='search']",
                    "input[id*='search']",
                    "input[placeholder*='search']",
                    "input[placeholder*='Search']"
                ]
                
                search_box = None
                for selector in search_selectors:
                    try:
                        search_box = driver.find_element(By.CSS_SELECTOR, selector)
                        break
                    except NoSuchElementException:
                        continue
                
                if search_box:
                    search_box.clear()
                    search_box.send_keys("training professional development education coaching")
                    search_box.send_keys(Keys.ENTER)
                    sleep(3)
                else:
                    # If no search box, try to find tender listings directly
                    logger.info(f"No search box found on {portal_name}, looking for direct listings")
                    
            except Exception as e:
                logger.warning(f"Could not perform search on {portal_name}: {e}")
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Look for tender listings with various selectors
            tender_selectors = [
                'tr[class*="tender"]',
                'div[class*="tender"]',
                'div[class*="opportunity"]',
                'tr[class*="opportunity"]',
                'div[class*="bid"]',
                'tr[class*="bid"]'
            ]
            
            tender_elements = []
            for selector in tender_selectors:
                elements = soup.select(selector)
                if elements:
                    tender_elements = elements
                    break
            
            if not tender_elements:
                # Fallback: look for any table rows or divs that might contain tender info
                # Try different selectors without lambda
                for selector in ['tr', 'div']:
                    elements = soup.find_all(selector)
                    for element in elements:
                        if element.get('class'):
                            class_str = ' '.join(element.get('class')).lower()
                            if any(keyword in class_str for keyword in ['tender', 'opportunity', 'bid', 'rfp']):
                                tender_elements.append(element)
                    if tender_elements:
                        break
            
            logger.info(f"Found {len(tender_elements)} potential tender elements on {portal_name}")
            
            for element in tender_elements[:30]:  # Limit to prevent long runs
                tender = self._parse_bidsandtenders_element(element, portal_name, search_url)
                if tender and self._is_training_related(tender):
                    tenders.append(tender)
                    
        except Exception as e:
            logger.error(f"Error scanning bids&tenders portal {portal_name}: {e}")
        finally:
            if driver:
                driver.quit()
                
        return tenders
    
    def _parse_bidsandtenders_element(self, soup_element, portal_name: str, base_url: str) -> Optional[Dict]:
        """Parse a tender element from bids&tenders platform"""
        try:
            # Try to extract tender information from various element structures
            tender = {
                'tender_id': '',
                'title': '',
                'organization': portal_name,
                'portal': portal_name,
                'portal_url': base_url,
                'value': 0,
                'closing_date': None,
                'posted_date': None,
                'description': '',
                'location': portal_name.split()[-1] if 'City' in portal_name else 'Canada',
                'tender_url': base_url,
                'categories': [],
                'keywords': []
            }
            
            # Extract title from various possible elements
            title_selectors = ['h3', 'h4', 'a', 'td', 'div[class*="title"]', 'span[class*="title"]']
            for selector in title_selectors:
                title_elem = soup_element.select_one(selector)
                if title_elem and title_elem.text.strip():
                    tender['title'] = title_elem.text.strip()
                    # Try to get URL from link
                    if title_elem.name == 'a' and title_elem.get('href'):
                        href = title_elem.get('href')
                        if href.startswith('http'):
                            tender['tender_url'] = href
                        else:
                            tender['tender_url'] = base_url.rstrip('/') + '/' + href.lstrip('/')
                    break
            
            # Extract tender ID from various sources
            if not tender['tender_id']:
                # Try to find ID in text content
                text_content = soup_element.get_text()
                id_match = re.search(r'(?:Tender|Bid|RFP|Opportunity)\s*(?:#|No\.?|Number)?\s*([A-Z0-9\-]+)', text_content, re.IGNORECASE)
                if id_match:
                    tender['tender_id'] = id_match.group(1)
                else:
                    tender['tender_id'] = f"BIDSANDTENDERS_{datetime.now().timestamp()}"
            
            # Extract dates
            date_patterns = [
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YYYY or DD-MM-YYYY
                r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
                r'(\w+\s+\d{1,2},?\s+\d{4})',  # Month DD, YYYY
            ]
            
            text_content = soup_element.get_text()
            for pattern in date_patterns:
                matches = re.findall(pattern, text_content)
                if matches:
                    try:
                        parsed_date = self._parse_date(matches[0])
                        if parsed_date and not tender['closing_date']:
                            tender['closing_date'] = parsed_date
                        elif parsed_date and not tender['posted_date']:
                            tender['posted_date'] = parsed_date
                    except:
                        continue
            
            # Extract description
            desc_selectors = ['p', 'div[class*="desc"]', 'span[class*="desc"]', 'td']
            for selector in desc_selectors:
                desc_elem = soup_element.select_one(selector)
                if desc_elem and desc_elem.text.strip() and desc_elem.text.strip() != tender['title']:
                    tender['description'] = desc_elem.text.strip()[:500]  # Limit length
                    break
            
            # Extract categories and keywords
            full_text = f"{tender['title']} {tender['description']}"
            tender['categories'] = self._extract_categories_from_text(full_text)
            tender['keywords'] = self._extract_keywords_from_text(full_text)
            
            return tender if tender['title'] else None
            
        except Exception as e:
            logger.error(f"Error parsing bids&tenders element: {e}")
            return None

class TenderMatcher:
    """Match tenders with TKA courses"""
    
    @staticmethod
    def match_courses(tender: Dict) -> List[str]:
        """Find matching TKA courses for a tender"""
        matching_courses = []
        
        tender_text = f"{tender.get('title', '')} {tender.get('description', '')} {' '.join(tender.get('keywords', []))}".lower()
        
        for category in tender.get('categories', []):
            if category in TKA_COURSES:
                config = TKA_COURSES[category]
                
                # Check each course
                for course in config['courses']:
                    course_keywords = course.lower().split()
                    
                    # Match if course name appears in tender or keywords match
                    if course.lower() in tender_text:
                        matching_courses.append(course)
                    elif any(kw in tender_text for kw in course_keywords if len(kw) > 3):
                        matching_courses.append(course)
                    elif any(kw in tender_text for kw in config['keywords'][:5]):
                        matching_courses.append(course)
        
        return list(set(matching_courses))[:5]  # Limit to 5 courses
    
    @staticmethod
    def calculate_priority(tender: Dict) -> str:
        """Calculate tender priority based on multiple factors"""
        value = tender.get('value', 0)
        closing_date = tender.get('closing_date')
        matching_courses = tender.get('matching_courses', [])
        categories = tender.get('categories', [])
        
        if not closing_date:
            return 'low'
        
        days_until_closing = (closing_date - datetime.utcnow()).days
        
        # High priority criteria
        if (value > 1000000 or 
            days_until_closing < 7 or 
            len(matching_courses) >= 3 or
            len(categories) >= 2):
            return 'high'
        # Medium priority criteria
        elif (value > 500000 or 
              days_until_closing < 14 or 
              len(matching_courses) >= 1):
            return 'medium'
        else:
            return 'low'

def save_tender_to_db(db: Session, tender_data: Dict) -> bool:
    """
    Saves a new tender or updates an existing one in the database.

    This function checks if a tender with the given tender_id already exists.
    If it does, it compares a hash of the content to see if an update is needed.
    If it doesn't exist, it creates a new record.

    Args:
        db (Session): The SQLAlchemy database session.
        tender_data (Dict): A dictionary containing the tender's information.

    Returns:
        bool: True if a new tender was created, False otherwise (updated or no change).
    """
    try:
        # The tender_id is the unique identifier from the portal
        tender_id = tender_data.get('tender_id')
        if not tender_id:
            logger.warning("Skipping tender with no tender_id.")
            return False

        # Generate a hash of the tender's data to easily detect changes
        tender_hash = hashlib.md5(
            json.dumps(tender_data, sort_keys=True, default=str).encode()
        ).hexdigest()

        # Check if a tender with this ID already exists in the database
        existing_tender = db.query(Tender).filter_by(tender_id=tender_id).first()

        if existing_tender:
            # If the tender exists, check if its content has changed
            if existing_tender.hash != tender_hash:
                logger.info(f"Updating tender: {tender_id}")
                # Update all attributes of the existing tender object
                for key, value in tender_data.items():
                    # JSON fields must be converted to strings
                    if key in ['categories', 'keywords', 'matching_courses', 'attachments']:
                        setattr(existing_tender, key, json.dumps(value or []))
                    else:
                        setattr(existing_tender, key, value)
                
                existing_tender.hash = tender_hash
                existing_tender.last_updated = datetime.utcnow()
                db.commit()
            return False  # Indicates an update or no change
        else:
            # If the tender is new, create a new Tender object
            logger.info(f"Creating new tender: {tender_id}")
            new_tender = Tender(
                # The primary key for our database
                id=f"{tender_data.get('portal', 'unknown')}_{tender_id}",
                hash=tender_hash,
                # Unpack all other keys from the dictionary
                **{k: v for k, v in tender_data.items()
                   if k not in ['categories', 'keywords', 'matching_courses', 'attachments']}
            )
            # Handle JSON fields separately for the new object
            new_tender.categories = json.dumps(tender_data.get('categories', []))
            new_tender.keywords = json.dumps(tender_data.get('keywords', []))
            new_tender.matching_courses = json.dumps(tender_data.get('matching_courses', []))
            new_tender.attachments = json.dumps(tender_data.get('attachments', []))

            db.add(new_tender)
            db.commit()
            return True  # Indicates a new tender was created

    except Exception as e:
        logger.error(f"Error saving tender {tender_data.get('tender_id', 'unknown')} to DB: {e}")
        db.rollback()  # Roll back the transaction in case of an error
        return False

# Scheduled job manager
scheduler = AsyncIOScheduler()

async def scan_all_portals():
    """Scan all configured portals for new tenders"""
    logger.info("Starting comprehensive portal scan...")
    
    scanner = ProcurementScanner()
    all_tenders = []
    
    try:
        # Federal portals with APIs
        logger.info("Scanning CanadaBuys Open Data...")
        all_tenders.extend(await scanner.scan_canadabuys())
        
        logger.info("Scanning MERX...")
        all_tenders.extend(await scanner.scan_merx())
        
        # Provincial portals
        logger.info("Scanning BC Bid...")
        all_tenders.extend(await scanner.scan_bcbid())
        
        # Quebec with API
        logger.info("Scanning SEAO Quebec API...")
        all_tenders.extend(await scanner.scan_seao_api())
        
        logger.info("Scanning SEAO Quebec (web scrape)...")
        all_tenders.extend(await scanner.scan_seao())
        
        # Municipal portals
        for portal_id, config in PORTAL_CONFIGS.items():
            # Skip portals marked as not working
            if config.get('working', True) == False:
                logger.info(f"Skipping {config['name']} - marked as not working")
                continue
                
            portal_type = config.get('type')
            
            if portal_type == 'ariba':
                logger.info(f"Scanning {config['name']} (Ariba)...")
                tenders = await scanner.scan_ariba_portal(config['name'], config)
                all_tenders.extend(tenders)
            elif portal_type == 'bidsandtenders':
                logger.info(f"Scanning {config['name']} (bids&tenders)...")
                tenders = await scanner.scan_bidsandtenders_portal(config['name'], config['search_url'])
                all_tenders.extend(tenders)
            elif portal_type == 'biddingo':
                logger.info(f"Scanning {config['name']} (Biddingo)...")
                tenders = await scanner.scan_biddingo(config['name'], config)
                all_tenders.extend(tenders)
            elif portal_type == 'sasktenders' and portal_id not in ['sasktenders']:
                # Municipal portals using SaskTenders
                logger.info(f"Scanning {config['name']} via SaskTenders...")
                # Will be handled by scrapers.py
        
        # Save to database
        db = SessionLocal()
        matcher = TenderMatcher()
        new_count = 0
        updated_count = 0
        
        for tender_data in all_tenders:
            # Add matching courses and priority
            tender_data['matching_courses'] = matcher.match_courses(tender_data)
            tender_data['priority'] = matcher.calculate_priority(tender_data)
            
            # Use our new, centralized function
            was_new = save_tender_to_db(db, tender_data)
            if was_new:
                new_count += 1
            else:
                # This counts both updates and tenders that were unchanged
                updated_count += 1
        
        # Mark expired tenders after processing all current ones
        expired = db.query(Tender).filter(
            Tender.closing_date < datetime.utcnow(),
            Tender.is_active == True
        ).update({'is_active': False})
        db.commit()
        
        db.close()
        logger.info(f"Scan complete. Found {len(all_tenders)} tenders. New: {new_count}, Updated: {updated_count}, Expired: {expired}")
        
    except Exception as e:
        logger.error(f"Error in scan_all_portals: {e}")
    finally:
        await scanner.close_session()

# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting procurement scanner...")
    
    # Schedule scans
    scheduler.add_job(scan_all_portals, 'interval', hours=1, id='hourly_scan')
    scheduler.add_job(scan_all_portals, 'cron', hour=7, minute=0, id='morning_scan')
    scheduler.add_job(scan_all_portals, 'cron', hour=13, minute=0, id='afternoon_scan')
    scheduler.start()
    
    # Run initial scan in background
    asyncio.create_task(scan_all_portals())
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    logger.info("Shutting down procurement scanner...")

app = FastAPI(
    title="Canadian Procurement Scanner API",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Endpoints
@app.get("/api/tenders", response_model=List[TenderResponse])
async def get_tenders(
    skip: int = 0,
    limit: int = 100,
    portal: Optional[str] = None,
    min_value: Optional[float] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all active tenders with optional filters"""
    query = db.query(Tender).filter(Tender.is_active == True)
    
    if portal:
        query = query.filter(Tender.portal == portal)
    
    if min_value:
        query = query.filter(Tender.value >= min_value)
    
    if category:
        query = query.filter(Tender.categories.contains(f'"{category}"'))
    
    if priority:
        query = query.filter(Tender.priority == priority)
        
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            or_(
                Tender.title.ilike(search_pattern),
                Tender.description.ilike(search_pattern),
                Tender.organization.ilike(search_pattern)
            )
        )
    
    # Order by closing date (soonest first) and priority
    query = query.order_by(Tender.closing_date, Tender.priority.desc())
    
    tenders = query.offset(skip).limit(limit).all()
    
    # Convert to response model
    results = []
    for tender in tenders:
        tender_dict = {
            'id': tender.id,
            'tender_id': tender.tender_id,
            'title': tender.title,
            'organization': tender.organization,
            'portal': tender.portal,
            'value': tender.value,
            'closing_date': tender.closing_date,
            'posted_date': tender.posted_date,
            'description': tender.description or '',
            'location': tender.location,
            'categories': json.loads(tender.categories) if tender.categories else [],
            'keywords': json.loads(tender.keywords) if tender.keywords else [],
            'tender_url': tender.tender_url,
            'matching_courses': json.loads(tender.matching_courses) if tender.matching_courses else [],
            'priority': tender.priority
        }
        results.append(TenderResponse(**tender_dict))
    
    return results

@app.get("/api/stats", response_model=StatsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """Get procurement statistics"""
    # Total active tenders
    total_tenders = db.query(Tender).filter(Tender.is_active == True).count()
    
    # Total value
    total_value = db.query(func.sum(Tender.value)).filter(Tender.is_active == True).scalar() or 0
    
    # By portal
    by_portal = db.query(
        Tender.portal,
        func.count(Tender.id).label('count'),
        func.sum(Tender.value).label('value')
    ).filter(Tender.is_active == True).group_by(Tender.portal).all()
    
    # By category
    all_categories = {}
    tenders = db.query(Tender.categories).filter(Tender.is_active == True).all()
    for (categories_json,) in tenders:
        if categories_json:
            categories = json.loads(categories_json)
            for cat in categories:
                all_categories[cat] = all_categories.get(cat, 0) + 1
    
    # Closing soon (within 7 days)
    closing_soon = db.query(Tender).filter(
        Tender.is_active == True,
        Tender.closing_date <= datetime.utcnow() + timedelta(days=7),
        Tender.closing_date > datetime.utcnow()
    ).count()
    
    # New today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_today = db.query(Tender).filter(
        Tender.posted_date >= today_start
    ).count()
    
    # Last scan time
    last_scan = db.query(func.max(Tender.last_updated)).scalar()
    
    return StatsResponse(
        total_tenders=total_tenders,
        total_value=float(total_value),
        by_portal=[
            {"portal": p[0], "count": p[1], "value": float(p[2] or 0)} 
            for p in by_portal
        ],
        by_category=all_categories,
        closing_soon=closing_soon,
        new_today=new_today,
        last_scan=last_scan
    )

@app.post("/api/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Manually trigger a scan of all portals"""
    background_tasks.add_task(scan_all_portals)
    return {"message": "Scan initiated", "status": "processing"}

@app.get("/api/portals")
async def get_portals():
    """Get list of all monitored portals with their status"""
    db = SessionLocal()
    portal_stats = []
    
    for portal_id, config in PORTAL_CONFIGS.items():
        count = db.query(Tender).filter(
            Tender.portal == config['name'],
            Tender.is_active == True
        ).count()
        
        last_update = db.query(func.max(Tender.last_updated)).filter(
            Tender.portal == config['name']
        ).scalar()
        
        portal_stats.append({
            "id": portal_id,
            "name": config['name'],
            "type": config['type'],
            "url": config.get('url', ''),
            "active_tenders": count,
            "last_update": last_update,
            "requires_selenium": config.get('requires_selenium', False)
        })
    
    db.close()
    return {"portals": portal_stats}

@app.get("/api/tender/{tender_id}")
async def get_tender_detail(tender_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific tender"""
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Increment download count
    tender.download_count += 1
    db.commit()
    
    return {
        "id": tender.id,
        "tender_id": tender.tender_id,
        "title": tender.title,
        "organization": tender.organization,
        "portal": tender.portal,
        "value": tender.value,
        "closing_date": tender.closing_date,
        "posted_date": tender.posted_date,
        "description": tender.description,
        "location": tender.location,
        "categories": json.loads(tender.categories) if tender.categories else [],
        "keywords": json.loads(tender.keywords) if tender.keywords else [],
        "matching_courses": json.loads(tender.matching_courses) if tender.matching_courses else [],
        "tender_url": tender.tender_url,
        "documents_url": tender.documents_url,
        "contact_email": tender.contact_email,
        "contact_phone": tender.contact_phone,
        "priority": tender.priority,
        "download_count": tender.download_count,
        "last_updated": tender.last_updated,
        "attachments": json.loads(tender.attachments) if tender.attachments else []
    }

@app.get("/api/portal-status")
async def get_portal_status():
    """Check the status of all portal URLs and APIs"""
    portal_status = []
    session = aiohttp.ClientSession()
    
    try:
        for portal_id, config in PORTAL_CONFIGS.items():
            status = {
                "id": portal_id,
                "name": config['name'],
                "type": config['type'],
                "url": config.get('url', ''),
                "status": "unknown",
                "api_status": {}
            }
            
            # Check main URL
            try:
                async with session.get(config.get('url', ''), timeout=aiohttp.ClientTimeout(total=5)) as response:
                    status['status'] = 'online' if response.status < 400 else f'error_{response.status}'
            except:
                status['status'] = 'offline'
            
            # Check API endpoints if available
            if config.get('type') == 'api' and 'apis' in config:
                for api_name, api_url in config['apis'].items():
                    try:
                        async with session.head(api_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                            status['api_status'][api_name] = 'online' if response.status < 400 else f'error_{response.status}'
                    except:
                        status['api_status'][api_name] = 'offline'
            
            portal_status.append(status)
            
    finally:
        await session.close()
    
    return {"portals": portal_status, "timestamp": datetime.utcnow()}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db = SessionLocal()
    try:
        # Check database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    finally:
        db.close()
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow()
    }

@app.get("/api/export/csv")
async def export_csv(
    portal: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Export tenders to CSV format"""
    query = db.query(Tender).filter(Tender.is_active == True)
    
    if portal:
        query = query.filter(Tender.portal == portal)
    if category:
        query = query.filter(Tender.categories.contains(f'"{category}"'))
    
    tenders = query.all()
    
    # Create CSV content
    csv_data = []
    csv_data.append("Tender ID,Title,Organization,Portal,Value,Closing Date,Location,Priority,Matching Courses,URL")
    
    for tender in tenders:
        matching_courses = json.loads(tender.matching_courses) if tender.matching_courses else []
        csv_data.append(
            f'"{tender.tender_id}","{tender.title}","{tender.organization}","{tender.portal}",'
            f'{tender.value},"{tender.closing_date}","{tender.location}","{tender.priority}",'
            f'"{";".join(matching_courses)}","{tender.tender_url}"'
        )
    
    csv_content = "\n".join(csv_data)
    
    from fastapi.responses import Response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tenders_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)