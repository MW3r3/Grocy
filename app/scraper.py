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
import requests
from bs4 import BeautifulSoup
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from app.models import db, Item
from datetime import datetime

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

def parse_maxima_sales():
    """
    Parses sales data from maxima.lv and inserts it into the database.
    """
    url = "https://www.maxima.lv/ajax/salesloadmore?sort_by=newest&limit=150&search="
    response = requests.get(url)
    if response.status_code != 200:
        logger.error("Failed to fetch data from %s", url)
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    items = soup.find_all('div', class_='item')

    for item in items:
        
        if 'offer-2-l-pd-sku-lidz' in item.get('class', []):
            continue

        if item.find('div', class_='discount percents'):
            continue

        title = item.find('div', class_='title').text.strip()

        price_element = item.find('div', class_='t1')
        if price_element:
            value = price_element.find('span', class_='value').text.strip()
            cents = price_element.find('span', class_='cents').text.strip()
            price = float(f"{value}.{cents}")
        else:
            price = 0.0
        
        old_price_element = item.find('div', class_='t2')
        if old_price_element:
            old_price_text = old_price_element.find('span', class_='value').text.strip()
            old_price = float(old_price_text.replace(',', '.'))
            discount = round((old_price - price) / old_price * 100)
        else:
            discount = 0.0

        dates_interval = item.get('data-dates-interval')
        if dates_interval:
            end_date_str = dates_interval.split(' - ')[1].strip('.')
            valid_to = datetime.strptime(end_date_str, '%d.%m.%Y')
        else:
            valid_to = None

        new_item = Item(
            name=title,
            price=price,
            discount=discount,
            vendor='Maxima',
            deadline=valid_to
        )
        db.session.add(new_item)

    db.session.commit()

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        parse_maxima_sales()
