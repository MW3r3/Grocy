import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_pdfs_from_lidl(download_dir: str):
    """
    Downloads PDF files from lidl.lv using Selenium.
    
    Args:
        download_dir (str): Directory where the PDFs will be saved.
    """
    url = "https://www.lidl.lv/"
    try:
        chrome_options = Options()
        # Remove the headless argument to run with a visible browser window
        # chrome_options.add_argument("--headless")
        prefs = {
            "download.default_directory": download_dir,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Accept cookies if the button is present
        try:
            accept_cookies_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'PIEKRIST')]"))
            )
            accept_cookies_button.click()
        except TimeoutException:
            logger.info("No cookies acceptance button found.")
        
        try:
            flyer_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//li[@data-ga-action='Flyer']//a"))
            )
            flyer_button.click()
        except TimeoutException as e:
            logger.error(f"Flyer button not found on {url}: {e}")
            return
        
        # Find the section containing the <h2> tag with the text "Akciju bukleti"
        try:
            section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h2[text()='Akciju bukleti']/ancestor::section"))
            )
        except TimeoutException as e:
            logger.error(f"Section with <h2> 'Akciju bukleti' not found on {url}: {e}")
            return
        
        # Find links within the section
        links = section.find_elements(By.XPATH, ".//a[contains(@href, 'akciju-buklets')]")
        if not links:
            logger.warning(f"No links found in the 'Akciju bukleti' section on {url}")
        
        for link in links:
            flyer_url = link.get_attribute("href")
            try:
                # Open the link in a new tab
                driver.execute_script("window.open(arguments[0], '_blank');", flyer_url)
                driver.switch_to.window(driver.window_handles[-1])
                
                # Click the button to open the sidebar
                try:
                    sidebar_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Izvēlne"]'))
                    )
                    sidebar_button.click()
                    
                    # Click the download link within the sidebar
                    try:
                        download_link = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[.//span[contains(@class, 'button__label') and contains(text(), 'Lejupielādēt PDF')]]"))
                        )
                        download_link.click()
                        
                    except TimeoutException as e:
                        logger.error(f"Download link not found in the sidebar on {flyer_url}: {e}")
                except TimeoutException as e:
                    logger.error(f"Sidebar button not found on {flyer_url}: {e}")
                
                # Close the current tab and switch back to the main tab
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except WebDriverException as e:
                logger.error(f"Error accessing flyer link from {flyer_url}: {e}")
    except WebDriverException as e:
        logger.error(f"Error accessing {url}: {e}")
    finally:
        time.sleep(10)
        driver.quit()

def download_pdfs_from_maxima(download_dir: str):
    """
    Downloads PDF files from maxima.lv using Selenium.
    
    Args:
        download_dir (str): Directory where the PDFs will be saved.
    """
    url = "https://www.maxima.lv/"
    try:
        chrome_options = Options()
        # Remove the headless argument to run with a visible browser window
        # chrome_options.add_argument("--headless")
        prefs = {
            "download.default_directory": download_dir,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Accept cookies if the button is present
        try:
            accept_cookies_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'PIEKRĪTU')]"))
            )
            accept_cookies_button.click()
        except TimeoutException:
            logger.info("No cookies acceptance button found.")
        
        # Example: Find PDF links on the Maxima website
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
        if not pdf_links:
            logger.warning(f"No PDF links found on {url}")
        
        for link in pdf_links:
            pdf_url = link.get_attribute("href")
            try:
                driver.get(pdf_url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//body"))
                )
                # Wait for 10 seconds before closing the driver
                time.sleep(10)
            except WebDriverException as e:
                logger.error(f"Error downloading PDF from {pdf_url}: {e}")
    except WebDriverException as e:
        logger.error(f"Error accessing {url}: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)

    # Download PDFs from Lidl and Maxima
    download_pdfs_from_lidl(download_dir)
    download_pdfs_from_maxima(download_dir)