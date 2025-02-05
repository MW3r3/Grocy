"""
Routes module for the Flask application.
"""

from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime
from .models import Item

main = Blueprint("main", __name__)

@main.route("/")
def index():
    """
    Route for the index page.
    """
    items = Item.get_all()
    total_items = Item.collection().count_documents({})
    return render_template("index.html", items=items, total_items=total_items, current_year=datetime.utcnow().year)

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
        "product_id": "",  # no product_id provided via form
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
    from threading import Thread
    from flask import copy_current_request_context
    from .scraper import parse_maxima_sales

    @copy_current_request_context
    def run_scrape():
        parse_maxima_sales()

    Thread(target=run_scrape).start()
    return redirect(url_for("main.index"))

@main.route("/scrape_rimi", endpoint="scrape_rimi")
def scrape_rimi():
    """
    Route for scraping sales data from Rimi.
    """
    from threading import Thread
    from .scraper import parse_rimi_sales
    Thread(target=parse_rimi_sales).start()
    return redirect(url_for("main.index"))

@main.route("/search")
def search():
    """
    Route for fuzzy searching items.
    """
    query = request.args.get("query", "")
    if query:
        items = Item.search_by_name(query)
    else:
        items = []
    return render_template("search_results_partial.html", items=items)
