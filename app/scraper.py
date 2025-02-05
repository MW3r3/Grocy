"""
Module for scraping item prices from grocery stores.
"""

import os
import time
import re
from datetime import datetime
import logging
import requests
from bs4 import BeautifulSoup
from app.models import Item

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_maxima_sales():
    store = "MAXIMA"
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
        # Cache frequently used element lookups
        classes = item.get('class', [])
        if 'offer-2-l-pd-sku-lidz' in classes or item.find('div', class_='discount percents'):
            continue

        product_id = item.get('data-product-id')
        existing_item = Item.collection().find_one({"product_id": product_id, "store": store})

        # Cache title extraction
        title_elem = item.find('div', class_='title')
        if not title_elem:
            continue
        title = title_elem.text.strip()
        
        search_name = re.sub(r'\b[A-Z]{2,}\b', '', title.split(',')[0]).strip().lower()
        match = re.search(r'\b(?:[A-Z]{2,}(?:\s+[A-Z]{2,})+)\b', title)
        if match:
            brand = match.group().strip()
        else:
            match = re.search(r'\b[A-Z]{2,}\b', title)
            brand = match.group().strip() if match else store

        price_element = item.find('div', class_='t1')
        if price_element:
            value = price_element.find('span', class_='value').text.strip()
            cents = price_element.find('span', class_='cents').text.strip()
            price = float(f"{value}.{cents}")
        else:
            price = 0.0
            
        old_price_element = item.find('div', class_='t2')
        if old_price_element:
            old_value = old_price_element.find('span', class_='value').text.strip()
            old_price = float(old_value.replace(',', '.'))
            
        if old_price:
            discount = round((old_price - price) / old_price * 100)
        
        try:
            unit_price_text = item.find('div', class_='t1 with_unit_price').find('span', class_='unit-price').text.strip()
            unit = unit_price_text.split('/')[-1].strip()
            unit_price = unit_price_text.split('')[0].strip()
            quantity = round(price / unit_price, 2)
            if unit == 'kg':
                quantity *= 1000
                unit = 'g'
            elif unit == 'l':
                quantity *= 1000
                unit = 'ml'
        except:
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

        # Extract deadline from data-dates-interval attribute
        dates_interval = item.get('data-dates-interval')
        if dates_interval:
            end_date_str = dates_interval.split(' - ')[1].strip('.')
            valid_to = datetime.strptime(end_date_str, '%d.%m.%Y')
        else:
            valid_to = None

        # TODO: Implement categorization based on title or other criteria
        category = None

        # Build document based on dbschema.json structure
        now = datetime.utcnow()
        new_item = {
            "name": title,
            "product_id": product_id,
            "description": "",
            "search_name": search_name,
            "image_url": "",
            "store": store,
            "category": category,
            "stock": True,
            "unit": unit,
            "quantity": quantity,
            "brand": brand,
            "price": {
                "value": price,
                "old_value": old_price if old_price is not None else price,
                "discount": discount,
                "currency": "EUR",
                "price_per_unit": (
                    round(price * 1000 / quantity, 2) if quantity and quantity != 0 and unit in ['g', 'ml']
                    else (round(price / quantity, 2) if quantity and quantity != 0 else 0)
                )
            },
            "time": {
                "created": now,
                "updated": now,
                "discount_deadline": valid_to
            }
        }
        if existing_item:
            new_item["time"]["created"] = existing_item["time"]["created"]
            def build_diff(new_doc, existing_doc):
                diff = {}
                for key, value in new_doc.items():
                    if key == "time":
                        existing_time = existing_doc.get("time", {})
                        time_diff = {}
                        for subkey, subvalue in value.items():
                            if subkey == "updated":
                                continue
                            if existing_time.get(subkey) != subvalue:
                                time_diff[subkey] = subvalue
                        if time_diff:
                            time_diff["updated"] = value["updated"]
                            diff["time"] = time_diff
                    else:
                        if existing_doc.get(key) != value:
                            diff[key] = value
                return diff

            diff = build_diff(new_item, existing_item)
            if diff:
                Item.update(existing_item["_id"], diff)
                logger.info("Updated existing item with product_id %s", product_id)
            else:
                logger.info("No changes for product_id %s, skipping update", product_id)
        else:
            Item.create(new_item)

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
                existing_item = Item.collection().find_one({"product_id": product_id, "store": "Rimi"})

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

                now = datetime.utcnow()
                new_item = {
                    "name": title,
                    "product_id": product_id,
                    "description": "",
                    "search_name": title.lower(),
                    "image_url": "",
                    "store": "Rimi",
                    "category": category,
                    "stock": 0,
                    "unit": final_unit,
                    "quantity": quantity,
                    "price": {
                        "value": price,
                        "old_value": old_price if old_price is not None else price,
                        "discount": discount,
                        "currency": "EUR",
                        "price_per_unit": (
                            round(price * 1000 / quantity, 2) if quantity and quantity != 0 and final_unit in ['g', 'ml']
                            else (round(price / quantity, 2) if quantity and quantity != 0 else 0)
                        )
                    },
                    "time": {
                        "created": now,
                        "updated": now,
                        "discount_deadline": None
                    }
                }
                if existing_item:
                    new_item["time"]["created"] = existing_item["time"]["created"]
                    diff = build_diff(new_item, existing_item)
                    if diff:
                        Item.update(existing_item["_id"], diff)
                        logger.info("Updated existing item with product_id %s", product_id)
                    else:
                        logger.info("No changes for product_id %s, skipping update", product_id)
                else:
                    Item.create(new_item)

            if len(li_items) < 100:
                break
            currentPage += 1

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        parse_maxima_sales()
        parse_rimi_sales()