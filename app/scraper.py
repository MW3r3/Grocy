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
    url = "https://www.maxima.lv/ajax/salesloadmore?sort_by=newest&limit=2000&search="
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

        product_id = item.get('data-product-id')
        
        # Check if the item already exists in the database (vendor specific)
        existing_item = Item.query.filter_by(product_id=product_id, vendor='Maxima').first()
        if existing_item:
            logger.info("Item with product_id %s already exists for Maxima, skipping.", product_id)
            continue

        title = item.find('div', class_='title').text.strip()

        # Extract unit and quantity from the title
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

        price_element = item.find('div', class_='t1')
        if price_element:
            value = price_element.find('span', class_='value').text.strip()
            cents = price_element.find('span', class_='cents').text.strip()
            price = float(f"{value}.{cents}")
        else:
            price = 0.0


        discount = 0.0
        try:
            details_inner = item.find('div', class_='card__details').find('div', class_='card__details-inner')
            discount_div = details_inner.find('div', class_='-has-discount')
            container = discount_div.find('div', class_='old-price-tag') or discount_div.find('div', class_='card__old-price')
            span = container.find('span')
            old_price = float(span.text.replace('€', '').replace(',', '.'))
            discount = round((old_price - price) / old_price * 100)
        except (AttributeError, ValueError):
            discount = 0.0

        # New extraction of unit price to update unit and quantity
        p_price_per = item.find('p', class_='card__price-per')
        if p_price_per:
            text = p_price_per.get_text(separator=" ", strip=True)
            # Expected examples: "0,99 €/gab.", "1,99 €/kg" or "1,50 €/l"
            unit_price_match = re.search(r'([\d,]+)\s*€\s*/\s*([^\s]+)', text)
            if unit_price_match:
                try:
                    unit_price = float(unit_price_match.group(1).replace(',', '.'))
                    extracted_unit = unit_price_match.group(2).lower()
                    if unit_price > 0:
                        calc_qty = price / unit_price
                        if extracted_unit == 'kg':
                            quantity = round(calc_qty * 1000, 2)
                            unit = 'g'
                        elif extracted_unit in ['l', 'lt', 'litre', 'liter']:
                            quantity = round(calc_qty * 1000, 2)
                            unit = 'ml'
                        else:
                            quantity = round(calc_qty, 2)
                            unit = extracted_unit
                except ValueError:
                    pass

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
            category=category,
            product_id=product_id
        )
        db.session.add(new_item)

    db.session.commit()
    
def parse_rimi_sales():
    """
    Parses sales data from rimi.lv and inserts it into the database.
    """
    import json
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    with open('app/links.txt', 'r') as file:
        links = file.readlines()

    for line in links:
        if '=' not in line:
            logger.error("Invalid line in links.txt (missing '=' sign): %s", line)
            continue
        category, base_url = line.strip().split('=', 1)
        currentPage = 1
        while True:
            parsed = urlparse(base_url)
            q = parse_qs(parsed.query)
            q["currentPage"] = [str(currentPage)]
            new_query = urlencode(q, doseq=True)
            page_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                                   parsed.params, new_query, parsed.fragment))
            try:
                response = requests.get(page_url, timeout=10)
                response.raise_for_status()
            except requests.exceptions.Timeout:
                logger.error("Request to %s timed out", page_url)
                break
            except requests.exceptions.RequestException as e:
                logger.error("Request to %s failed: %s", page_url, e)
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            grid = soup.find('ul', class_='product-grid')
            li_items = grid.find_all('li', class_='product-grid__item') if grid else []
            logger.info("Found %d products on %s", len(li_items), page_url)

            for li in li_items:
                # New parsing logic using the provided HTML structure
                product_div = li.find('div', attrs={'data-product-code': True})
                if not product_div:
                    continue

                product_id = product_div.get('data-product-code') or product_div.get('data-gtms-product-id')
                if Item.query.filter_by(product_id=product_id, vendor='Rimi').first():
                    logger.info("Item with product_id %s already exists for Rimi, skipping.", product_id)
                    continue

                title = product_div.get("data-gtms-banner-title")
                if not title:
                    name_elem = li.find('p', class_='card__name')
                    title = name_elem.get_text(strip=True) if name_elem else "Unknown"

                # Price extraction from the price tag element
                price_div = li.find('div', class_='price-tag')
                if price_div:
                    int_part = price_div.find('span').get_text(strip=True)
                    details_div = price_div.find('div')
                    frac_part = details_div.find('sup').get_text(strip=True) if details_div and details_div.find('sup') else "0"
                    try:
                        price = float(f"{int_part}.{frac_part}")
                    except ValueError:
                        price = 0.0
                    sub_tag = details_div.find('sub') if details_div else None
                    unit_from_price = sub_tag.get_text(strip=True).replace("€", "").replace("/", "").strip() if sub_tag else None
                else:
                    price = 0.0
                    unit_from_price = None

                # Old price extraction for discount calculation
                old_price_elem = li.find('div', class_='old-price-tag')
                if old_price_elem:
                    old_span = old_price_elem.find('span')
                    if old_span:
                        try:
                            old_price = float(old_span.get_text(strip=True).replace("€", "").replace(",", "."))
                        except ValueError:
                            old_price = None
                    else:
                        old_price = None
                else:
                    old_price = None
                discount = round((old_price - price) / old_price * 100) if old_price and old_price > price else 0.0

                # Quantity extraction from the counter form
                form_counter = li.find('form', class_='counter')
                quantity = None
                unit_from_counter = None
                if form_counter:
                    hidden_input = form_counter.find('input', {'name': 'amount'})
                    if hidden_input and hidden_input.has_attr('data-amount'):
                        try:
                            quantity = float(hidden_input['data-amount'])
                        except ValueError:
                            quantity = None
                        unit_from_counter = hidden_input.get('data-unit')
                    else:
                        counter_span = form_counter.find('span', class_='counter__number')
                        if counter_span:
                            m = re.match(r'([\d.]+)\s*(\D+)', counter_span.get_text(strip=True))
                            if m:
                                try:
                                    quantity = float(m.group(1))
                                except ValueError:
                                    quantity = None
                                unit_from_counter = m.group(2).strip()
                final_unit = unit_from_counter if unit_from_counter else unit_from_price

                new_item = Item(
                    name=title,
                    price=price,
                    quantity=quantity,
                    unit=final_unit,
                    discount=discount,
                    vendor='Rimi',
                    deadline=None,
                    category=category,
                    product_id=product_id
                )
                db.session.add(new_item)

            db.session.commit()
            if len(li_items) < 100:
                break
            currentPage += 1

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        parse_maxima_sales()
        parse_rimi_sales()