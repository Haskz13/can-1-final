#!/usr/bin/env python3
import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def examine_merx_structure():
    """Examine MERX search page structure to find correct selectors"""
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    driver = None
    try:
        # Connect to Selenium Grid
        driver = webdriver.Remote(
            command_executor='http://selenium-hub:4444/wd/hub',
            options=chrome_options
        )
        
        logger.info("🚀 Examining MERX search page structure...")
        
        # Navigate to MERX search page
        search_url = "https://www.merx.com/public/solicitations/search"
        driver.get(search_url)
        
        # Wait for page to load
        time.sleep(5)
        
        logger.info(f"Current URL: {driver.current_url}")
        logger.info(f"Page title: {driver.title}")
        
        # Take screenshot for debugging
        driver.save_screenshot("/app/merx_page.png")
        logger.info("Screenshot saved to /app/merx_page.png")
        
        # Look for search elements
        logger.info("🔍 Looking for search elements...")
        
        # Try different selectors for search input
        search_selectors = [
            "input[type='text']",
            "input[name*='search']",
            "input[id*='search']",
            ".search-input",
            "#search",
            "input[placeholder*='search']",
            "input[placeholder*='Search']",
            ".form-control",
            "input"
        ]
        
        for selector in search_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                logger.info(f"Selector '{selector}': Found {len(elements)} elements")
                
                for i, elem in enumerate(elements[:3]):  # Show first 3
                    try:
                        tag_name = elem.tag_name
                        element_type = elem.get_attribute("type")
                        element_id = elem.get_attribute("id")
                        element_name = elem.get_attribute("name")
                        element_class = elem.get_attribute("class")
                        placeholder = elem.get_attribute("placeholder")
                        is_displayed = elem.is_displayed()
                        is_enabled = elem.is_enabled()
                        
                        logger.info(f"  Element {i+1}: tag={tag_name}, type={element_type}, id={element_id}, name={element_name}, class={element_class}, placeholder={placeholder}, displayed={is_displayed}, enabled={is_enabled}")
                        
                        if is_displayed and is_enabled:
                            logger.info(f"  ✅ This element looks interactable!")
                            
                    except Exception as e:
                        logger.warning(f"  Error examining element {i+1}: {e}")
                        
            except Exception as e:
                logger.warning(f"Error with selector '{selector}': {e}")
        
        # Look for search buttons
        logger.info("🔍 Looking for search buttons...")
        
        button_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            ".search-button",
            ".btn-search",
            "button:contains('Search')",
            "button",
            ".btn"
        ]
        
        for selector in button_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                logger.info(f"Button selector '{selector}': Found {len(elements)} elements")
                
                for i, elem in enumerate(elements[:3]):  # Show first 3
                    try:
                        tag_name = elem.tag_name
                        element_type = elem.get_attribute("type")
                        element_id = elem.get_attribute("id")
                        element_class = elem.get_attribute("class")
                        element_text = elem.text
                        is_displayed = elem.is_displayed()
                        is_enabled = elem.is_enabled()
                        
                        logger.info(f"  Button {i+1}: tag={tag_name}, type={element_type}, id={element_id}, class={element_class}, text='{element_text}', displayed={is_displayed}, enabled={is_enabled}")
                        
                        if is_displayed and is_enabled:
                            logger.info(f"  ✅ This button looks clickable!")
                            
                    except Exception as e:
                        logger.warning(f"  Error examining button {i+1}: {e}")
                        
            except Exception as e:
                logger.warning(f"Error with button selector '{selector}': {e}")
        
        # Check if we're on a different page than expected
        if "search" not in driver.current_url.lower():
            logger.warning("⚠️  We may have been redirected to a different page!")
            
            # Look for any forms
            forms = driver.find_elements(By.CSS_SELECTOR, "form")
            logger.info(f"Found {len(forms)} forms on the page")
            
            for i, form in enumerate(forms):
                try:
                    form_action = form.get_attribute("action")
                    form_method = form.get_attribute("method")
                    form_id = form.get_attribute("id")
                    form_class = form.get_attribute("class")
                    
                    logger.info(f"  Form {i+1}: action={form_action}, method={form_method}, id={form_id}, class={form_class}")
                    
                    # Look for inputs in this form
                    inputs = form.find_elements(By.CSS_SELECTOR, "input")
                    logger.info(f"    Form {i+1} has {len(inputs)} input elements")
                    
                except Exception as e:
                    logger.warning(f"  Error examining form {i+1}: {e}")
        
        logger.info("✅ Structure examination complete!")
        
    except Exception as e:
        logger.error(f"Error examining MERX structure: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    asyncio.run(examine_merx_structure()) 