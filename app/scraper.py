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
import base64

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

def scrape_img(element, store=""):
    """
    Helper function to extract the src URL from an <img> element within the given element.
    Returns the URL if found, otherwise None.
    """
    if not element:
        logger.warning("No element provided for image scraping")
        return None
    img_element = element.find('div', class_='img')
    if not img_element:
        logger.warning("No 'div.img' found in the element: %s", element)
        return None
    img = img_element.find('img')
    img_url_relative = img['src'] if img and img.has_attr('src') else None
    if not img_url_relative:
        logger.warning("No 'src' attribute found for image in element: %s", element)
        return None
    
    if ".png" in img_url_relative:
        img_url_relative = img_url_relative.split(".png")[0] + ".png"
        logger.info("Truncated image URL to: %s", img_url_relative)
    else:
        logger.warning("'.png' not found in image URL: %s", img_url_relative)
    if store == "Rimi":
        return img_url_relative
    elif store == "Maxima":
        full_url = f"https://www.maxima.lv{img_url_relative}"
        logger.info("Full image URL for Maxima (truncated): %s", full_url)
        return full_url
    return img_url_relative

def upload_image_to_imgbb(image_data, api_key=None, name=""):
    """
    Uploads the image to imgbb with an expiration of 600 seconds.
    If image_data is a URL (string starting with http), passes it directly.
    Otherwise, assumes image_data is raw bytes and encodes it.
    Returns the image URL on success, otherwise None.
    """
    if not api_key:
        api_key = os.environ.get("IMGBB_API_KEY")
    if not api_key:
        raise ValueError("IMGBB_API_KEY not found in environment variables")
    
    endpoint = f"https://api.imgbb.com/1/upload?expiration=604800&key={api_key}"
    
    # If image_data is a URL, pass it directly without downloading
    if isinstance(image_data, str) and image_data.startswith("http"):
        payload = {
            "name": name,
            "image": image_data
        }
        logger.info("Uploading image via URL: %s", image_data)
    else:
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        payload = {
            "name": name,
            "image": encoded_image
        }
        logger.info("Uploading image as base64-encoded data")
    
    response = requests.post(endpoint, data=payload)
    if response.status_code == 200:
        result = response.json()
        uploaded_url = result['data'].get('url')
        logger.info("Image uploaded successfully: %s", uploaded_url)
        return uploaded_url
    else:
        logger.error("Failed to upload image '%s'. Status: %s; Response: %s",
                     name, response.status_code, response.text)
    return None

def parse_maxima_sales():
    store = "Maxima"
    """
    Parses sales data from maxima.lv and inserts it into the database.
    """
    url = "https://www.maxima.lv/ajax/salesloadmore?sort_by=newest&limit=2000&search="
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.error("Request to %s timed out", url)
        return
    except requests.exceptions.RequestException as e:
        logger.error("Request to %s failed: %s", url, e)
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    items = soup.find_all('div', class_='item')

    for item in items:
        classes = item.get('class', [])
        if 'offer-2-l-pd-sku-lidz' in classes or item.find('div', class_='discount percents'):
            continue

        product_id = item.get('data-product-id')
        existing_item = Item.collection().find_one({"product_id": product_id, "store": store})

        # Extract Image URL and upload to imgbb
        name=product_id+"@"+store
        img = scrape_img(item, store)
        img_url = upload_image_to_imgbb(img, name=name) if img else None

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
            "image_url": img_url,
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
                    round(price / (quantity/1000), 2) if quantity and quantity != 0 and unit in ['g', 'ml']
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
        #logger.info("Parsed MAXIMA item: product_id=%s, title=%s, price=%s, quantity=%s, discount=%s, unit=%s",
        #            product_id, title, price, quantity, discount, unit)
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
            store = "Rimi"
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

                    name = product_id + "@" + store
                    # Threading for image upload
                    img = scrape_img(product_div, store)
                    if img:
                        result_container = {}
                        thread = threading.Thread(
                            target=lambda: result_container.update({"result": upload_image_to_imgbb(img, name=name)})
                        )
                        thread.start()
                        thread.join()
                        img_url = result_container.get("result", "")
                    else:
                        img_url = ""
                    
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
                    
                    # Title filtering for search_name: split title at commas and any digit
                    import re
                    search_name = re.split(r'[,0-9]', title)[0].strip().lower()
                
                    now = datetime.utcnow()
                    new_item = {
                        "name": title,
                        "product_id": product_id,
                        "description": "",
                        "search_name": search_name,
                        "image_url": img_url,
                        "store": store,
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
                                round(price / (quantity/1000), 2) if quantity and quantity != 0 and unit in ['g', 'ml']
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

def load_category_keywords():
    """Load category keywords from file."""
    keywords = {}
    try:
        with open('app/category_keywords.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    category, words = line.strip().split('=')
                    keywords[category] = [word.strip().lower() for word in words.split(',')]
    except FileNotFoundError:
        logger.error("Category keywords file not found")
        return {}
    return keywords

def categorize_maxima_items():
    """
    Adds category information to all Maxima items using both keyword matching
    and similar Rimi items.
    """
    logger.info("Starting to categorize Maxima items...")
    
    # Load category keywords
    category_keywords = load_category_keywords()
    
    # Fetch all Maxima items
    maxima_items = Item.collection().find({"store": "MAXIMA"})
    
    for item in maxima_items:
        # First try keyword matching
        item_name = item["name"].lower()
        matched_category = None
        
        for category, keywords in category_keywords.items():
            if any(keyword in item_name for keyword in keywords):
                matched_category = category
                break
        
        if matched_category:
            if item.get("category") != matched_category:
                Item.update(item["_id"], {"category": matched_category})
                logger.info(f"Categorized '{item['name']}' as '{matched_category}' using keywords")
            continue
        
        # If no keyword match, try finding similar Rimi items
        pipeline = [
            {
                "$search": {
                    "index": "search_name",
                    "text": {
                        "query": item["search_name"],
                        "path": "search_name",
                        "fuzzy": {}
                    }
                }
            },
            {
                "$match": {
                    "store": "Rimi",
                    "category": {"$ne": None}
                }
            },
            {
                "$limit": 10
            }
        ]
        
        similar_items = list(Item.collection().aggregate(pipeline))
        
        if similar_items:
            category_counts = {}
            for similar_item in similar_items:
                category = similar_item.get("category")
                if category:
                    category_counts[category] = category_counts.get(category, 0) + 1
            
            if category_counts:
                best_category = max(category_counts.items(), key=lambda x: x[1])[0]
                if item.get("category") != best_category:
                    Item.update(item["_id"], {"category": best_category})
                    logger.info(f"Categorized '{item['name']}' as '{best_category}' using similar items "
                              f"(Found in {category_counts[best_category]} of {len(similar_items)} similar items)")
    
    logger.info("Finished categorizing Maxima items.")

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        parse_maxima_sales()
        parse_rimi_sales()