# local_selenium.py - Local Selenium setup without Grid
import logging
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException, 
    TimeoutException, 
    NoSuchElementException,
    SessionNotCreatedException
)
from typing import Optional, Any
import os

logger = logging.getLogger(__name__)

class LocalSeleniumManager:
    """Local Selenium manager without Grid dependency"""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 2
        
    def get_chrome_options(self) -> Options:
        """Get Chrome options for local driver"""
        options = Options()
        
        # Essential headless options
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Anti-bot detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User agent rotation
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        # Performance options
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')  # Remove if JS is needed
        
        return options
    
    def create_driver(self, max_attempts: int = 3) -> Optional[webdriver.Chrome]:
        """Create local Chrome WebDriver"""
        for attempt in range(max_attempts):
            try:
                logger.info(f"Creating local Chrome driver (attempt {attempt + 1}/{max_attempts})")
                
                # Try different ChromeDriver paths
                driver_paths = [
                    '/usr/bin/chromedriver',
                    '/usr/local/bin/chromedriver',
                    'chromedriver'
                ]
                
                service = None
                for path in driver_paths:
                    try:
                        service = Service(path)
                        break
                    except Exception:
                        continue
                
                if service is None:
                    logger.error("ChromeDriver not found in any expected location")
                    return None
                
                options = self.get_chrome_options()
                
                # Try to create the driver
                driver = webdriver.Chrome(service=service, options=options)
                
                # Test the driver
                driver.get("data:text/html,<html><body>Test</body></html>")
                logger.info("Local Chrome driver successfully created and tested")
                return driver
                
            except Exception as e:
                logger.warning(f"Local driver creation failed on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                continue
        
        logger.error("Failed to create local Chrome driver after all attempts")
        return None
    
    def safe_quit_driver(self, driver: Optional[webdriver.Chrome]) -> None:
        """Safely quit WebDriver"""
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.warning(f"Error quitting driver: {e}")
    
    def stealth_navigation(self, driver: webdriver.Chrome, url: str, max_attempts: int = 3) -> bool:
        """Navigate to URL with stealth measures"""
        for attempt in range(max_attempts):
            try:
                logger.info(f"Navigating to {url} (attempt {attempt + 1}/{max_attempts})")
                
                # Random delay
                time.sleep(random.uniform(1, 3))
                
                # Navigate
                driver.get(url)
                
                # Wait for page load
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Additional delay
                time.sleep(random.uniform(2, 5))
                
                logger.info(f"Successfully navigated to {url}")
                return True
                
            except TimeoutException:
                logger.warning(f"Navigation timeout on attempt {attempt + 1}")
                if attempt < max_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                continue
            except Exception as e:
                logger.error(f"Navigation failed on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                continue
        
        logger.error(f"Failed to navigate to {url} after all attempts")
        return False
    
    def find_element_safe(self, driver: webdriver.Chrome, by: str, value: str, timeout: int = 10) -> Optional[Any]:
        """Safely find element with timeout"""
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.warning(f"Element not found: {by}={value}")
            return None
        except Exception as e:
            logger.error(f"Error finding element {by}={value}: {e}")
            return None
    
    def find_elements_safe(self, driver: webdriver.Chrome, by: str, value: str, timeout: int = 10) -> list:
        """Safely find elements with timeout"""
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            elements = driver.find_elements(by, value)
            return elements
        except TimeoutException:
            logger.warning(f"Elements not found: {by}={value}")
            return []
        except Exception as e:
            logger.error(f"Error finding elements {by}={value}: {e}")
            return []

# Global local selenium manager instance
local_selenium_manager = None

def get_local_selenium_manager() -> LocalSeleniumManager:
    """Get or create the local selenium manager"""
    global local_selenium_manager
    if local_selenium_manager is None:
        local_selenium_manager = LocalSeleniumManager()
    return local_selenium_manager

def get_local_driver():
    """Get a local WebDriver instance"""
    manager = get_local_selenium_manager()
    driver = manager.create_driver()
    if driver is None:
        raise RuntimeError("Failed to create local WebDriver")
    return driver