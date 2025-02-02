"""
Routes module for the Flask application.
"""

from flask import Blueprint, render_template, request, redirect, url_for
from .models import db, Item
from .scraper import parse_maxima_sales
from sqlalchemy import func  # Add this import
from app.init_db import setup_fts  # Add this import

main = Blueprint("main", __name__)

@main.route("/")
def index():
    """
    Route for the index page.
    """
    items = Item.query.all()
    total_items = db.session.query(func.max(Item.id)).scalar() or 0  # Use max id as count
    return render_template("index.html", items=items, total_items=total_items)

@main.route("/add", methods=["POST"])
def add():
    """
    Route for adding an item.
    """
    name = request.form["name"]
    price = request.form["price"]
    quantity = request.form["quantity"]
    discount = request.form["discount"]
    vendor = request.form["vendor"]
    category = request.form["category"]
    unit = request.form["unit"]
    item = Item(name=name, price=price, quantity=quantity,
                discount=discount,vendor=vendor, category=category, unit=unit)
    db.session.add(item)
    db.session.commit()
    return redirect(url_for("main.index"))

@main.route("/delete/<int:item_id>")
def delete(item_id):
    """
    Route for deleting an item.
    """
    item = Item.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("main.index"))

@main.route("/scrape")
def scrape():
    """
    Route for scraping sales data from Maxima.
    """
    parse_maxima_sales()
    return redirect(url_for("main.index"))

# New route for scraping Rimi sales with explicit endpoint
@main.route("/scrape_rimi", endpoint="scrape_rimi")
def scrape_rimi():
    """
    Route for scraping sales data from Rimi.
    """
    from app.scraper import parse_rimi_sales  # import here if needed
    parse_rimi_sales()
    return redirect(url_for("main.index"))

@main.route("/search")
def search():
    """
    Route for fuzzy searching items.
    """
    query = request.args.get("query", "")
    if query:
        items = Item.fuzzy_search_by_name(query)
    else:
        items = []
    return render_template("search_results_partial.html", items=items)

@main.route('/initdb', methods=['GET'])
def init_db_route():
    db.create_all()  # Ensure all tables including 'items' exist
    setup_fts()
    return redirect(url_for('main.init_db_status'))  # Prefixed with blueprint 'main'

@main.route('/initdb/status', methods=['GET'])
def init_db_status():
    return render_template('init_db_status.html', message="FTS table and triggers created.")

@main.route("/fts")
def fts_search():
    """
    Route for full-text searching items via SQLite FTS5.
    """
    query = request.args.get("query", "")
    if query:
        items = Item.fts_search_by_name(query)
    else:
        items = []
    return render_template("search_results_partial.html", items=items)

@main.route("/combined_search")
def combined_search():
    query = request.args.get("query", "")
    if query:
        items = Item.combined_search_by_name_precise(query)
    else:
        items = []
    return render_template("search_results_partial.html", items=items)
