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
import re

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

def parse_maxima_sales():
    """
    Parses sales data from maxima.lv and inserts it into the database.
    """
    url = "https://www.maxima.lv/ajax/salesloadmore?sort_by=newest&limit=10000&search="
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

        quantity = None
        unit = None
        match = re.search(r'(\d+)\s*(gab.|kg|ml|l|g)', title, re.IGNORECASE)
        if match:
            quantity = int(match.group(1))
            unit = match.group(2).lower()
            if unit == 'kg':
                quantity *= 1000
                unit = 'g'
            elif unit == 'l':
                quantity *= 1000
                unit = 'ml'
            title = re.sub(r'(\d+\s*(gab.|kg|ml|l|g))(.*)', '', title).replace(',', '').strip()

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

        product_id = item.get('data-product-id')

        existing_item = Item.query.filter_by(product_id=product_id).first()
        if existing_item:
            existing_item.price = price
            existing_item.discount = discount
            existing_item.vendor = 'Maxima'
            existing_item.deadline = valid_to
            existing_item.quantity = quantity
            existing_item.unit = unit
        else:
            new_item = Item(
                name=title,
                price=price,
                discount=discount,
                vendor='Maxima',
                deadline=valid_to,
                quantity=quantity,
                unit=unit,
                product_id=product_id
            )
            db.session.add(new_item)

    db.session.commit()

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        parse_maxima_sales()
