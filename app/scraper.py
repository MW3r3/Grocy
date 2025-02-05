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
import threading
from fuzzywuzzy import fuzz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

        brand_match = re.search(r'\b(?:[A-ZĀČĒĢĪĶĻŅŠŪŽ]{2,}(?:\s+[A-ZĀČĒĢĪĶĻŅŠŪŽ]{2,})+)\b', title)
        if brand_match:
            brand = brand_match.group().strip()
        else:
            brand_match = re.search(r'\b[A-ZĀČĒĢĪĶĻŅŠŪŽ]{2,}\b', title)
            brand = brand_match.group().strip() if brand_match else store

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
        else:
            discount = 0
        
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
            match = re.search(r'(\d+(?:[.,]\d+)?)\s*(gab\.|kg|ml|l|g)', title, re.IGNORECASE)
            if match:
                quantity_str = match.group(1).replace(',', '.')
                quantity = float(quantity_str)
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
        if unit == 'kg':
            new_item['quantity'] *= 1000
            new_item['unit'] = 'g'
        elif unit == 'l':
            new_item['quantity'] *= 1000
            new_item['unit'] = 'ml'
        logger.info("Parsed MAXIMA item: product_id=%s, title=%s, price=%s, quantity=%s, discount=%s, unit=%s",
                    product_id, title, price, quantity, discount, unit)
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
    Parses sales data from rimi.lv and inserts it into the database using threads.
    """
    import json
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

    proxies = {
        "http": os.environ.get("HTTP_PROXY"),
        "https": os.environ.get("HTTPS_PROXY"),
    }

    def scrape_link(category, base_url):
        """Helper function to scrape a single link."""
        from app import create_app
        app = create_app()
        with app.app_context():
            currentPage = 1
            while True:
                parsed = urlparse(base_url)
                q = parse_qs(parsed.query)
                q["currentPage"] = [str(currentPage)]
                new_query = urlencode(q, doseq=True)
                page_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                                       parsed.params, new_query, parsed.fragment))
                try:
                    response = requests.get(page_url, timeout=10, proxies=proxies)
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
                    product_div = li.find('div', attrs={'data-product-code': True})
                    if not product_div:
                        continue

                    product_id = product_div.get('data-product-code') or product_div.get('data-gtms-product-id')
                    existing_item = Item.collection().find_one({"product_id": product_id, "store": "Rimi"})

                    title = product_div.get("data-gtms-banner-title")
                    if not title:
                        name_elem = li.find('p', class_='card__name')
                        title = name_elem.get_text(strip=True) if name_elem else "Unknown"
                    
                    brand = product_div.get("brand") or "Rimi"

                    # Price extraction
                    price_card_elem = product_div.find('div', class_='card__price')
                    
                    price_euros = price_card_elem.find('span').get_text(strip=True) if price_card_elem else None
                    price_cents = price_card_elem.find('sup').get_text(strip=True) if price_card_elem else None
                    try:
                        price = float(f"{price_euros}.{price_cents}")
                    except (TypeError, ValueError):
                        price = 0.0

                    # Old price extraction for discount calculation
                    old_price_elem = product_div.find('div', class_='card__old-price')
                    if old_price_elem:
                        old_price_str = old_price_elem.find('span').get_text(strip=True)
                        try:
                            old_price = float(old_price_str.replace(',', '.').replace('€', ''))
                        except (TypeError, ValueError):
                            old_price = None
                    else:
                        old_price = None

                    discount = round((old_price - price) / old_price * 100) if old_price and old_price > price else 0
                    
                    price_per_unit_elem = product_div.find('p', class_='card__price-per') if product_div else None
             
                    price_per_unit_text = price_per_unit_elem.get_text(strip=True) if price_per_unit_elem else None
                    price_per_unit_str = price_per_unit_text.split(' ')[0].replace(',', '.') if price_per_unit_text else None
                    try:
                        price_per_unit = float(price_per_unit_str) if price_per_unit_str else None
                    except ValueError:
                        price_per_unit = None
                        
                    unit = price_per_unit_text.split('/')[-1].strip() if price_per_unit_text else None
                    if price_per_unit and unit:
                        if unit in ['kg', 'l']:
                            quantity = round(price / price_per_unit * 1000, 2)
                            unit = 'g' if unit == 'kg' else 'ml'
                        else:
                            quantity = round(price / price_per_unit, 2)
                    else:
                        quantity = None
                    stock = True if price_per_unit else False

                    now = datetime.utcnow()
                    new_item = {
                        "name": title,
                        "product_id": product_id,
                        "description": "",
                        "search_name": title.lower(),
                        "image_url": "",
                        "store": "Rimi",
                        "category": category,
                        "stock": stock,
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
                            "discount_deadline": None
                        }
                    }
                    if unit == 'kg':
                        new_item['quantity'] *= 1000
                        new_item['unit'] = 'g'
                    elif unit == 'l':
                        new_item['quantity'] *= 1000
                        new_item['unit'] = 'ml'
                    if existing_item:
                        new_item["time"]["created"] = existing_item["time"]["created"]
                        diff = build_diff(new_item, existing_item)
                        if diff:
                            Item.update(existing_item["_id"], diff)
                    else:
                        Item.create(new_item)

                if len(li_items) < 100:
                    break
                currentPage += 1

    with open('app/links.txt', 'r') as file:
        links = file.readlines()

    threads = []
    for line in links:
        if '=' not in line:
            logger.error("Invalid line in links.txt (missing '=' sign): %s", line)
            continue
        category, base_url = line.strip().split('=', 1)
        thread = threading.Thread(target=scrape_link, args=(category, base_url))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    logger.info("Finished parsing Rimi sales data using threads.")

def categorize_maxima_items():
    """
    Adds category information to Maxima items based on Rimi items using fuzzy matching.
    """
    logger.info("Starting to categorize Maxima items based on Rimi items using fuzzy matching...")
    
    # Fetch all Rimi items
    rimi_items = Item.collection().find({"store": "Rimi"})
    
    # Create a dictionary mapping Rimi item names to their categories
    rimi_category_map = {}
    for item in rimi_items:
        if item["category"]:
            # Extract core product name from Rimi item using regex
            match = re.match(r'([A-Za-z\s]+)', item["name"])  # Match only letters and spaces at the beginning
            if match:
                rimi_name = match.group(1).strip()
                rimi_category_map[rimi_name] = item["category"]
            else:
                logger.warning(f"Could not extract name from Rimi item: {item['name']}")
    
    # Fetch all Maxima items without a category
    maxima_items = Item.collection().find({"store": "MAXIMA", "category": None})
    
    # Iterate through Maxima items and update their categories based on Rimi items
    for item in maxima_items:
        best_match = None
        best_ratio = 0
        
        for rimi_name, rimi_category in rimi_category_map.items():
            ratio = fuzz.ratio(item["search_name"].lower(), rimi_name.lower())
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = rimi_category
        
        # Set a threshold for the matching ratio
        if best_match and best_ratio > 70:  # Adjust threshold as needed
            new_category = best_match
            Item.update(item["_id"], {"category": new_category})
            logger.info(f"Updated category for Maxima item {item['_id']} to {new_category} (Ratio: {best_ratio})")
            
    logger.info("Finished categorizing Maxima items based on Rimi items using fuzzy matching.")

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        parse_maxima_sales()
        parse_rimi_sales()