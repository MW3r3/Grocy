"""
Module for scraping discount booklets from grocery stores.
"""

import os
import time
import re
from datetime import datetime
import sqlite3
import logging
import requests
from bs4 import BeautifulSoup
from flask_sqlalchemy import SQLAlchemy
from app.models import db, Item

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_maxima_sales():
    """
    Parses sales data from maxima.lv and inserts it into the database.
    """
    url = "https://www.maxima.lv/ajax/salesloadmore?sort_by=newest&limit=150&search="
    try:
        response = requests.get(url, timeout=10)  # Add timeout parameter
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.Timeout:
        logger.error("Request to %s timed out", url)
        return
    except requests.exceptions.RequestException as e:
        logger.error("Request to %s failed: %s", url, e)
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    items = soup.find_all('div', class_='item')

    for item in items:
        # Ignore items with the class 'offer-2-l-pd-sku-lidz'
        if 'offer-2-l-pd-sku-lidz' in item.get('class', []):
            continue

        # Ignore items that contain a div with the class 'discount percents'
        if item.find('div', class_='discount percents'):
            continue

        title = item.find('div', class_='title').text.strip()

        # Extract unit and quantity from the title
        quantity = None
        unit = None
        match = re.search(r'(\d+)\s*(g|kg|ml|l|pcs)', title, re.IGNORECASE)
        if match:
            quantity = int(match.group(1))
            unit = match.group(2).lower()

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

        # Extract deadline from data-dates-interval attribute
        dates_interval = item.get('data-dates-interval')
        if dates_interval:
            end_date_str = dates_interval.split(' - ')[1].strip('.')
            valid_to = datetime.strptime(end_date_str, '%d.%m.%Y')
        else:
            valid_to = None

        # TODO: Implement categorization based on title or other criteria
        category = None

        new_item = Item(
            name=title,
            price=price,
            quantity=quantity,
            unit=unit,
            discount=discount,
            vendor='Maxima',
            deadline=valid_to,
            category=category
        )
        db.session.add(new_item)

    db.session.commit()

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        parse_maxima_sales()
