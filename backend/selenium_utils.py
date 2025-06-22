# selenium_utils.py - Selenium Grid utilities with health checks and retry logic
import logging
import time
import random
import requests  # type: ignore
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException, 
    TimeoutException, 
    NoSuchElementException,
    SessionNotCreatedException,
    NoSuchWindowException
)
from typing import Optional, Dict, Any, Union
import os

logger = logging.getLogger(__name__)

class SeleniumGridManager:
    """Manages Selenium Grid connections with health checks and retry logic"""
    
    def __init__(self, hub_url: Optional[str] = None):
        self.hub_url = hub_url or os.getenv('SELENIUM_HUB_URL', 'http://selenium-hub:4444/wd/hub')
        self.max_retries = 5
        self.retry_delay = 2
        self.health_check_interval = 30
        
    def check_grid_health(self) -> bool:
        """Check if Selenium Grid is healthy"""
        try:
            response = requests.get(f"{self.hub_url}/status", timeout=10)
            if response.status_code == 200:
                status = response.json()
                ready = status.get('value', {}).get('ready', False)
                nodes = status.get('value', {}).get('nodes', [])
                available_nodes = len([n for n in nodes if n.get('availability') == 'UP'])
                
                logger.info(f"Selenium Grid health check: Ready={ready}, Available nodes={available_nodes}")
                return ready and available_nodes > 0
            return False
        except Exception as e:
            logger.error(f"Selenium Grid health check failed: {e}")
            return False
    
    def wait_for_grid_ready(self, timeout: int = 300) -> bool:
        """Wait for Selenium Grid to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_grid_health():
                logger.info("Selenium Grid is ready")
                return True
            logger.info(f"Waiting for Selenium Grid to be ready... ({timeout - (time.time() - start_time):.0f}s remaining)")
            time.sleep(10)
        
        logger.error("Selenium Grid failed to become ready within timeout")
        return False
    
    def get_chrome_options(self) -> Options:
        """Get Chrome options with enhanced anti-bot measures"""
        options = Options()
        
        # Enhanced anti-bot evasion
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Random user agent rotation
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        # Additional stealth options
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Window size
        options.add_argument('--window-size=1920,1080')
        
        return options
    
    def create_driver(self, max_attempts: int = 3) -> Optional[webdriver.Remote]:
        """Create WebDriver with retry logic"""
        for attempt in range(max_attempts):
            try:
                logger.info(f"Creating WebDriver (attempt {attempt + 1}/{max_attempts})")
                
                # Check grid health before creating driver
                if not self.check_grid_health():
                    logger.warning(f"Grid not healthy on attempt {attempt + 1}, waiting...")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                
                options = self.get_chrome_options()
                driver = webdriver.Remote(
                    command_executor=self.hub_url,
                    options=options
                )
                
                # Test the driver
                driver.get("data:text/html,<html><body>Test</body></html>")
                logger.info("WebDriver successfully created and tested")
                return driver
                
            except SessionNotCreatedException as e:
                logger.warning(f"Session creation failed on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                continue
            except Exception as e:
                logger.error(f"Driver creation failed on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                continue
        
        logger.error("Failed to create WebDriver after all attempts")
        return None
    
    def safe_quit_driver(self, driver: Optional[webdriver.Remote]) -> None:
        """Safely quit WebDriver"""
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.warning(f"Error quitting driver: {e}")
    
    def stealth_navigation(self, driver: webdriver.Remote, url: str, max_attempts: int = 3) -> bool:
        """Navigate to URL with stealth measures and retry logic"""
        for attempt in range(max_attempts):
            try:
                logger.info(f"Navigating to {url} (attempt {attempt + 1}/{max_attempts})")
                
                # Add random delay to appear more human-like
                time.sleep(random.uniform(1, 3))
                
                # Navigate to URL
                driver.get(url)
                
                # Wait for page to load
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Additional random delay
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
    
    def find_element_safe(self, driver: webdriver.Remote, by: str, value: str, timeout: int = 10) -> Optional[Any]:
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
    
    def find_elements_safe(self, driver: webdriver.Remote, by: str, value: str, timeout: int = 10) -> list:
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

# Global selenium manager instance
selenium_manager = None

def get_selenium_manager() -> SeleniumGridManager:
    """Get or create the global Selenium Grid manager"""
    global selenium_manager
    if selenium_manager is None:
        selenium_manager = SeleniumGridManager()
    return selenium_manager

def get_driver():
    """Get a WebDriver instance for the enhanced scrapers"""
    manager = get_selenium_manager()
    
    # Wait for grid to be ready
    if not manager.wait_for_grid_ready():
        raise RuntimeError("Selenium Grid is not ready")
    
    # Create driver
    driver = manager.create_driver()
    if driver is None:
        raise RuntimeError("Failed to create WebDriver")
    
    return driver 