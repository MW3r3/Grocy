"""
Routes module for the Flask application.
"""

from flask import Blueprint, copy_current_request_context, redirect, render_template, request, current_app, url_for
from datetime import datetime
from .models import Item
from threading import Thread
from flask import copy_current_request_context

# Helper to run tasks in background threads with request context
def run_in_background(task, *args, **kwargs):
    @copy_current_request_context
    def wrapper():
        task(*args, **kwargs)
    Thread(target=wrapper).start()

main = Blueprint("main", __name__)

@main.route("/")
def index():
    """
    Route for the index page.
    """
    items = Item.get_all()
    total_items = Item.collection().count_documents({})
    
    # Read categories from links.txt
    categories = []
    try:
        with open('app/links.txt', 'r') as f:
            for line in f:
                if '=' in line:
                    category = line.split('=')[0].strip()
                    categories.append(category)
    except FileNotFoundError:
        current_app.logger.error("links.txt file not found")
        categories = []

    # Get distinct stores from items
    stores = Item.collection().distinct("store")

    return render_template("index.html", 
                         items=items, 
                         total_items=total_items, 
                         categories=sorted(categories),
                         stores=sorted(stores),
                         current_year=datetime.utcnow().year)

@main.route("/add", methods=["POST"])
def add():
    """
    Route for adding an item.
    """
    now = datetime.utcnow()
    name = request.form["name"]
    price = float(request.form["price"])
    quantity = float(request.form["quantity"])
    discount = float(request.form["discount"])
    vendor = request.form["vendor"]
    category = request.form["category"]
    unit = request.form["unit"]
    data = {
        "name": name,
        "product_id": "",
        "description": "",
        "search_name": name.lower(),
        "image_url": "",
        "store": vendor,
        "category": category,
        "stock": 0,
        "unit": unit,
        "price": {
            "value": price,
            "old_value": price,
            "discount": discount,
            "currency": "EUR",
            "price_per_unit": round(price / quantity, 2) if quantity != 0 else 0
        },
        "time": {
            "created": now,
            "updated": now,
            "discount_deadline": None
        }
    }
    Item.create(data)
    return redirect(url_for("main.index"))

@main.route("/delete/<item_id>")
def delete(item_id):
    """
    Route for deleting an item.
    """
    Item.delete(item_id)
    return redirect(url_for("main.index"))

@main.route("/delete_all", methods=["POST"])
def delete_all():
    """
    Route for deleting all items in the database.
    """
    from .models import Item
    Item.collection().delete_many({})
    return redirect(url_for("main.index"))

@main.route("/scrape")
def scrape():
    """
    Route for scraping sales data from Maxima.
    """
    from .scraper import parse_maxima_sales
    run_in_background(parse_maxima_sales)
    return redirect(url_for("main.index"))

@main.route("/scrape_rimi", endpoint="scrape_rimi")
def scrape_rimi():
    """
    Route for scraping sales data from Rimi.
    """
    from .scraper import parse_rimi_sales
    run_in_background(parse_rimi_sales)
    return redirect(url_for("main.index"))

@main.route("/categorize_maxima")
def categorize_maxima():
    """
    Route for categorizing Maxima items based on Rimi items.
    """
    from .scraper import categorize_maxima_items
    run_in_background(categorize_maxima_items)
    return redirect(url_for("main.index"))

@main.route("/search")
def search():
    """
    Route for fuzzy searching items with filters.
    """
    query = request.args.get("query", "")
    lang = request.args.get("lang", "english").lower()
    if query and lang == "english":
        try:
            import os
            from google.cloud import translate_v2 as translate

            # Set up translation client
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/melihbulut/Grocy/keys/grocy-416211-959710a9980e.json'
            translate_client = translate.Client()

            # Translate the query
            translation = translate_client.translate(
                query,
                target_language="lv",
            )
            query = translation["translatedText"]
        except Exception as e:
            current_app.logger.error(f"Translation failed: {e}")
            # Optionally, set a flag or message to inform the user
            translation_failed = True

    if query:
        filters = {
            'category': request.args.get('category'),
            'stock': request.args.get('stock') == 'true',
        }
        # Add quantity filters if provided
        min_qty = request.args.get('min_quantity')
        max_qty = request.args.get('max_quantity')
        if min_qty and min_qty.isdigit():
            filters['min_quantity'] = float(min_qty)
        if max_qty and max_qty.isdigit():
            filters['max_quantity'] = float(max_qty)
        # Remove empty filters
        filters = {k: v for k, v in filters.items() if v is not None and v != ''}
        items = Item.search_by_name(query, filters)
    else:
        items = []
    return render_template("search_results_partial.html", items=items)

@main.route("/remove_duplicates")
def remove_duplicates():
    """
    Route for removing duplicate items.
    """
    def run_cleanup():
        # Get all items grouped by product_id and store
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "product_id": "$product_id",
                        "store": "$store"
                    },
                    "items": {"$push": "$$ROOT"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1}
                }
            }
        ]
        
        duplicates = Item.collection().aggregate(pipeline)
        removed_count = 0
        
        for group in duplicates:
            # Sort by update time and keep the most recent
            items = sorted(group["items"], key=lambda x: x["time"]["updated"], reverse=True)
            # Keep the first (most recent) item and remove others
            for item in items[1:]:
                Item.delete(item["_id"])
                removed_count += 1
        
        app = current_app._get_current_object() 
        app.logger.info(f"Removed {removed_count} duplicate items")
    run_in_background(run_cleanup)
    return redirect(url_for("main.index"))
