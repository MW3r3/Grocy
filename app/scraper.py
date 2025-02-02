"""
Module for scraping discount booklets from grocery stores.
"""

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def configure_driver(download_dir: str):
    """
    Configures and returns a Selenium WebDriver instance.

    Args:
        download_dir (str): Directory where the PDFs will be saved.

    Returns:
        WebDriver: Configured WebDriver instance.
    """
    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    return webdriver.Chrome(options=chrome_options)

def download_pdfs_from_lidl(download_dir: str):
    """
    Downloads PDF files from lidl.lv using Selenium.

    Args:
        download_dir (str): Directory where the PDFs will be saved.
    """
    url = "https://www.lidl.lv/"
    driver = configure_driver(download_dir)

    try:
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
            logger.error("Flyer button not found on %s: %s", url, e)
            return

        # Find the section containing the <h2> tag with the text "Akciju bukleti"
        try:
            section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h2[text()='Akciju bukleti']/ancestor::section")
                    ))
        except TimeoutException as e:
            logger.error("Section with <h2> 'Akciju bukleti' not found on %s: %s", url, e)
            return

        # Find links within the section
        links = section.find_elements(By.XPATH, ".//a[contains(@href, 'akciju-buklets')]")
        if not links:
            logger.warning("No links found in the 'Akciju bukleti' section on %s", url)

        for link in links:
            flyer_url = link.get_attribute("href")
            try:
                # Open the link in a new tab
                driver.execute_script("window.open(arguments[0], '_blank');", flyer_url)
                driver.switch_to.window(driver.window_handles[-1])

                # Click the button to open the sidebar
                try:
                    sidebar_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, 'button[aria-label="Izvēlne"]')
                            ))
                    sidebar_button.click()

                    # Click the download link within the sidebar
                    try:
                        download_link = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//a[.//span[contains(@class, 'button__label') and "
                                 "contains(text(), 'Lejupielādēt PDF')]]")
                            )
                        )
                        download_link.click()
                        time.sleep(4)
                    except TimeoutException as e:
                        logger.error(
                            "Download link not found in the sidebar on %s: %s", flyer_url, e
                            )
                except TimeoutException as e:
                    logger.error("Sidebar button not found on %s: %s", flyer_url, e)

                # Close the current tab and switch back to the main tab
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except WebDriverException as e:
                logger.error("Error accessing flyer link from %s: %s", flyer_url, e)
    except WebDriverException as e:
        logger.error("Error accessing %s: %s", url, e)
    finally:
        
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
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'PIEKRĪTU')]")
                    ))
            accept_cookies_button.click()
        except TimeoutException:
            logger.info("No cookies acceptance button found.")

        # Example: Find PDF links on the Maxima website
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
        if not pdf_links:
            logger.warning("No PDF links found on %s", url)

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
                logger.error("Error downloading PDF from %s: %s", pdf_url, e)
    except WebDriverException as e:
        logger.error("Error accessing %s: %s", url, e)
    finally:
        driver.quit()

if __name__ == "__main__":
    download_directory = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_directory, exist_ok=True)

    # Download PDFs from Lidl and Maxima
    download_pdfs_from_lidl(download_directory)
    download_pdfs_from_maxima(download_directory)
