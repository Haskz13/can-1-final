# scrapers.py - Additional portal-specific scrapers
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import pandas as pd
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import hashlib

logger = logging.getLogger(__name__)

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date from various formats"""
    if not date_str:
        return None
        
    date_str = str(date_str).strip()
    
    # Common formats
    formats = [
        '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S',
        '%d-%b-%Y', '%d %b %Y', '%B %d, %Y', '%d %B %Y',
        '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%d-%m-%Y',
        '%b %d, %Y', '%d %b %Y %I:%M %p'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
            
    try:
        return pd.to_datetime(date_str, errors='coerce')
    except:
        return None

def parse_value(value_str: str) -> float:
    """Parse monetary value from string"""
    if not value_str:
        return 0.0
        
    value_str = str(value_str)
    
    # Remove currency symbols and text
    value_str = re.sub(r'[^0-9.,]', '', value_str)
    value_str = value_str.replace(',', '')
    
    try:
        return float(value_str)
    except:
        return 0.0

class ProvincialScrapers:
    """Scrapers for provincial procurement portals"""
    
    @staticmethod
    async def scan_alberta_purchasing(driver, selenium_helper) -> List[Dict]:
        """Scan Alberta Purchasing Connection"""
        tenders = []
        
        try:
            driver.get("https://vendor.purchasingconnection.ca/")
            
            # Navigate to opportunities
            opp_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Opportunities"))
            )
            opp_link.click()
            
            # Search for training
            search_box = driver.find_element(By.ID, "ContentPlaceHolder1_txt_keyword")
            search_box.send_keys("training professional development")
            
            search_btn = driver.find_element(By.ID, "ContentPlaceHolder1_btn_search")
            search_btn.click()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results_table = soup.find('table', id='ContentPlaceHolder1_GridView1')
            
            if results_table:
                rows = results_table.find_all('tr')[1:]  # Skip header
                for row in rows:  # Process ALL rows, not just first 30
                    cells = row.find_all('td')
                    if len(cells) >= 5:
                        tender = {
                            'tender_id': cells[0].text.strip(),
                            'title': cells[1].text.strip(),
                            'organization': cells[2].text.strip(),
                            'portal': 'Alberta Purchasing Connection',
                            'value': 0,
                            'closing_date': parse_date(cells[4].text.strip()),
                            'posted_date': parse_date(cells[3].text.strip()),
                            'location': 'Alberta',
                            'tender_url': 'https://vendor.purchasingconnection.ca/',
                            'description': '',
                            'categories': [],
                            'keywords': []
                        }
                        
                        # Get link if available
                        link = cells[1].find('a')
                        if link and link.get('href'):
                            tender['tender_url'] = 'https://vendor.purchasingconnection.ca/' + str(link.get('href', ''))
                            
                        tenders.append(tender)
                        
        except Exception as e:
            logger.error(f"Error scanning Alberta Purchasing: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_saskatchewan_tenders(driver, selenium_helper) -> List[Dict]:  # type: ignore
        """Scan SaskTenders"""
        tenders = []
        
        try:
            driver.get("https://sasktenders.ca/content/public/Search.aspx")
            
            # Enter search
            keyword_box = driver.find_element(By.ID, "ctl00_ContentPlaceHolder_KeywordTextBox")
            keyword_box.send_keys("training education professional development")
            
            # Submit search
            search_btn = driver.find_element(By.ID, "ctl00_ContentPlaceHolder_SearchButton")
            search_btn.click()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results = soup.find_all('div', class_='tender-result')
            
            for result in results:  # Process ALL results, not just first 30
                org_elem = result.find('span', class_='org')
                organization = org_elem.text.strip() if org_elem and hasattr(org_elem, 'text') and org_elem.text else 'Saskatchewan Government'
                closing_elem = result.find('span', class_='closing')
                closing_date = parse_date(closing_elem.text.strip() if closing_elem and hasattr(closing_elem, 'text') and closing_elem.text else '')
                tender = {
                    'tender_id': result.get('data-tender-id', ''),
                    'title': result.find('h3').text.strip() if result.find('h3') and hasattr(result.find('h3'), 'text') and result.find('h3').text else '',
                    'organization': organization,
                    'portal': 'SaskTenders',
                    'value': 0,
                    'closing_date': closing_date,
                    'posted_date': datetime.utcnow(),
                    'location': 'Saskatchewan',
                    'tender_url': 'https://sasktenders.ca' + str(result.find('a').get('href', '')) if result.find('a') and result.find('a').get('href') else '',
                    'description': '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning SaskTenders: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_manitoba_tenders(session) -> List[Dict]:
        """Scan Manitoba Tenders (non-Selenium)"""
        tenders = []
        
        try:
            async with session.get("https://www.gov.mb.ca/tenders/") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find tender listings
                    tender_links = soup.find_all('a', href=re.compile(r'/tenders/tender_'))
                    
                    for link in tender_links:  # Process ALL links, not just first 30
                        tender = {
                            'tender_id': link.get('href', '').split('/')[-1].replace('.html', ''),
                            'title': link.text.strip(),
                            'organization': 'Manitoba Government',
                            'portal': 'Manitoba Tenders',
                            'value': 0,
                            'closing_date': None,
                            'posted_date': datetime.utcnow(),
                            'location': 'Manitoba',
                            'tender_url': 'https://www.gov.mb.ca' + str(link.get('href', '')),
                            'description': '',
                            'categories': [],
                            'keywords': []
                        }
                        
                        tenders.append(tender)
                        
        except Exception as e:
            logger.error(f"Error scanning Manitoba Tenders: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_ontario_tenders(driver, selenium_helper) -> List[Dict]:
        """Scan Ontario Tenders Portal"""
        tenders = []
        
        try:
            driver.get("https://ontariotenders.ca/page/public/buyer")
            
            # Search for training
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchKeyword"))
            )
            search_input.send_keys("training professional development")
            search_input.submit()
            
            # Wait for results
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "tender-list"))
            )
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tender_items = soup.find_all('div', class_='tender-item')
            
            for item in tender_items:  # Process ALL items, not just first 30
                tender = {
                    'tender_id': item.get('data-id', ''),
                    'title': item.find('h3', class_='tender-title').text.strip() if item.find('h3') else '',
                    'organization': item.find('div', class_='org-name').text.strip() if item.find('div', class_='org-name') else '',
                    'portal': 'Ontario Tenders Portal',
                    'value': parse_value(item.find('span', class_='value').text if item.find('span', class_='value') else '0'),
                    'closing_date': parse_date(item.find('span', class_='closing-date').text if item.find('span', class_='closing-date') else ''),
                    'posted_date': parse_date(item.find('span', class_='posted-date').text if item.find('span', class_='posted-date') else ''),
                    'location': 'Ontario',
                    'tender_url': 'https://ontariotenders.ca' + item.find('a')['href'] if item.find('a') else '',
                    'description': item.find('p', class_='description').text.strip() if item.find('p', class_='description') else '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning Ontario Tenders: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_ns_tenders(driver, selenium_helper) -> List[Dict]:
        """Scan Nova Scotia Tenders"""
        tenders = []
        
        try:
            driver.get("https://novascotia.ca/tenders/tenders/tender-search.aspx")
            
            # Enter search keywords
            keyword_input = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtKeywords")
            keyword_input.send_keys("training professional development education")
            
            # Submit search
            search_btn = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnSearch")
            search_btn.click()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results_table = soup.find('table', id='ctl00_ContentPlaceHolder1_gvTenders')
            
            if results_table:
                rows = results_table.find_all('tr')[1:]  # Skip header  
                for row in rows:  # Process ALL rows, not just first 30
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        tender = {
                            'tender_id': cells[0].text.strip(),
                            'title': cells[1].text.strip(),
                            'organization': cells[2].text.strip(),
                            'portal': 'Nova Scotia Tenders',
                            'value': 0,
                            'closing_date': parse_date(cells[3].text.strip()),
                            'posted_date': datetime.utcnow(),
                            'location': 'Nova Scotia',
                            'tender_url': 'https://novascotia.ca/tenders/',
                            'description': '',
                            'categories': [],
                            'keywords': []
                        }
                        
                        tenders.append(tender)
                        
        except Exception as e:
            logger.error(f"Error scanning NS Tenders: {e}")
            
        return tenders

class MunicipalScrapers:
    """Scrapers for municipal procurement portals"""
    
    @staticmethod
    async def scan_ottawa_bids(driver, selenium_helper) -> List[Dict]:
        """Scan Ottawa Bids and Tenders"""
        tenders = []
        
        try:
            driver.get("https://ottawa.bidsandtenders.ca/Module/Tenders/en")
            
            # Search for training
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchTb"))
            )
            search_box.send_keys("training professional development")
            search_box.submit()
            
            # Wait for results
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "tender-row"))
            )
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tender_rows = soup.find_all('tr', class_='tender-row')
            
            for row in tender_rows[:30]:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    tender = {
                        'tender_id': cells[0].text.strip(),
                        'title': cells[1].text.strip(),
                        'organization': 'City of Ottawa',
                        'portal': 'City of Ottawa',
                        'value': 0,
                        'closing_date': parse_date(cells[3].text.strip()),
                        'posted_date': parse_date(cells[2].text.strip()),
                        'location': 'Ottawa',
                        'tender_url': 'https://ottawa.bidsandtenders.ca' + cells[1].find('a')['href'] if cells[1].find('a') else '',
                        'description': '',
                        'categories': [],
                        'keywords': []
                    }
                    
                    tenders.append(tender)
                    
        except Exception as e:
            logger.error(f"Error scanning Ottawa Bids: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_edmonton_bids(driver, selenium_helper) -> List[Dict]:
        """Scan Edmonton Bids and Tenders"""
        tenders = []
        
        try:
            driver.get("https://edmonton.bidsandtenders.ca/Module/Tenders/en")
            
            # Similar structure to Ottawa
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchTb"))
            )
            search_box.send_keys("training development education")
            search_box.submit()
            
            # Wait and parse
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "tender-row"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tender_rows = soup.find_all('tr', class_='tender-row')
            
            for row in tender_rows:  # Process ALL rows, not just first 30
                cells = row.find_all('td')
                if len(cells) >= 4:
                    tender = {
                        'tender_id': cells[0].text.strip(),
                        'title': cells[1].text.strip(),
                        'organization': 'City of Edmonton',
                        'portal': 'City of Edmonton',
                        'value': 0,
                        'closing_date': parse_date(cells[3].text.strip()),
                        'posted_date': parse_date(cells[2].text.strip()),
                        'location': 'Edmonton',
                        'tender_url': 'https://edmonton.bidsandtenders.ca' + cells[1].find('a')['href'] if cells[1].find('a') else '',
                        'description': '',
                        'categories': [],
                        'keywords': []
                    }
                    
                    tenders.append(tender)
                    
        except Exception as e:
            logger.error(f"Error scanning Edmonton Bids: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_calgary_procurement(driver, selenium_helper) -> List[Dict]:
        """Scan Calgary Procurement"""
        tenders = []
        
        try:
            driver.get("https://procurement.calgary.ca/")
            
            # Navigate to opportunities
            opp_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Current Opportunities"))
            )
            opp_link.click()
            
            # Search
            search_input = driver.find_element(By.ID, "keyword-search")
            search_input.send_keys("training professional development")
            search_input.submit()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opportunities = soup.find_all('div', class_='opportunity')
            
            for opp in opportunities[:30]:
                tender = {
                    'tender_id': opp.get('data-id', ''),
                    'title': opp.find('h3').text.strip() if opp.find('h3') else '',
                    'organization': 'City of Calgary',
                    'portal': 'City of Calgary',
                    'value': parse_value(opp.find('span', class_='value').text if opp.find('span', class_='value') else '0'),
                    'closing_date': parse_date(opp.find('span', class_='closing').text if opp.find('span', class_='closing') else ''),
                    'posted_date': datetime.utcnow(),
                    'location': 'Calgary',
                    'tender_url': 'https://procurement.calgary.ca' + opp.find('a')['href'] if opp.find('a') else '',
                    'description': opp.find('p', class_='desc').text.strip() if opp.find('p', class_='desc') else '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning Calgary Procurement: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_winnipeg_bids(session) -> List[Dict]:
        """Scan Winnipeg Bids (non-Selenium)"""
        tenders = []
        try:
            async with session.get("https://winnipeg.ca/matmgt/bidopp.asp") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    bid_table = soup.find('table', class_='bidopptable')
                    if bid_table:
                        rows = bid_table.find_all('tr')[1:]
                        for row in rows:  # Process ALL rows, not just first 30
                            cells = row.find_all('td')
                            if len(cells) >= 4:
                                tender = {
                                    'tender_id': cells[0].text.strip(),
                                    'title': cells[1].text.strip(),
                                    'organization': 'City of Winnipeg',
                                    'portal': 'City of Winnipeg',
                                    'value': 0,
                                    'closing_date': parse_date(cells[3].text.strip()),
                                    'posted_date': parse_date(cells[2].text.strip()),
                                    'location': 'Winnipeg',
                                    'tender_url': 'https://winnipeg.ca' + (cells[1].find('a')['href'] if cells[1].find('a') else ''),
                                    'description': '',
                                    'categories': [],
                                    'keywords': []
                                }
                                tenders.append(tender)
        except Exception as e:
            logger.error(f"Error scanning Winnipeg Bids: {e}")
        return tenders

    @staticmethod
    async def scan_vancouver_procurement(driver, selenium_helper) -> List[Dict]:
        """Scan Vancouver Procurement"""
        tenders = []
        try:
            driver.get("https://procure.vancouver.ca/psp/VFCPROD/SUPPLIER/ERP/h/?tab=DEFAULT")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "ptpglpage")))
            sourcing_link = driver.find_element(By.LINK_TEXT, "Sourcing")
            sourcing_link.click()
            search_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "BUYER_SEARCH_WRK_DESCRLONG")))
            search_box.send_keys("training professional development")
            search_btn = driver.find_element(By.ID, "BUYER_SEARCH_WRK_SEARCH_PB")
            search_btn.click()
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opp_grid = soup.find('table', id='BUYER_SOURCING_SEARCH')
            if opp_grid:
                rows = opp_grid.find_all('tr')[1:]
                for row in rows:  # Process ALL rows, not just first 30
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        tender = {
                            'tender_id': cells[0].text.strip(),
                            'title': cells[1].text.strip(),
                            'organization': 'City of Vancouver',
                            'portal': 'City of Vancouver',
                            'value': 0,
                            'closing_date': parse_date(cells[3].text.strip()),
                            'posted_date': datetime.utcnow(),
                            'location': 'Vancouver',
                            'tender_url': driver.current_url,
                            'description': '',
                            'categories': [],
                            'keywords': []
                        }
                        tenders.append(tender)
        except Exception as e:
            logger.error(f"Error scanning Vancouver Procurement: {e}")
        return tenders

    @staticmethod
    async def scan_halifax_procurement(driver, selenium_helper) -> List[Dict]:
        """Scan Halifax Regional Municipality"""
        tenders = []
        
        try:
            driver.get("https://procurement.novascotia.ca/ns-tenders.aspx")
            
            # Filter by Halifax
            location_filter = driver.find_element(By.ID, "ddlLocation")
            location_filter.send_keys("Halifax")
            
            # Search for training
            keyword_box = driver.find_element(By.ID, "txtKeywords")
            keyword_box.send_keys("training professional development")
            
            search_btn = driver.find_element(By.ID, "btnSearch")
            search_btn.click()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results = soup.find_all('tr', class_='tender-row')
            
            for row in results:  # Process ALL results, not just first 30
                cells = row.find_all('td')
                if len(cells) >= 4 and 'Halifax' in cells[2].text:
                    tender = {
                        'tender_id': cells[0].text.strip(),
                        'title': cells[1].text.strip(),
                        'organization': 'Halifax Regional Municipality',
                        'portal': 'Halifax Regional Municipality',
                        'value': 0,
                        'closing_date': parse_date(cells[3].text.strip()),
                        'posted_date': datetime.utcnow(),
                        'location': 'Halifax',
                        'tender_url': 'https://procurement.novascotia.ca' + cells[1].find('a')['href'] if cells[1].find('a') else '',
                        'description': '',
                        'categories': [],
                        'keywords': []
                    }
                    
                    tenders.append(tender)
                    
        except Exception as e:
            logger.error(f"Error scanning Halifax Procurement: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_regina_procurement(driver, selenium_helper) -> List[Dict]:
        """Scan City of Regina"""
        tenders = []
        
        try:
            driver.get("https://procurement.regina.ca/")
            
            # Navigate to current opportunities
            current_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Current Opportunities"))
            )
            current_link.click()
            
            # Search
            search_input = driver.find_element(By.ID, "search-field")
            search_input.send_keys("training development")
            search_input.submit()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opportunities = soup.find_all('div', class_='opportunity-item')
            
            for opp in opportunities:  # Process ALL opportunities, not just first 30
                tender = {
                    'tender_id': opp.get('data-ref', ''),
                    'title': opp.find('h3').text.strip() if opp.find('h3') else '',
                    'organization': 'City of Regina',
                    'portal': 'City of Regina',
                    'value': 0,
                    'closing_date': parse_date(opp.find('span', class_='closing-date').text if opp.find('span', class_='closing-date') else ''),
                    'posted_date': parse_date(opp.find('span', class_='posted-date').text if opp.find('span', class_='posted-date') else ''),
                    'location': 'Regina',
                    'tender_url': 'https://procurement.regina.ca' + opp.find('a')['href'] if opp.find('a') else '',
                    'description': opp.find('p', class_='description').text.strip() if opp.find('p', class_='description') else '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning Regina Procurement: {e}")
            
        return tenders

class SpecializedScrapers:
    """Scrapers for specialized procurement platforms"""
    
    @staticmethod
    async def scan_nbon_newbrunswick(driver, selenium_helper) -> List[Dict]:
        """Scan New Brunswick Opportunities Network"""
        tenders = []
        
        try:
            driver.get("https://nbon.gnb.ca/content/nbon/en/opportunities.html")
            
            # Search for training
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "keyword"))
            )
            search_box.send_keys("training professional development education")
            
            # Select relevant categories
            category_select = driver.find_element(By.ID, "category")
            categories = ["Professional Services", "Educational Services", "Training Services"]
            for cat in categories:
                try:
                    option = driver.find_element(By.XPATH, f"//option[contains(text(), '{cat}')]")
                    option.click()
                except:
                    pass
            
            # Submit search
            search_btn = driver.find_element(By.ID, "search-submit")
            search_btn.click()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opportunities = soup.find_all('div', class_='opportunity-listing')
            
            for opp in opportunities:  # Process ALL opportunities, not just first 30
                tender = {
                    'tender_id': opp.get('data-opp-id', ''),
                    'title': opp.find('h3', class_='opp-title').text.strip() if opp.find('h3', class_='opp-title') else '',
                    'organization': opp.find('span', class_='org-name').text.strip() if opp.find('span', class_='org-name') else 'New Brunswick Government',
                    'portal': 'New Brunswick Opportunities Network',
                    'value': parse_value(opp.find('span', class_='value').text if opp.find('span', class_='value') else '0'),
                    'closing_date': parse_date(opp.find('span', class_='closing-date').text if opp.find('span', class_='closing-date') else ''),
                    'posted_date': parse_date(opp.find('span', class_='posted-date').text if opp.find('span', class_='posted-date') else ''),
                    'location': 'New Brunswick',
                    'tender_url': 'https://nbon.gnb.ca' + opp.find('a')['href'] if opp.find('a') else '',
                    'description': opp.find('p', class_='description').text.strip() if opp.find('p', class_='description') else '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning NBON: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_pei_tenders(session) -> List[Dict]:
        """Scan PEI Tenders"""
        tenders = []
        
        try:
            # PEI uses a simple listing page
            async with session.get("https://www.princeedwardisland.ca/en/search/site?f%5B0%5D=type%3Atender") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find search results
                    results = soup.find_all('li', class_='search-result')
                    
                    for result in results:  # Process ALL results, not just first 30
                        title_elem = result.find('h3', class_='title')
                        if title_elem:
                            # Check if training related
                            title = title_elem.text.strip()
                            if any(keyword in title.lower() for keyword in ['training', 'education', 'development', 'professional']):
                                tender = {
                                    'tender_id': result.get('data-id', f"PEI_{datetime.now().timestamp()}"),
                                    'title': title,
                                    'organization': 'PEI Government',
                                    'portal': 'PEI Tenders',
                                    'value': 0,
                                    'closing_date': None,
                                    'posted_date': datetime.utcnow(),
                                    'location': 'Prince Edward Island',
                                    'tender_url': 'https://www.princeedwardisland.ca' + title_elem.find('a')['href'] if title_elem.find('a') else '',
                                    'description': result.find('p', class_='search-snippet').text.strip() if result.find('p', class_='search-snippet') else '',
                                    'categories': [],
                                    'keywords': []
                                }
                                
                                # Try to extract date from description
                                desc = tender['description']
                                date_match = re.search(r'Closing[:\s]+([A-Za-z]+ \d+, \d{4})', desc)
                                if date_match:
                                    tender['closing_date'] = parse_date(date_match.group(1))
                                
                                tenders.append(tender)
                                
        except Exception as e:
            logger.error(f"Error scanning PEI Tenders: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_nl_procurement(session) -> List[Dict]:
        """Scan Newfoundland and Labrador Procurement"""
        tenders = []
        
        try:
            # Search for training-related commodities
            search_url = "https://www.gov.nl.ca/tenders/commodity-search/?commodity=training"
            
            async with session.get(search_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find tender listings
                    tender_list = soup.find('div', class_='tender-list')
                    if tender_list:
                        tender_items = tender_list.find_all('div', class_='tender-item')
                        
                        for item in tender_items:  # Process ALL items, not just first 30
                            tender = {
                                'tender_id': item.get('data-tender-id', ''),
                                'title': item.find('h3').text.strip() if item.find('h3') else '',
                                'organization': item.find('span', class_='dept').text.strip() if item.find('span', class_='dept') else 'NL Government',
                                'portal': 'Newfoundland Procurement',
                                'value': parse_value(item.find('span', class_='value').text if item.find('span', class_='value') else '0'),
                                'closing_date': parse_date(item.find('span', class_='closing').text if item.find('span', class_='closing') else ''),
                                'posted_date': parse_date(item.find('span', class_='posted').text if item.find('span', class_='posted') else ''),
                                'location': 'Newfoundland and Labrador',
                                'tender_url': 'https://www.gov.nl.ca' + item.find('a')['href'] if item.find('a') else '',
                                'description': item.find('p', class_='desc').text.strip() if item.find('p', class_='desc') else '',
                                'categories': [],
                                'keywords': []
                            }
                            
                            tenders.append(tender)
                            
        except Exception as e:
            logger.error(f"Error scanning NL Procurement: {e}")
            
        return tenders

class HealthEducationScrapers:
    """Scrapers for health and education sector procurement"""
    
    @staticmethod
    async def scan_buybc_health(driver, selenium_helper) -> List[Dict]:
        """Scan Buy BC Health"""
        tenders = []
        
        try:
            driver.get("https://www.bchealth.ca/tenders")
            
            # Search for training
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "tender-search"))
            )
            search_input.send_keys("training education professional development")
            search_input.submit()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tender_cards = soup.find_all('div', class_='tender-card')
            
            for card in tender_cards:  # Process ALL cards, not just first 30
                tender = {
                    'tender_id': card.get('data-tender-id', ''),
                    'title': card.find('h3', class_='tender-title').text.strip() if card.find('h3') else '',
                    'organization': card.find('span', class_='health-authority').text.strip() if card.find('span', class_='health-authority') else 'BC Health',
                    'portal': 'Buy BC Health',
                    'value': parse_value(card.find('span', class_='value').text if card.find('span', class_='value') else '0'),
                    'closing_date': parse_date(card.find('span', class_='closing').text if card.find('span', class_='closing') else ''),
                    'posted_date': parse_date(card.find('span', class_='posted').text if card.find('span', class_='posted') else ''),
                    'location': 'British Columbia',
                    'tender_url': 'https://www.bchealth.ca' + card.find('a')['href'] if card.find('a') else '',
                    'description': card.find('p', class_='description').text.strip() if card.find('p') else '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning Buy BC Health: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_ontario_health(driver, selenium_helper) -> List[Dict]:
        """Scan Ontario Health via MERX"""
        tenders = []
        
        try:
            # Ontario Health posts on MERX
            driver.get("https://www.merx.com/search")
            
            # Search for Ontario Health training opportunities
            search_box = driver.find_element(By.ID, "keyword")
            search_box.send_keys("Ontario Health training professional development")
            
            # Filter by organization
            org_filter = driver.find_element(By.ID, "organization")
            org_filter.send_keys("Ontario Health")
            
            # Submit search
            search_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            search_btn.click()
            
            # Parse results (similar to MERX scraper)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opportunities = soup.find_all('div', class_='row')
            
            for opp in opportunities:  # Process ALL opportunities, not just first 20
                if 'Ontario Health' in opp.text:
                    tender = {
                        'tender_id': opp.get('data-id', ''),
                        'title': opp.find('a', class_='search-result-title').text.strip() if opp.find('a', class_='search-result-title') else '',
                        'organization': 'Ontario Health',
                        'portal': 'Ontario Health',
                        'value': 0,
                        'closing_date': parse_date(opp.find('span', class_='closing-date').text if opp.find('span', class_='closing-date') else ''),
                        'posted_date': parse_date(opp.find('span', class_='posted-date').text if opp.find('span', class_='posted-date') else ''),
                        'location': 'Ontario',
                        'tender_url': 'https://www.merx.com' + opp.find('a')['href'] if opp.find('a') else '',
                        'description': '',
                        'categories': [],
                        'keywords': []
                    }
                    
                    tenders.append(tender)
                    
        except Exception as e:
            logger.error(f"Error scanning Ontario Health: {e}")
            
        return tenders

class MERXScraper:
    """Enhanced MERX scraper with multiple search strategies"""
    
    def __init__(self, username=None, password=None):
        self.base_url = "https://www.merx.com"
        self.search_url = "https://www.merx.com/public/solicitations/open?"
        self.login_url = "https://www.merx.com/login"
        self.username = username
        self.password = password
        self.driver = None
        self.is_logged_in = False
        
    async def search(self, query, max_pages=5, search_url=None):
        """Enhanced search with multiple strategies and pagination"""
        logger.info(f"Starting enhanced MERX search for: {query}")
        
        if not self.driver:
            self.driver = await self._setup_driver()
        
        all_tenders = []
        
        try:
            # Add timeout to prevent getting stuck
            import asyncio
            search_task = asyncio.create_task(self._perform_search(query, max_pages, search_url))
            
            try:
                # Wait for search to complete with timeout
                all_tenders = await asyncio.wait_for(search_task, timeout=300)  # 5 minute timeout
            except asyncio.TimeoutError:
                logger.warning("MERX search timed out after 5 minutes - returning partial results")
                # Cancel the task if it's still running
                if not search_task.done():
                    search_task.cancel()
                # Return whatever we have so far
                return all_tenders
                
        except Exception as e:
            logger.error(f"Error during MERX search: {e}")
        
        logger.info(f"MERX search complete: {len(all_tenders)} total tenders found")
        return all_tenders
    
    async def _perform_search(self, query, max_pages=5, search_url=None):
        """Internal search method with timeout protection"""
        all_tenders = []
        
        try:
            # Format query for MERX
            if isinstance(query, (list, tuple)):
                query_str = ' '.join(query)
            else:
                query_str = str(query)
            
            # For MERX: Use AND between keywords for multi-keyword search
            if ' ' in query_str and ' AND ' not in query_str.upper():
                keywords = query_str.split()
                query_str = ' AND '.join(keywords)
            logger.info(f"Using MERX search query: {query_str}")
            
            # Use the provided search_url or fall back to default
            if search_url:
                target_url = search_url
            else:
                target_url = "https://www.merx.com/public/solicitations/open?"
            
            # Navigate to MERX search page
            self.driver.get(target_url)
            await asyncio.sleep(3)
            
            # Debug: Log the current page title and URL
            logger.info(f"Current page: {self.driver.title}")
            logger.info(f"Current URL: {self.driver.current_url}")
            
            # Handle cookie consent
            await self._handle_cookie_consent()
            
            # Try to login if credentials provided (with timeout)
            if self.username and self.password:
                logger.info("Attempting to login to MERX")
                try:
                    login_task = asyncio.create_task(self._login())
                    await asyncio.wait_for(login_task, timeout=60)  # 1 minute timeout for login
                except asyncio.TimeoutError:
                    logger.warning("Login timed out - continuing with public access")
                except Exception as e:
                    logger.error(f"Error during login: {e}")
                    logger.warning("Continuing with public access")
            
            # Check if we're on a login page or 404
            if "login" in self.driver.title.lower() or "error" in self.driver.title.lower():
                logger.warning("Redirected to login page or error page - trying alternative URL")
                alternative_url = "https://www.merx.com/public/solicitations/open?"
                self.driver.get(alternative_url)
                await asyncio.sleep(3)
                logger.info(f"Alternative page: {self.driver.title}")
                logger.info(f"Alternative URL: {self.driver.current_url}")
            
            # Try to find search input field
            search_input = None
            search_selectors = [
                "input[name='search']",
                "input[placeholder*='Search']",
                "input[type='search']",
                "input[aria-label*='Search']",
                "#search",
                ".search-input",
                "input[class*='search']",
                "input[data-testid*='search']",
                "input[name='keywords']",
                "input[name='query']",
                "input[name='q']",
                "input[placeholder*='keyword']",
                "input[placeholder*='find']",
                "input[placeholder*='tender']",
                "input[placeholder*='opportunity']"
            ]
            
            for selector in search_selectors:
                try:
                    search_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if search_input.is_displayed() and search_input.is_enabled():
                        logger.info(f"Found search input with selector: {selector}")
                        break
                except:
                    continue
            
            if not search_input:
                # Try to find any input field that might be for search
                all_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input")
                logger.info(f"Found {len(all_inputs)} input elements on the page")
                for i, inp in enumerate(all_inputs[:5]):  # Log first 5 inputs
                    try:
                        placeholder = inp.get_attribute('placeholder') or 'None'
                        name = inp.get_attribute('name') or 'None'
                        input_type = inp.get_attribute('type') or 'None'
                        logger.info(f"Input {i}: type={input_type}, name={name}, placeholder={placeholder}")
                    except:
                        pass
                
                logger.error("Error during MERX search: Could not find search input field on MERX")
                logger.info("MERX search complete: 0 total tenders found")
                return all_tenders
            
            # Clear and enter search query
            try:
                search_input.clear()
                search_input.send_keys(query_str)
                await asyncio.sleep(1)
                
                # Try multiple submit button selectors
                search_button = None
                button_selectors = [
                    "button[type='submit']",
                    "button[aria-label*='Search']",
                    ".search-button",
                    "button[class*='search']",
                    "input[type='submit']",
                    ".btn-search",
                    "button:contains('Search')",
                    ".search-submit",
                    "button[data-testid*='search']",
                    "button[class*='btn']"
                ]
                
                for selector in button_selectors:
                    try:
                        search_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if search_button.is_displayed() and search_button.is_enabled():
                            logger.info(f"Found search button with selector: {selector}")
                            break
                    except:
                        continue
                
                if not search_button:
                    # Try pressing Enter on the search input
                    from selenium.webdriver.common.keys import Keys
                    search_input.send_keys(Keys.RETURN)
                    logger.info("Submitted search using Enter key")
                else:
                    search_button.click()
                    logger.info("Submitted search using search button")
                
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.warning(f"Could not interact with search input: {e}")
                logger.info("MERX search complete: 0 total tenders found")
                return all_tenders
            
            # Process multiple pages
            for page in range(1, max_pages + 1):
                logger.info(f"Processing MERX page {page} for query: {query_str}")
                
                # Wait for results to load
                await asyncio.sleep(3)
                
                # Extract tenders from current page
                page_tenders = await self._extract_tenders_from_page()
                all_tenders.extend(page_tenders)
                
                logger.info(f"Found {len(page_tenders)} tenders on page {page}")
                
                # Try to go to next page
                if page < max_pages:
                    try:
                        next_selectors = [
                            "a[aria-label*='Next']",
                            ".next-page",
                            ".pagination-next",
                            "a[rel='next']",
                            "a:contains('Next')",
                            "button[aria-label*='Next']",
                            ".next",
                            "[class*='next']",
                            "a[href*='page']",
                            "a[href*='p=']"
                        ]
                        
                        next_button = None
                        for selector in next_selectors:
                            try:
                                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                if next_button.is_displayed() and next_button.is_enabled():
                                    break
                            except:
                                continue
                        
                        if next_button and 'disabled' not in next_button.get_attribute('class'):
                            next_button.click()
                            await asyncio.sleep(2)
                        else:
                            logger.info("Reached last page or no next button found")
                            break
                    except Exception as e:
                        logger.info(f"No more pages available: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Error during MERX search: {e}")
        
        return all_tenders
    
    async def _scrape_all_open_solicitations(self, max_pages=5, query=""):
        """Scrape all open solicitations and filter by relevance"""
        all_tenders = []
        
        try:
            # Process multiple pages of open solicitations
            for page in range(1, max_pages + 1):
                logger.info(f"Processing MERX page {page} for all open solicitations")
                
                # Wait for results to load
                await asyncio.sleep(3)
                
                # Extract tenders from current page
                page_tenders = await self._extract_tenders_from_page()
                
                # Filter by relevance if query provided
                if query:
                    relevant_tenders = []
                    for tender in page_tenders:
                        relevance_score = self._calculate_relevance(tender, query)
                        if relevance_score > 0.3:  # Threshold for relevance
                            tender['relevance_score'] = relevance_score
                            relevant_tenders.append(tender)
                    page_tenders = relevant_tenders
                
                all_tenders.extend(page_tenders)
                
                logger.info(f"Found {len(page_tenders)} relevant tenders on page {page}")
                
                # Try to go to next page
                if page < max_pages:
                    try:
                        next_selectors = [
                            "button[aria-label*='Next']",
                            "a[aria-label*='Next']",
                            ".next-page",
                            ".pagination-next",
                            "a[rel='next']",
                            "button:contains('Next')",
                            "a:contains('Next')",
                            "a[href*='page']",
                            ".pagination a[href*='page']",
                            "[class*='next']",
                            "a[href*='p=']"
                        ]
                        
                        next_button = None
                        for selector in next_selectors:
                            try:
                                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                if next_button.is_displayed() and next_button.is_enabled():
                                    break
                            except:
                                continue
                        
                        if next_button and 'disabled' not in next_button.get_attribute('class'):
                            next_button.click()
                            await asyncio.sleep(2)
                        else:
                            logger.info("Reached last page or no next button found")
                            break
                    except Exception as e:
                        logger.info(f"No more pages available: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Error scraping open solicitations: {e}")
        
        return all_tenders
    
    def _calculate_relevance(self, tender, query):
        """Calculate relevance score for a tender based on query"""
        query_terms = query.lower().split()
        title = tender.get('title', '').lower()
        description = tender.get('description', '').lower()
        
        score = 0
        for term in query_terms:
            if term in title:
                score += 0.5
            if term in description:
                score += 0.3
            # Check for partial matches
            if any(term in word for word in title.split()):
                score += 0.2
            if any(term in word for word in description.split()):
                score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    async def _setup_driver(self):
        """Setup Selenium WebDriver with enhanced configuration"""
        try:
            from selenium_utils import get_driver
            driver = get_driver()
            
            # Set page load timeout
            driver.set_page_load_timeout(30)
            
            # Set window size for better compatibility
            driver.set_window_size(1920, 1080)
            
            logger.info("Selenium WebDriver setup complete")
            return driver
            
        except Exception as e:
            logger.error(f"Error setting up WebDriver: {e}")
            raise
    
    async def _handle_cookie_consent(self):
        """Handle cookie consent popups"""
        try:
            # Navigate to MERX first to trigger cookie consent
            self.driver.get(self.base_url)
            await asyncio.sleep(2)
            
            # Look for cookie consent buttons
            cookie_selectors = [
                "button[aria-label*='Accept']",
                "button[aria-label*='Accept All']",
                "button:contains('Accept')",
                "button:contains('Accept All')",
                "button:contains('I Accept')",
                "button:contains('OK')",
                "button:contains('Continue')",
                ".cookie-accept",
                ".cookie-consent-accept",
                "[data-testid*='accept']",
                "[data-testid*='cookie']",
                ".cookie-banner button",
                ".cookie-notice button",
                "button[class*='accept']",
                "button[class*='cookie']"
            ]
            
            for selector in cookie_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            logger.info(f"Found and clicking cookie consent button: {selector}")
                            button.click()
                            await asyncio.sleep(1)
                            return
                except:
                    continue
            
            logger.info("No cookie consent popup found or already handled")
            
        except Exception as e:
            logger.warning(f"Error handling cookie consent: {e}")
    
    async def _login(self):
        """Login to MERX with provided credentials"""
        try:
            logger.info("Attempting to login to MERX")
            
            # Navigate to login page
            self.driver.get(self.login_url)
            await asyncio.sleep(3)
            
            # Handle cookie consent before login
            await self._handle_cookie_consent()
            
            # Check if we're already on a login page
            if "login" not in self.driver.title.lower() and "sign in" not in self.driver.title.lower():
                logger.info("Not on login page, may already be logged in or redirected")
                return
            
            # Find username field with better error handling
            username_selectors = [
                "input[name='j_username']",
                "input[name='username']",
                "input[type='email']",
                "input[placeholder*='Username']",
                "input[placeholder*='Email']",
                "#username",
                "#email"
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if username_field.is_displayed() and username_field.is_enabled():
                        logger.info(f"Found username field with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Username selector {selector} failed: {e}")
                    continue
            
            if not username_field:
                logger.warning("Could not find username field - skipping login")
                return
            
            # Find password field with better error handling
            password_selectors = [
                "input[name='j_password']",
                "input[name='password']",
                "input[type='password']",
                "input[placeholder*='Password']",
                "#password"
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if password_field.is_displayed() and password_field.is_enabled():
                        logger.info(f"Found password field with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Password selector {selector} failed: {e}")
                    continue
            
            if not password_field:
                logger.warning("Could not find password field - skipping login")
                return
            
            # Enter credentials with better error handling
            try:
                # Clear fields first
                username_field.clear()
                await asyncio.sleep(0.5)
                username_field.send_keys(self.username)
                await asyncio.sleep(0.5)
                
                password_field.clear()
                await asyncio.sleep(0.5)
                password_field.send_keys(self.password)
                await asyncio.sleep(0.5)
                
                logger.info("Credentials entered successfully")
            except Exception as e:
                logger.warning(f"Error entering credentials: {e} - skipping login")
                return
            
            # Find and click login button with better error handling
            login_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Login')",
                "button:contains('Sign In')",
                "button:contains('Log In')",
                ".login-button",
                ".signin-button",
                "[data-testid*='login']",
                "[data-testid*='signin']"
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if login_button.is_displayed() and login_button.is_enabled():
                        logger.info(f"Found login button with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Login button selector {selector} failed: {e}")
                    continue
            
            if not login_button:
                logger.warning("Could not find login button - trying Enter key")
                try:
                    from selenium.webdriver.common.keys import Keys
                    password_field.send_keys(Keys.RETURN)
                    await asyncio.sleep(3)
                    logger.info("Submitted login with Enter key")
                except Exception as e:
                    logger.warning(f"Enter key submission failed: {e} - skipping login")
                    return
            else:
                # Click login button with better error handling
                try:
                    login_button.click()
                    await asyncio.sleep(3)
                    logger.info("Clicked login button")
                except Exception as e:
                    logger.warning(f"Login button click failed: {e} - trying JavaScript click")
                    try:
                        self.driver.execute_script("arguments[0].click();", login_button)
                        await asyncio.sleep(3)
                        logger.info("Login button clicked via JavaScript")
                    except Exception as e2:
                        logger.warning(f"JavaScript click also failed: {e2} - skipping login")
                        return
            
            # Check if login was successful
            await asyncio.sleep(2)
            if "login" not in self.driver.title.lower() and "sign in" not in self.driver.title.lower():
                self.is_logged_in = True
                logger.info("Successfully logged in to MERX")
            else:
                logger.warning("Login may have failed - continuing with public access")
            
        except Exception as e:
            logger.error(f"Error during login: {e}")
            logger.warning("Continuing with public access")
    
    async def _extract_tenders_from_page(self):
        """Extract tenders from current page with enhanced parsing for MERX structure"""
        tenders = []
        
        try:
            # Wait for results to load - MERX shows results in a table format
            result_selectors = [
                "table",  # MERX uses tables for results
                ".results-table",
                "[class*='result']",
                "[class*='tender']",
                "[class*='opportunity']",
                "[class*='solicitation']"
            ]
            
            results_found = False
            for selector in result_selectors:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Found results container with selector: {selector}")
                    results_found = True
                    break
                except:
                    continue
            
            if not results_found:
                # Wait for any content to load
                await asyncio.sleep(5)
                logger.info("No specific results container found, proceeding with general search")
            
            # Find all tender rows - MERX uses table rows for tenders
            tender_selectors = [
                "tr",  # Table rows for MERX
                "tr[data-testid*='tender']",
                "tr[class*='tender']",
                "tr[class*='opportunity']",
                "tr[class*='solicitation']",
                ".tender-row",
                ".opportunity-row",
                ".solicitation-row",
                "[class*='tender']",
                "[class*='opportunity']",
                "[class*='bid']",
                "article",
                ".card",
                ".item"
            ]
            
            tender_cards = []
            for selector in tender_selectors:
                try:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards:
                        logger.info(f"Found {len(cards)} tender cards with selector: {selector}")
                        tender_cards = cards
                        break
                except:
                    continue
            
            if not tender_cards:
                # Fallback: look for any clickable elements that might be tenders
                all_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='tender'], a[href*='opportunity'], a[href*='bid'], a[href*='solicitation']")
                logger.info(f"Fallback: found {len(all_links)} potential tender links")
                tender_cards = all_links
            
            for card in tender_cards:
                try:
                    tender_data = await self._parse_tender_card(card)
                    if tender_data:
                        tenders.append(tender_data)
                except Exception as e:
                    logger.warning(f"Error parsing tender card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting tenders from page: {e}")
        
        return tenders
    
    async def _parse_tender_card(self, card):
        """Enhanced tender card parsing with better field extraction"""
        try:
            # Extract title and link with multiple selectors
            title_selectors = [
                "h3 a", ".tender-title a", "h2 a", "h1 a",
                ".title a", ".name a", ".heading a",
                "a[href*='tender']", "a[href*='opportunity']", "a[href*='bid']",
                "a", ".title", ".name", ".heading"
            ]
            
            title_element = None
            title = ""
            tender_url = ""
            
            for selector in title_selectors:
                try:
                    title_element = card.find_element(By.CSS_SELECTOR, selector)
                    if title_element.is_displayed():
                        title = title_element.text.strip()
                        tender_url = title_element.get_attribute('href') or ""
                        if title and tender_url:
                            logger.info(f"Found title with selector: {selector}")
                            break
                except:
                    continue
            
            if not title:
                # Fallback: get any text that might be a title
                title = card.text[:200].strip()  # First 200 chars as title
                tender_url = card.get_attribute('href') or ""
            
            # Extract tender ID from URL or text
            tender_id = self._extract_tender_id(tender_url, title)
            
            # Extract organization with multiple selectors
            org_selectors = [
                ".organization", ".buyer-name", ".buyer", ".department",
                ".agency", ".client", ".company", ".org",
                "[class*='organization']", "[class*='buyer']", "[class*='department']"
            ]
            
            organization = ""
            for selector in org_selectors:
                try:
                    org_element = card.find_element(By.CSS_SELECTOR, selector)
                    organization = org_element.text.strip()
                    if organization:
                        break
                except:
                    continue
            
            # Extract location with multiple selectors
            location_selectors = [
                ".location", ".province", ".region", ".area",
                ".city", ".state", ".territory",
                "[class*='location']", "[class*='province']", "[class*='region']"
            ]
            
            location = ""
            for selector in location_selectors:
                try:
                    location_element = card.find_element(By.CSS_SELECTOR, selector)
                    location = location_element.text.strip()
                    if location:
                        break
                except:
                    continue
            
            # Extract closing date
            closing_date = await self._extract_date(card, ".closing-date, .deadline, .due-date, [class*='closing'], [class*='deadline']")
            
            # Extract posted date
            posted_date = await self._extract_date(card, ".posted-date, .published-date, .issue-date, [class*='posted'], [class*='published']")
            
            # Extract value (if available)
            value = await self._extract_value(card)
            
            # Extract description
            description = await self._extract_description(card)
            
            # Determine priority based on content analysis
            priority = self._determine_priority(title, description)
            
            # Extract matching courses
            matching_courses = self._extract_matching_courses(title, description)
            
            # Extract categories
            categories = await self._extract_categories(card)
            
            # Extract keywords
            keywords = self._extract_keywords(title, description)
            
            # Extract contact info
            contact_email, contact_phone = await self._extract_contact_info(card)
            
            return {
                'tender_id': tender_id,
                'title': title,
                'organization': organization,
                'portal': 'CanadaBuys',
                'value': value,
                'closing_date': closing_date,
                'posted_date': posted_date,
                'description': description,
                'location': location,
                'categories': categories,
                'keywords': keywords,
                'contact_email': contact_email,
                'contact_phone': contact_phone,
                'tender_url': tender_url,
                'documents_url': None,
                'priority': priority,
                'matching_courses': matching_courses
            }
            
        except Exception as e:
            logger.warning(f"Error parsing tender card: {e}")
            return None
    
    def _extract_tender_id(self, url, title):
        """Extract tender ID from URL or title"""
        if url:
            # Try to extract from URL
            import re
            match = re.search(r'/(\d+)(?:/|$)', url)
            if match:
                return match.group(1)
        
        # Try to extract from title
        import re
        match = re.search(r'#(\d+)', title)
        if match:
            return match.group(1)
        
        # Generate ID from title hash
        import hashlib
        return hashlib.md5(title.encode()).hexdigest()[:8]
    
    async def _extract_date(self, card, selector):
        """Extract date from card element"""
        try:
            date_element = card.find_element(By.CSS_SELECTOR, selector)
            date_text = date_element.text
            return self._parse_date(date_text)
        except:
            return None
    
    def _parse_date(self, date_text):
        """Parse various date formats"""
        if not date_text:
            return None
        
        try:
            # Common date formats
            from datetime import datetime
            formats = [
                '%B %d, %Y',
                '%b %d, %Y',
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_text.strip(), fmt).isoformat()
                except:
                    continue
            
            return None
        except:
            return None
    
    async def _extract_value(self, card):
        """Extract tender value"""
        try:
            value_element = card.find_element(By.CSS_SELECTOR, ".value, .budget, .amount")
            value_text = value_element.text
            return self._parse_value(value_text)
        except:
            return 0
    
    def _parse_value(self, value_text):
        """Parse value from text"""
        if not value_text:
            return 0
        
        try:
            import re
            # Extract numbers and handle currency
            numbers = re.findall(r'[\d,]+', value_text.replace(',', ''))
            if numbers:
                value = float(numbers[0])
                
                # Handle multipliers (K, M, B)
                if 'K' in value_text.upper():
                    value *= 1000
                elif 'M' in value_text.upper():
                    value *= 1000000
                elif 'B' in value_text.upper():
                    value *= 1000000000
                
                return int(value)
        except:
            pass
        
        return 0
    
    async def _extract_description(self, card):
        """Extract tender description"""
        try:
            desc_element = card.find_element(By.CSS_SELECTOR, ".description, .summary, .details")
            return desc_element.text
        except:
            return ""
    
    def _determine_priority(self, title, description):
        """Determine tender priority based on content analysis"""
        text = f"{title} {description}".lower()
        
        # High priority indicators
        high_priority_terms = [
            'training', 'professional development', 'certification',
            'AWS', 'Azure', 'cybersecurity', 'project management',
            'agile', 'scrum', 'leadership', 'coaching'
        ]
        
        # Medium priority indicators
        medium_priority_terms = [
            'consulting', 'implementation', 'change management',
            'development', 'education', 'learning'
        ]
        
        high_count = sum(1 for term in high_priority_terms if term in text)
        medium_count = sum(1 for term in medium_priority_terms if term in text)
        
        if high_count >= 2:
            return 'high'
        elif high_count >= 1 or medium_count >= 2:
            return 'medium'
        else:
            return 'low'
    
    def _extract_matching_courses(self, title, description):
        """Extract matching TKA courses from content"""
        text = f"{title} {description}".lower()
        matching_courses = []
        
        # Course mappings
        course_mappings = {
            'aws': 'AWS Training',
            'azure': 'Azure Training',
            'cloud': 'Cloud Computing',
            'cybersecurity': 'Cybersecurity Training',
            'cissp': 'CISSP Certification',
            'project management': 'Project Management',
            'pmp': 'PMP Certification',
            'prince2': 'PRINCE2 Certification',
            'agile': 'Agile Training',
            'scrum': 'Scrum Training',
            'leadership': 'Leadership Development',
            'itil': 'ITIL Training',
            'devops': 'DevOps Training',
            'data analytics': 'Data Analytics',
            'business intelligence': 'Business Intelligence',
            'change management': 'Change Management',
            'coaching': 'Executive Coaching'
        }
        
        for keyword, course in course_mappings.items():
            if keyword in text:
                matching_courses.append(course)
        
        return matching_courses
    
    async def _extract_categories(self, card):
        """Extract tender categories"""
        try:
            category_elements = card.find_elements(By.CSS_SELECTOR, ".category, .tag, .classification")
            categories = []
            for element in category_elements:
                category = element.text
                if category:
                    categories.append(category.strip())
            return categories
        except:
            return []
    
    def _extract_keywords(self, title, description):
        """Extract keywords from title and description"""
        text = f"{title} {description}".lower()
        keywords = []
        
        # Extract meaningful keywords
        import re
        words = re.findall(r'\b\w{4,}\b', text)
        
        # Filter for relevant keywords
        relevant_words = [
            'training', 'development', 'consulting', 'implementation',
            'management', 'leadership', 'technology', 'digital',
            'transformation', 'change', 'process', 'system'
        ]
        
        for word in words:
            if word in relevant_words and word not in keywords:
                keywords.append(word)
        
        return keywords[:10]  # Limit to 10 keywords
    
    async def _extract_contact_info(self, card):
        """Extract contact information"""
        try:
            # Look for contact elements
            contact_elements = card.find_elements(By.CSS_SELECTOR, ".contact, .contact-info, .buyer-contact")
            
            email = None
            phone = None
            
            for element in contact_elements:
                text = element.text
                
                # Extract email
                import re
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                if email_match:
                    email = email_match.group(0)
                
                # Extract phone
                phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
                if phone_match:
                    phone = phone_match.group(0)
            
            return email, phone
        except:
            return None, None

class CanadaBuysScraper:
    """Enhanced CanadaBuys scraper with multiple search strategies"""
    
    def __init__(self):
        self.base_url = "https://canadabuys.canada.ca"
        self.search_url = "https://canadabuys.canada.ca/en/tender-opportunities?search_filter=&status%5B87%5D=87&record_per_page=50&current_tab=t&words="
        self.driver = None
        
    async def search(self, query, max_pages=5):
        logger.info(f"[DEBUG] CanadaBuysScraper.search called with query: {query}")
        """Enhanced search with multiple strategies and pagination"""
        logger.info(f"Starting enhanced CanadaBuys search for: {query}")
        
        if not self.driver:
            self.driver = await self._setup_driver()
        
        all_tenders = []
        
        try:
            # --- 1. Use quoted multi-keyword search ---
            if isinstance(query, (list, tuple)):
                query_str = ' '.join(query)
            else:
                query_str = str(query)
            if ' ' in query_str and not (query_str.startswith('"') and query_str.endswith('"')):
                query_str = f'"{query_str.strip()}"'
            logger.info(f"Using quoted search query: {query_str}")

            # Navigate to search page with query parameters
            search_url_with_query = f"{self.search_url}{query_str}"
            self.driver.get(search_url_with_query)
            await asyncio.sleep(3)
            
            # Debug: Log the current page title and URL
            logger.info(f"Current page: {self.driver.title}")
            logger.info(f"Current URL: {self.driver.current_url}")
            
            # Handle cookie consent if present
            try:
                accept_selectors = [
                    "button[aria-label*='Accept']",
                    ".accept-cookies", 
                    ".cookie-accept",
                    "button:contains('Accept')",
                    "button:contains('OK')",
                    ".btn-accept",
                    "button[data-testid*='accept']",
                    "button[class*='accept']"
                ]
                for selector in accept_selectors:
                    try:
                        accept_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if accept_button.is_displayed():
                            accept_button.click()
                            await asyncio.sleep(1)
                            break
                    except:
                        continue
            except:
                pass
            
            # Try multiple search input selectors for CanadaBuys
            search_input = None
            search_selectors = [
                "input[placeholder*='Search']",
                "input[name='search']",
                "input[type='search']",
                "input[aria-label*='Search']",
                "#search",
                ".search-input",
                "input[class*='search']",
                "input[data-testid*='search']",
                "input[name='keywords']",
                "input[name='query']",
                "input[name='q']",
                "input[placeholder*='keyword']",
                "input[placeholder*='find']",
                "input[placeholder*='tender']",
                "input[placeholder*='opportunity']",
                "input[name='words']"
            ]
            
            for selector in search_selectors:
                try:
                    search_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if search_input.is_displayed() and search_input.is_enabled():
                        logger.info(f"Found search input with selector: {selector}")
                        break
                except:
                    continue
            
            if not search_input:
                # Try to find any input field that might be for search
                all_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input")
                logger.info(f"Found {len(all_inputs)} input elements on the page")
                for i, inp in enumerate(all_inputs[:5]):  # Log first 5 inputs
                    try:
                        placeholder = inp.get_attribute('placeholder') or 'None'
                        name = inp.get_attribute('name') or 'None'
                        input_type = inp.get_attribute('type') or 'None'
                        logger.info(f"Input {i}: type={input_type}, name={name}, placeholder={placeholder}")
                    except:
                        pass
                
                for inp in all_inputs:
                    if inp.is_displayed() and inp.is_enabled():
                        placeholder = inp.get_attribute('placeholder') or ''
                        name = inp.get_attribute('name') or ''
                        if any(term in placeholder.lower() or term in name.lower() 
                               for term in ['search', 'keyword', 'query', 'find', 'tender', 'opportunity', 'words']):
                            search_input = inp
                            logger.info(f"Found search input by analyzing attributes")
                            break
            
            if not search_input:
                logger.warning("Could not find search input field on CanadaBuys - scraping all opportunities")
                return await self._scrape_all_opportunities(max_pages, query_str)
            
            # Clear and enter search query
            try:
                search_input.clear()
                search_input.send_keys(query_str)
                await asyncio.sleep(1)
                
                # Try multiple submit button selectors
                search_button = None
                button_selectors = [
                    "button[type='submit']",
                    "button[aria-label*='Search']",
                    ".search-button",
                    "button[class*='search']",
                    "input[type='submit']",
                    ".btn-search",
                    "button:contains('Search')",
                    ".search-submit",
                    "button[data-testid*='search']",
                    "button[class*='btn']"
                ]
                
                for selector in button_selectors:
                    try:
                        search_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if search_button.is_displayed() and search_button.is_enabled():
                            logger.info(f"Found search button with selector: {selector}")
                            break
                    except:
                        continue
                
                if not search_button:
                    # Try pressing Enter on the search input
                    from selenium.webdriver.common.keys import Keys
                    search_input.send_keys(Keys.RETURN)
                    logger.info("Submitted search using Enter key")
                else:
                    search_button.click()
                    logger.info("Submitted search using search button")
                
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.warning(f"Could not interact with search input: {e}")
                return await self._scrape_all_opportunities(max_pages, query_str)

            # --- 2. Set results per page to 200 ---
            try:
                # Try to find the results-per-page dropdown/button
                per_page_selectors = [
                    "select[name='record_per_page']",
                    "#results-per-page",
                    ".results-per-page select",
                    "select[aria-label*='Results per page']",
                    "select",
                    "button[aria-label*='Results per page']",
                    ".results-per-page button",
                    "button:contains('Results per page')",
                    "[data-testid*='results-per-page']"
                ]
                per_page_control = None
                for selector in per_page_selectors:
                    try:
                        per_page_control = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if per_page_control.is_displayed() and per_page_control.is_enabled():
                            logger.info(f"Found results-per-page control with selector: {selector}")
                            break
                    except:
                        continue
                if per_page_control:
                    tag = per_page_control.tag_name.lower()
                    if tag == 'select':
                        from selenium.webdriver.support.ui import Select
                        select = Select(per_page_control)
                        select.select_by_value('200')
                        logger.info("Set results per page to 200 via select dropdown")
                    elif tag == 'button':
                        per_page_control.click()
                        await asyncio.sleep(1)
                        # Try to find the 200 option in the dropdown
                        option_selectors = [
                            "li[data-value='200']",
                            "button[data-value='200']",
                            "li:contains('200')",
                            "button:contains('200')",
                            "option[value='200']",
                            "[role='option'][data-value='200']"
                        ]
                        for opt_selector in option_selectors:
                            try:
                                option = self.driver.find_element(By.CSS_SELECTOR, opt_selector)
                                if option.is_displayed() and option.is_enabled():
                                    option.click()
                                    logger.info("Set results per page to 200 via button dropdown")
                                    break
                            except:
                                continue
                    await asyncio.sleep(2)
                else:
                    logger.warning("Could not find results-per-page control to set 200 per page")
            except Exception as e:
                logger.warning(f"Error setting results per page: {e}")
            
            # Process multiple pages
            for page in range(1, max_pages + 1):
                logger.info(f"Processing CanadaBuys page {page} for query: {query}")
                
                # Wait for results to load
                await asyncio.sleep(3)
                
                # Extract tenders from current page
                page_tenders = await self._extract_tenders_from_page()
                all_tenders.extend(page_tenders)
                
                logger.info(f"Found {len(page_tenders)} tenders on page {page}")
                
                # Try to go to next page
                if page < max_pages:
                    try:
                        next_selectors = [
                            "a[aria-label*='Next']",
                            ".next-page",
                            ".pagination-next",
                            "a[rel='next']",
                            "a:contains('Next')",
                            "button[aria-label*='Next']",
                            ".next",
                            "[class*='next']",
                            "a[href*='page']",
                            "a[href*='p=']"
                        ]
                        
                        next_button = None
                        for selector in next_selectors:
                            try:
                                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                if next_button.is_displayed() and next_button.is_enabled():
                                    break
                            except:
                                continue
                        
                        if next_button and 'disabled' not in next_button.get_attribute('class'):
                            next_button.click()
                            await asyncio.sleep(2)
                        else:
                            logger.info("Reached last page or no next button found")
                            break
                    except Exception as e:
                        logger.info(f"No more pages available: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Error during CanadaBuys search: {e}")
        
        logger.info(f"CanadaBuys search complete: {len(all_tenders)} total tenders found")
        return all_tenders
    
    async def _scrape_all_opportunities(self, max_pages=5, query=""):
        """Scrape all opportunities and filter by relevance"""
        all_tenders = []
        
        try:
            # Process multiple pages of opportunities
            for page in range(1, max_pages + 1):
                logger.info(f"Processing CanadaBuys page {page} for all opportunities")
                
                # Wait for results to load
                await asyncio.sleep(3)
                
                # Extract tenders from current page
                page_tenders = await self._extract_tenders_from_page()
                
                # Filter by relevance if query provided
                if query:
                    relevant_tenders = []
                    for tender in page_tenders:
                        relevance_score = self._calculate_relevance(tender, query)
                        if relevance_score > 0.3:  # Threshold for relevance
                            tender['relevance_score'] = relevance_score
                            relevant_tenders.append(tender)
                    page_tenders = relevant_tenders
                
                all_tenders.extend(page_tenders)
                
                logger.info(f"Found {len(page_tenders)} relevant tenders on page {page}")
                
                # Try to go to next page
                if page < max_pages:
                    try:
                        next_selectors = [
                            "a[aria-label*='Next']",
                            ".next-page",
                            ".pagination-next",
                            "a[rel='next']",
                            "a:contains('Next')",
                            "button[aria-label*='Next']",
                            ".next",
                            "[class*='next']",
                            "a[href*='page']",
                            "a[href*='p=']"
                        ]
                        
                        next_button = None
                        for selector in next_selectors:
                            try:
                                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                if next_button.is_displayed() and next_button.is_enabled():
                                    break
                            except:
                                continue
                        
                        if next_button and 'disabled' not in next_button.get_attribute('class'):
                            next_button.click()
                            await asyncio.sleep(2)
                        else:
                            logger.info("Reached last page or no next button found")
                            break
                    except Exception as e:
                        logger.info(f"No more pages available: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Error scraping opportunities: {e}")
        
        return all_tenders
    
    def _calculate_relevance(self, tender, query):
        """Calculate relevance score for a tender based on query"""
        query_terms = query.lower().split()
        title = tender.get('title', '').lower()
        description = tender.get('description', '').lower()
        
        score = 0
        for term in query_terms:
            if term in title:
                score += 0.5
            if term in description:
                score += 0.3
            # Check for partial matches
            if any(term in word for word in title.split()):
                score += 0.2
            if any(term in word for word in description.split()):
                score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    async def _setup_driver(self):
        """Setup Selenium WebDriver with enhanced configuration"""
        try:
            from selenium_utils import get_driver
            driver = get_driver()
            
            # Set page load timeout
            driver.set_page_load_timeout(30)
            
            # Set window size for better compatibility
            driver.set_window_size(1920, 1080)
            
            logger.info("Selenium WebDriver setup complete")
            return driver
            
        except Exception as e:
            logger.error(f"Error setting up WebDriver: {e}")
            raise
    
    async def _extract_tenders_from_page(self):
        """Extract tenders from current page with enhanced parsing for CanadaBuys structure"""
        tenders = []
        
        try:
            # Wait for results to load - CanadaBuys shows results in a list format
            result_selectors = [
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
            
            results_found = False
            for selector in result_selectors:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Found results container with selector: {selector}")
                    results_found = True
                    break
                except:
                    continue
            
            if not results_found:
                # Wait for any content to load
                await asyncio.sleep(5)
                logger.info("No specific results container found, proceeding with general search")
            
            # Find all tender cards - CanadaBuys uses various formats
            tender_selectors = [
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
                "div[class*='item']",       # Any item div
                "tr",                       # Table rows
                "li"                        # List items
            ]
            
            tender_cards = []
            for selector in tender_selectors:
                try:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards:
                        logger.info(f"Found {len(cards)} tender cards with selector: {selector}")
                        tender_cards = cards
                        break
                except:
                    continue
            
            if not tender_cards:
                # Fallback: look for any clickable elements that might be tenders
                all_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='tender'], a[href*='opportunity'], a[href*='bid'], a[href*='solicitation']")
                logger.info(f"Fallback: found {len(all_links)} potential tender links")
                tender_cards = all_links
            
            for card in tender_cards:
                try:
                    tender_data = await self._parse_tender_card(card)
                    if tender_data:
                        tenders.append(tender_data)
                except Exception as e:
                    logger.warning(f"Error parsing tender card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting tenders from page: {e}")
        
        return tenders
    
    async def _parse_tender_card(self, card):
        """Enhanced tender card parsing with better field extraction"""
        try:
            # Extract title and link with multiple selectors
            title_selectors = [
                "h3 a", ".tender-title a", "h2 a", "h1 a",
                ".title a", ".name a", ".heading a",
                "a[href*='tender']", "a[href*='opportunity']", "a[href*='bid']",
                "a", ".title", ".name", ".heading"
            ]
            
            title_element = None
            title = ""
            tender_url = ""
            
            for selector in title_selectors:
                try:
                    title_element = card.find_element(By.CSS_SELECTOR, selector)
                    if title_element.is_displayed():
                        title = title_element.text.strip()
                        tender_url = title_element.get_attribute('href') or ""
                        if title and tender_url:
                            logger.info(f"Found title with selector: {selector}")
                            break
                except:
                    continue
            
            if not title:
                # Fallback: get any text that might be a title
                title = card.text[:200].strip()  # First 200 chars as title
                tender_url = card.get_attribute('href') or ""
            
            # Extract tender ID from URL or text
            tender_id = self._extract_tender_id(tender_url, title)
            
            # Extract organization with multiple selectors
            org_selectors = [
                ".organization", ".buyer-name", ".buyer", ".department",
                ".agency", ".client", ".company", ".org",
                "[class*='organization']", "[class*='buyer']", "[class*='department']"
            ]
            
            organization = ""
            for selector in org_selectors:
                try:
                    org_element = card.find_element(By.CSS_SELECTOR, selector)
                    organization = org_element.text.strip()
                    if organization:
                        break
                except:
                    continue
            
            # Extract location with multiple selectors
            location_selectors = [
                ".location", ".province", ".region", ".area",
                ".city", ".state", ".territory",
                "[class*='location']", "[class*='province']", "[class*='region']"
            ]
            
            location = ""
            for selector in location_selectors:
                try:
                    location_element = card.find_element(By.CSS_SELECTOR, selector)
                    location = location_element.text.strip()
                    if location:
                        break
                except:
                    continue
            
            # Extract closing date
            closing_date = await self._extract_date(card, ".closing-date, .deadline, .due-date, [class*='closing'], [class*='deadline']")
            
            # Extract posted date
            posted_date = await self._extract_date(card, ".posted-date, .published-date, .issue-date, [class*='posted'], [class*='published']")
            
            # Extract value (if available)
            value = await self._extract_value(card)
            
            # Extract description
            description = await self._extract_description(card)
            
            # Determine priority based on content analysis
            priority = self._determine_priority(title, description)
            
            # Extract matching courses
            matching_courses = self._extract_matching_courses(title, description)
            
            # Extract categories
            categories = await self._extract_categories(card)
            
            # Extract keywords
            keywords = self._extract_keywords(title, description)
            
            # Extract contact info
            contact_email, contact_phone = await self._extract_contact_info(card)
            
            return {
                'tender_id': tender_id,
                'title': title,
                'organization': organization,
                'portal': 'CanadaBuys',
                'value': value,
                'closing_date': closing_date,
                'posted_date': posted_date,
                'description': description,
                'location': location,
                'categories': categories,
                'keywords': keywords,
                'contact_email': contact_email,
                'contact_phone': contact_phone,
                'tender_url': tender_url,
                'documents_url': None,
                'priority': priority,
                'matching_courses': matching_courses
            }
            
        except Exception as e:
            logger.warning(f"Error parsing tender card: {e}")
            return None
    
    def _extract_tender_id(self, url, title):
        """Extract tender ID from URL or title"""
        if url:
            # Try to extract from URL
            import re
            match = re.search(r'/(\d+)(?:/|$)', url)
            if match:
                return match.group(1)
        
        # Try to extract from title
        import re
        match = re.search(r'#(\d+)', title)
        if match:
            return match.group(1)
        
        # Generate ID from title hash
        import hashlib
        return hashlib.md5(title.encode()).hexdigest()[:8]
    
    async def _extract_date(self, card, selector):
        """Extract date from card element"""
        try:
            date_element = card.find_element(By.CSS_SELECTOR, selector)
            date_text = date_element.text
            return self._parse_date(date_text)
        except:
            return None
    
    def _parse_date(self, date_text):
        """Parse various date formats"""
        if not date_text:
            return None
        
        try:
            # Common date formats
            from datetime import datetime
            formats = [
                '%B %d, %Y',
                '%b %d, %Y',
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_text.strip(), fmt).isoformat()
                except:
                    continue
            
            return None
        except:
            return None
    
    async def _extract_value(self, card):
        """Extract tender value"""
        try:
            value_element = card.find_element(By.CSS_SELECTOR, ".value, .budget, .amount")
            value_text = value_element.text
            return self._parse_value(value_text)
        except:
            return 0
    
    def _parse_value(self, value_text):
        """Parse value from text"""
        if not value_text:
            return 0
        
        try:
            import re
            # Extract numbers and handle currency
            numbers = re.findall(r'[\d,]+', value_text.replace(',', ''))
            if numbers:
                value = float(numbers[0])
                
                # Handle multipliers (K, M, B)
                if 'K' in value_text.upper():
                    value *= 1000
                elif 'M' in value_text.upper():
                    value *= 1000000
                elif 'B' in value_text.upper():
                    value *= 1000000000
                
                return int(value)
        except:
            pass
        
        return 0
    
    async def _extract_description(self, card):
        """Extract tender description"""
        try:
            desc_element = card.find_element(By.CSS_SELECTOR, ".description, .summary, .details")
            return desc_element.text
        except:
            return ""
    
    def _determine_priority(self, title, description):
        """Determine tender priority based on content analysis"""
        text = f"{title} {description}".lower()
        
        # High priority indicators
        high_priority_terms = [
            'training', 'professional development', 'certification',
            'AWS', 'Azure', 'cybersecurity', 'project management',
            'agile', 'scrum', 'leadership', 'coaching'
        ]
        
        # Medium priority indicators
        medium_priority_terms = [
            'consulting', 'implementation', 'change management',
            'development', 'education', 'learning'
        ]
        
        high_count = sum(1 for term in high_priority_terms if term in text)
        medium_count = sum(1 for term in medium_priority_terms if term in text)
        
        if high_count >= 2:
            return 'high'
        elif high_count >= 1 or medium_count >= 2:
            return 'medium'
        else:
            return 'low'
    
    def _extract_matching_courses(self, title, description):
        """Extract matching TKA courses from content"""
        text = f"{title} {description}".lower()
        matching_courses = []
        
        # Course mappings
        course_mappings = {
            'aws': 'AWS Training',
            'azure': 'Azure Training',
            'cloud': 'Cloud Computing',
            'cybersecurity': 'Cybersecurity Training',
            'cissp': 'CISSP Certification',
            'project management': 'Project Management',
            'pmp': 'PMP Certification',
            'prince2': 'PRINCE2 Certification',
            'agile': 'Agile Training',
            'scrum': 'Scrum Training',
            'leadership': 'Leadership Development',
            'itil': 'ITIL Training',
            'devops': 'DevOps Training',
            'data analytics': 'Data Analytics',
            'business intelligence': 'Business Intelligence',
            'change management': 'Change Management',
            'coaching': 'Executive Coaching'
        }
        
        for keyword, course in course_mappings.items():
            if keyword in text:
                matching_courses.append(course)
        
        return matching_courses
    
    async def _extract_categories(self, card):
        """Extract tender categories"""
        try:
            category_elements = card.find_elements(By.CSS_SELECTOR, ".category, .tag, .classification")
            categories = []
            for element in category_elements:
                category = element.text
                if category:
                    categories.append(category.strip())
            return categories
        except:
            return []
    
    def _extract_keywords(self, title, description):
        """Extract keywords from title and description"""
        text = f"{title} {description}".lower()
        keywords = []
        
        # Extract meaningful keywords
        import re
        words = re.findall(r'\b\w{4,}\b', text)
        
        # Filter for relevant keywords
        relevant_words = [
            'training', 'development', 'consulting', 'implementation',
            'management', 'leadership', 'technology', 'digital',
            'transformation', 'change', 'process', 'system'
        ]
        
        for word in words:
            if word in relevant_words and word not in keywords:
                keywords.append(word)
        
        return keywords[:10]  # Limit to 10 keywords
    
    async def _extract_contact_info(self, card):
        """Extract contact information"""
        try:
            # Look for contact elements
            contact_elements = card.find_elements(By.CSS_SELECTOR, ".contact, .contact-info, .buyer-contact")
            
            email = None
            phone = None
            
            for element in contact_elements:
                text = element.text
                
                # Extract email
                import re
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                if email_match:
                    email = email_match.group(0)
                
                # Extract phone
                phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
                if phone_match:
                    phone = phone_match.group(0)
            
            return email, phone
        except:
            return None, None

class BidsAndTendersScraper:
    """Scraper for Bids&Tenders portal"""
    
    def __init__(self):
        """Initialize Bids&Tenders scraper"""
        self.base_url = "https://www.bidsandtenders.ca"
        self.search_url = "https://www.bidsandtenders.ca/section/opportunities/opportunities.asp"
        
    async def search(self, query, max_pages=5):
        """Search Bids&Tenders portal with multiple strategies"""
        tenders = []
        
        try:
            driver = await self._setup_driver()
            if not driver:
                logger.error("Could not setup driver for Bids&Tenders")
                return tenders
            
            # Handle cookie consent
            await self._handle_cookie_consent(driver)
            
            # Search strategies for Bids&Tenders
            search_strategies = [
                {"term": query, "description": f"Direct search: {query}"},
                {"term": "training services", "description": "Training services"},
                {"term": "professional development", "description": "Professional development"},
                {"term": "consulting services", "description": "Consulting services"},
                {"term": "education services", "description": "Education services"},
                {"term": "", "description": "All opportunities"}  # No search term
            ]
            
            for strategy in search_strategies:
                try:
                    logger.info(f"Bids&Tenders search strategy: {strategy['description']}")
                    strategy_tenders = await self._scrape_opportunities(driver, strategy['term'], max_pages)
                    tenders.extend(strategy_tenders)
                    logger.info(f"Found {len(strategy_tenders)} tenders for strategy: {strategy['description']}")
                except Exception as e:
                    logger.warning(f"Strategy failed for Bids&Tenders: {e}")
                    continue
            
            driver.quit()
            
        except Exception as e:
            logger.error(f"Error in Bids&Tenders search: {e}")
            
        return tenders
    
    async def _setup_driver(self):
        """Setup Selenium WebDriver"""
        try:
            from selenium_utils import get_driver
            return get_driver()
        except Exception as e:
            logger.error(f"Error setting up driver: {e}")
            return None
    
    async def _handle_cookie_consent(self, driver):
        """Handle cookie consent popup"""
        try:
            cookie_selectors = [
                "button[class*='accept']",
                "button[class*='Accept']",
                "button[class*='cookie']",
                "button[class*='Cookie']",
                ".cookie-accept",
                ".accept-cookies",
                "button:contains('Accept')",
                "button:contains('Accept All')"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if cookie_btn and cookie_btn.is_displayed():
                        cookie_btn.click()
                        await asyncio.sleep(2)
                        logger.info("Accepted cookies on Bids&Tenders")
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Error handling cookie consent: {e}")
    
    async def _scrape_opportunities(self, driver, query, max_pages):
        """Scrape opportunities from Bids&Tenders"""
        tenders = []
        
        try:
            # Navigate to search page
            search_params = {
                'type': '1',
                'show': 'all',
                'rregion': 'ALL'
            }
            
            if query:
                search_params['keys'] = query
            
            # Build search URL
            search_url = f"{self.search_url}?{'&'.join([f'{k}={v}' for k, v in search_params.items()])}"
            driver.get(search_url)
            await asyncio.sleep(3)
            
            # Process multiple pages
            for page in range(1, max_pages + 1):
                try:
                    logger.info(f"Processing Bids&Tenders page {page}")
                    
                    # Extract tenders from current page
                    page_tenders = await self._extract_tenders_from_page(driver)
                    tenders.extend(page_tenders)
                    
                    # Try to go to next page
                    if page < max_pages:
                        next_page_clicked = await self._go_to_next_page(driver)
                        if not next_page_clicked:
                            logger.info("No more pages available")
                            break
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"Error processing page {page}: {e}")
                    break
            
        except Exception as e:
            logger.error(f"Error scraping Bids&Tenders opportunities: {e}")
        
        return tenders
    
    async def _extract_tenders_from_page(self, driver):
        """Extract tender information from current page"""
        tenders = []
        
        try:
            # Look for tender listings
            tender_selectors = [
                ".opportunity-item",
                ".tender-item",
                ".bid-item",
                "tr[class*='opportunity']",
                "tr[class*='tender']",
                "tr[class*='bid']",
                ".result-item",
                "div[class*='opportunity']",
                "div[class*='tender']"
            ]
            
            tender_elements = []
            for selector in tender_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        tender_elements = elements
                        logger.info(f"Found {len(elements)} tender elements using selector: {selector}")
                        break
                except:
                    continue
            
            # Parse each tender element
            for element in tender_elements[:50]:  # Limit to 50 per page
                try:
                    tender_data = await self._parse_tender_element(element)
                    if tender_data:
                        tenders.append(tender_data)
                except Exception as e:
                    logger.warning(f"Error parsing tender element: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting tenders from page: {e}")
        
        return tenders
    
    async def _parse_tender_element(self, element):
        """Parse individual tender element"""
        try:
            # Extract basic information
            title = self._extract_text(element, [
                "h3", "h4", ".title", ".opportunity-title", ".tender-title",
                "td:nth-child(2)", "td:nth-child(1)"
            ])
            
            if not title:
                return None
            
            # Extract organization
            organization = self._extract_text(element, [
                ".organization", ".org", ".company", ".agency",
                "td:nth-child(3)", "td:nth-child(2)"
            ]) or "Unknown Organization"
            
            # Extract tender ID
            tender_id = self._extract_tender_id(element, title)
            
            # Extract dates
            closing_date = await self._extract_date(element, [
                ".closing-date", ".deadline", ".due-date",
                "td:nth-child(4)", "td:nth-child(5)"
            ])
            
            posted_date = await self._extract_date(element, [
                ".posted-date", ".publish-date", ".issue-date",
                "td:nth-child(3)", "td:nth-child(4)"
            ]) or datetime.utcnow()
            
            # Extract value
            value = await self._extract_value(element)
            
            # Extract URL
            tender_url = self._extract_url(element)
            
            # Extract description
            description = self._extract_text(element, [
                ".description", ".summary", ".details",
                "td:nth-child(6)", "td:nth-child(7)"
            ]) or ""
            
            tender = {
                'tender_id': tender_id,
                'title': title,
                'organization': organization,
                'portal': 'Bids&Tenders',
                'value': value,
                'closing_date': closing_date,
                'posted_date': posted_date,
                'location': 'Canada',
                'tender_url': tender_url,
                'description': description,
                'categories': [],
                'keywords': self._extract_keywords(title, description),
                'matching_courses': self._extract_matching_courses(title, description),
                'priority': self._determine_priority(title, description)
            }
            
            return tender
            
        except Exception as e:
            logger.warning(f"Error parsing tender element: {e}")
            return None
    
    def _extract_text(self, element, selectors):
        """Extract text from element using multiple selectors"""
        for selector in selectors:
            try:
                found = element.find_element(By.CSS_SELECTOR, selector)
                if found and found.text.strip():
                    return found.text.strip()
            except:
                continue
        return ""
    
    def _extract_tender_id(self, element, title):
        """Extract tender ID from element or generate from title"""
        # Try to find tender ID in various locations
        id_selectors = [
            ".tender-id", ".opportunity-id", ".bid-id",
            "td:nth-child(1)", "td:first-child"
        ]
        
        for selector in id_selectors:
            try:
                found = element.find_element(By.CSS_SELECTOR, selector)
                if found and found.text.strip():
                    return found.text.strip()
            except:
                continue
        
        # Generate ID from title
        return hashlib.md5(title.encode()).hexdigest()[:8]
    
    async def _extract_date(self, element, selectors):
        """Extract date from element"""
        for selector in selectors:
            try:
                found = element.find_element(By.CSS_SELECTOR, selector)
                if found and found.text.strip():
                    return parse_date(found.text.strip())
            except:
                continue
        return None
    
    async def _extract_value(self, element):
        """Extract monetary value from element"""
        value_selectors = [
            ".value", ".amount", ".budget", ".estimated-value",
            "td:nth-child(5)", "td:nth-child(6)"
        ]
        
        for selector in value_selectors:
            try:
                found = element.find_element(By.CSS_SELECTOR, selector)
                if found and found.text.strip():
                    return parse_value(found.text.strip())
            except:
                continue
        return 0.0
    
    def _extract_url(self, element):
        """Extract tender URL from element"""
        try:
            # Look for links
            links = element.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute('href')
                if href and ('opportunity' in href or 'tender' in href or 'bid' in href):
                    return href
        except:
            pass
        
        return self.base_url
    
    def _extract_keywords(self, title, description):
        """Extract keywords from title and description"""
        text = f"{title} {description}".lower()
        keywords = []
        
        # Training-related keywords
        training_keywords = [
            'training', 'education', 'learning', 'development', 'workshop',
            'seminar', 'course', 'certification', 'professional development',
            'skill development', 'capacity building', 'upskilling', 'reskilling'
        ]
        
        for keyword in training_keywords:
            if keyword in text:
                keywords.append(keyword)
        
        return keywords
    
    def _extract_matching_courses(self, title, description):
        """Extract matching courses from title and description"""
        text = f"{title} {description}".lower()
        matching_courses = []
        
        # Map keywords to TKA courses
        course_mapping = {
            'project management': 'Project Management',
            'leadership': 'Leadership',
            'communication': 'Communication',
            'negotiation': 'Negotiation',
            'contract management': 'Contract Management',
            'procurement': 'Procurement',
            'supply chain': 'Supply Chain',
            'risk management': 'Risk Management',
            'strategic planning': 'Strategic Planning',
            'change management': 'Change Management',
            'team building': 'Team Building',
            'conflict resolution': 'Conflict Resolution',
            'time management': 'Time Management',
            'problem solving': 'Problem Solving',
            'decision making': 'Decision Making',
            'financial management': 'Financial Management',
            'human resources': 'Human Resources',
            'marketing': 'Marketing',
            'sales': 'Sales',
            'customer service': 'Customer Service',
            'quality management': 'Quality Management',
            'process improvement': 'Process Improvement',
            'innovation': 'Innovation',
            'digital transformation': 'Digital Transformation',
            'data analysis': 'Data Analysis',
            'business intelligence': 'Business Intelligence',
            'cybersecurity': 'Cybersecurity',
            'cloud computing': 'Cloud Computing',
            'agile': 'Agile',
            'scrum': 'Scrum',
            'lean six sigma': 'Lean Six Sigma',
            'iso': 'ISO Standards',
            'compliance': 'Compliance',
            'regulatory': 'Regulatory Affairs'
        }
        
        for keyword, course in course_mapping.items():
            if keyword in text:
                matching_courses.append(course)
        
        return matching_courses
    
    def _determine_priority(self, title, description):
        """Determine priority based on content"""
        text = f"{title} {description}".lower()
        
        # High priority keywords
        high_priority = [
            'training', 'education', 'learning', 'development', 'workshop',
            'seminar', 'course', 'certification', 'professional development',
            'consulting', 'advisory', 'implementation', 'change management'
        ]
        
        # Medium priority keywords
        medium_priority = [
            'service', 'support', 'maintenance', 'management', 'administration',
            'coordination', 'facilitation', 'delivery', 'provision'
        ]
        
        for keyword in high_priority:
            if keyword in text:
                return 'high'
        
        for keyword in medium_priority:
            if keyword in text:
                return 'medium'
        
        return 'low'
    
    async def _go_to_next_page(self, driver):
        """Navigate to next page"""
        try:
            next_selectors = [
                "a[class*='next']",
                "a[class*='Next']",
                ".pagination .next",
                "a[aria-label*='Next']",
                "a[title*='Next']",
                "a:contains('Next')",
                "a:contains('>')"
            ]
            
            for selector in next_selectors:
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if next_btn and next_btn.is_displayed() and next_btn.is_enabled():
                        driver.execute_script("arguments[0].click();", next_btn)
                        await asyncio.sleep(3)
                        logger.info("Navigated to next page")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.warning(f"Error navigating to next page: {e}")
            return False


class BiddingoScraper:
    """Scraper for Biddingo portal"""
    
    def __init__(self):
        """Initialize Biddingo scraper"""
        self.base_url = "https://www.biddingo.com"
        self.search_url = "https://www.biddingo.com/search"
        
    async def search(self, query, max_pages=5):
        """Search Biddingo portal with multiple strategies"""
        tenders = []
        
        try:
            driver = await self._setup_driver()
            if not driver:
                logger.error("Could not setup driver for Biddingo")
                return tenders
            
            # Handle cookie consent
            await self._handle_cookie_consent(driver)
            
            # Search strategies for Biddingo
            search_strategies = [
                {"term": query, "description": f"Direct search: {query}"},
                {"term": "training services", "description": "Training services"},
                {"term": "professional development", "description": "Professional development"},
                {"term": "consulting services", "description": "Consulting services"},
                {"term": "education services", "description": "Education services"},
                {"term": "", "description": "All opportunities"}  # No search term
            ]
            
            for strategy in search_strategies:
                try:
                    logger.info(f"Biddingo search strategy: {strategy['description']}")
                    strategy_tenders = await self._scrape_opportunities(driver, strategy['term'], max_pages)
                    tenders.extend(strategy_tenders)
                    logger.info(f"Found {len(strategy_tenders)} tenders for strategy: {strategy['description']}")
                except Exception as e:
                    logger.warning(f"Strategy failed for Biddingo: {e}")
                    continue
            
            driver.quit()
            
        except Exception as e:
            logger.error(f"Error in Biddingo search: {e}")
            
        return tenders
    
    async def _setup_driver(self):
        """Setup Selenium WebDriver"""
        try:
            from selenium_utils import get_driver
            return get_driver()
        except Exception as e:
            logger.error(f"Error setting up driver: {e}")
            return None
    
    async def _handle_cookie_consent(self, driver):
        """Handle cookie consent popup"""
        try:
            cookie_selectors = [
                "button[class*='accept']",
                "button[class*='Accept']",
                "button[class*='cookie']",
                "button[class*='Cookie']",
                ".cookie-accept",
                ".accept-cookies",
                "button:contains('Accept')",
                "button:contains('Accept All')"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if cookie_btn and cookie_btn.is_displayed():
                        cookie_btn.click()
                        await asyncio.sleep(2)
                        logger.info("Accepted cookies on Biddingo")
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Error handling cookie consent: {e}")
    
    async def _scrape_opportunities(self, driver, query, max_pages):
        """Scrape opportunities from Biddingo"""
        tenders = []
        
        try:
            # Navigate to search page
            if query:
                search_url = f"{self.search_url}?q={query}"
            else:
                search_url = f"{self.base_url}/opportunities"
            
            driver.get(search_url)
            await asyncio.sleep(3)
            
            # Process multiple pages
            for page in range(1, max_pages + 1):
                try:
                    logger.info(f"Processing Biddingo page {page}")
                    
                    # Extract tenders from current page
                    page_tenders = await self._extract_tenders_from_page(driver)
                    tenders.extend(page_tenders)
                    
                    # Try to go to next page
                    if page < max_pages:
                        next_page_clicked = await self._go_to_next_page(driver)
                        if not next_page_clicked:
                            logger.info("No more pages available")
                            break
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"Error processing page {page}: {e}")
                    break
            
        except Exception as e:
            logger.error(f"Error scraping Biddingo opportunities: {e}")
        
        return tenders
    
    async def _extract_tenders_from_page(self, driver):
        """Extract tender information from current page"""
        tenders = []
        
        try:
            # Look for tender listings
            tender_selectors = [
                ".opportunity-item",
                ".tender-item",
                ".bid-item",
                ".listing-item",
                ".result-item",
                "div[class*='opportunity']",
                "div[class*='tender']",
                "div[class*='bid']",
                "div[class*='listing']",
                "article",
                ".card",
                ".item"
            ]
            
            tender_elements = []
            for selector in tender_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        tender_elements = elements
                        logger.info(f"Found {len(elements)} tender elements using selector: {selector}")
                        break
                except:
                    continue
            
            # Parse each tender element
            for element in tender_elements[:50]:  # Limit to 50 per page
                try:
                    tender_data = await self._parse_tender_element(element)
                    if tender_data:
                        tenders.append(tender_data)
                except Exception as e:
                    logger.warning(f"Error parsing tender element: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting tenders from page: {e}")
        
        return tenders
    
    async def _parse_tender_element(self, element):
        """Parse individual tender element"""
        try:
            # Extract basic information
            title = self._extract_text(element, [
                "h3", "h4", ".title", ".opportunity-title", ".tender-title",
                ".item-title", ".listing-title", ".card-title"
            ])
            
            if not title:
                return None
            
            # Extract organization
            organization = self._extract_text(element, [
                ".organization", ".org", ".company", ".agency", ".client",
                ".buyer", ".purchaser", ".issuer"
            ]) or "Unknown Organization"
            
            # Extract tender ID
            tender_id = self._extract_tender_id(element, title)
            
            # Extract dates
            closing_date = await self._extract_date(element, [
                ".closing-date", ".deadline", ".due-date", ".bid-deadline",
                ".submission-deadline", ".closing-time"
            ])
            
            posted_date = await self._extract_date(element, [
                ".posted-date", ".publish-date", ".issue-date", ".published-date",
                ".created-date", ".posted"
            ]) or datetime.utcnow()
            
            # Extract value
            value = await self._extract_value(element)
            
            # Extract URL
            tender_url = self._extract_url(element)
            
            # Extract description
            description = self._extract_text(element, [
                ".description", ".summary", ".details", ".content",
                ".item-description", ".listing-description"
            ]) or ""
            
            tender = {
                'tender_id': tender_id,
                'title': title,
                'organization': organization,
                'portal': 'Biddingo',
                'value': value,
                'closing_date': closing_date,
                'posted_date': posted_date,
                'location': 'Canada',
                'tender_url': tender_url,
                'description': description,
                'categories': [],
                'keywords': self._extract_keywords(title, description),
                'matching_courses': self._extract_matching_courses(title, description),
                'priority': self._determine_priority(title, description)
            }
            
            return tender
            
        except Exception as e:
            logger.warning(f"Error parsing tender element: {e}")
            return None
    
    def _extract_text(self, element, selectors):
        """Extract text from element using multiple selectors"""
        for selector in selectors:
            try:
                found = element.find_element(By.CSS_SELECTOR, selector)
                if found and found.text.strip():
                    return found.text.strip()
            except:
                continue
        return ""
    
    def _extract_tender_id(self, element, title):
        """Extract tender ID from element or generate from title"""
        # Try to find tender ID in various locations
        id_selectors = [
            ".tender-id", ".opportunity-id", ".bid-id", ".item-id",
            ".listing-id", ".reference", ".ref", ".number"
        ]
        
        for selector in id_selectors:
            try:
                found = element.find_element(By.CSS_SELECTOR, selector)
                if found and found.text.strip():
                    return found.text.strip()
            except:
                continue
        
        # Generate ID from title
        return hashlib.md5(title.encode()).hexdigest()[:8]
    
    async def _extract_date(self, element, selectors):
        """Extract date from element"""
        for selector in selectors:
            try:
                found = element.find_element(By.CSS_SELECTOR, selector)
                if found and found.text.strip():
                    return parse_date(found.text.strip())
            except:
                continue
        return None
    
    async def _extract_value(self, element):
        """Extract monetary value from element"""
        value_selectors = [
            ".value", ".amount", ".budget", ".estimated-value",
            ".contract-value", ".tender-value", ".bid-value"
        ]
        
        for selector in value_selectors:
            try:
                found = element.find_element(By.CSS_SELECTOR, selector)
                if found and found.text.strip():
                    return parse_value(found.text.strip())
            except:
                continue
        return 0.0
    
    def _extract_url(self, element):
        """Extract tender URL from element"""
        try:
            # Look for links
            links = element.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute('href')
                if href and ('opportunity' in href or 'tender' in href or 'bid' in href):
                    return href
        except:
            pass
        
        return self.base_url
    
    def _extract_keywords(self, title, description):
        """Extract keywords from title and description"""
        text = f"{title} {description}".lower()
        keywords = []
        
        # Training-related keywords
        training_keywords = [
            'training', 'education', 'learning', 'development', 'workshop',
            'seminar', 'course', 'certification', 'professional development',
            'skill development', 'capacity building', 'upskilling', 'reskilling'
        ]
        
        for keyword in training_keywords:
            if keyword in text:
                keywords.append(keyword)
        
        return keywords
    
    def _extract_matching_courses(self, title, description):
        """Extract matching courses from title and description"""
        text = f"{title} {description}".lower()
        matching_courses = []
        
        # Map keywords to TKA courses
        course_mapping = {
            'project management': 'Project Management',
            'leadership': 'Leadership',
            'communication': 'Communication',
            'negotiation': 'Negotiation',
            'contract management': 'Contract Management',
            'procurement': 'Procurement',
            'supply chain': 'Supply Chain',
            'risk management': 'Risk Management',
            'strategic planning': 'Strategic Planning',
            'change management': 'Change Management',
            'team building': 'Team Building',
            'conflict resolution': 'Conflict Resolution',
            'time management': 'Time Management',
            'problem solving': 'Problem Solving',
            'decision making': 'Decision Making',
            'financial management': 'Financial Management',
            'human resources': 'Human Resources',
            'marketing': 'Marketing',
            'sales': 'Sales',
            'customer service': 'Customer Service',
            'quality management': 'Quality Management',
            'process improvement': 'Process Improvement',
            'innovation': 'Innovation',
            'digital transformation': 'Digital Transformation',
            'data analysis': 'Data Analysis',
            'business intelligence': 'Business Intelligence',
            'cybersecurity': 'Cybersecurity',
            'cloud computing': 'Cloud Computing',
            'agile': 'Agile',
            'scrum': 'Scrum',
            'lean six sigma': 'Lean Six Sigma',
            'iso': 'ISO Standards',
            'compliance': 'Compliance',
            'regulatory': 'Regulatory Affairs'
        }
        
        for keyword, course in course_mapping.items():
            if keyword in text:
                matching_courses.append(course)
        
        return matching_courses
    
    def _determine_priority(self, title, description):
        """Determine priority based on content"""
        text = f"{title} {description}".lower()
        
        # High priority keywords
        high_priority = [
            'training', 'education', 'learning', 'development', 'workshop',
            'seminar', 'course', 'certification', 'professional development',
            'consulting', 'advisory', 'implementation', 'change management'
        ]
        
        # Medium priority keywords
        medium_priority = [
            'service', 'support', 'maintenance', 'management', 'administration',
            'coordination', 'facilitation', 'delivery', 'provision'
        ]
        
        for keyword in high_priority:
            if keyword in text:
                return 'high'
        
        for keyword in medium_priority:
            if keyword in text:
                return 'medium'
        
        return 'low'
    
    async def _go_to_next_page(self, driver):
        """Navigate to next page"""
        try:
            next_selectors = [
                "a[class*='next']",
                "a[class*='Next']",
                ".pagination .next",
                "a[aria-label*='Next']",
                "a[title*='Next']",
                "a:contains('Next')",
                "a:contains('>')",
                "button[class*='next']",
                "button:contains('Next')"
            ]
            
            for selector in next_selectors:
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if next_btn and next_btn.is_displayed() and next_btn.is_enabled():
                        driver.execute_script("arguments[0].click();", next_btn)
                        await asyncio.sleep(3)
                        logger.info("Navigated to next page")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.warning(f"Error navigating to next page: {e}")
            return False