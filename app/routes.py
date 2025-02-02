"""
Routes module for the Flask application.
"""

from flask import Blueprint, render_template, request, redirect, url_for
from .models import db, Item
from .scraper import parse_maxima_sales

main = Blueprint("main", __name__)

@main.route("/")
def index():
    """
    Route for the index page.
    """
    items = Item.query.all()
    total_items = Item.query.count()
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
