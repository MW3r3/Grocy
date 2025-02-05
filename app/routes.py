"""
Routes module for the Flask application.
"""

from flask import Blueprint, render_template, request, current_app
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

@main.route("/search")
def search():
    """
    Route for fuzzy searching items with filters.
    """
    query = request.args.get("query", "")
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