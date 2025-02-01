"""
Routes module for the Flask application.
"""

from flask import Blueprint, render_template, request, redirect, url_for
from .models import db, Item
from .scraper import download_pdfs_from_lidl

main = Blueprint("main", __name__)

@main.route("/")
def index():
    """
    Route for the index page.
    """
    items = Item.query.all()
    return render_template("index.html", items=items)

@main.route("/add", methods=["POST"])
def add():
    """
    Route for adding an item.
    """
    name = request.form["name"]
    price = request.form["price"]
    discount = request.form["discount"]
    store = request.form["store"]
    category = request.form["category"]
    item = Item(name=name, price=price, discount=discount, vendor=store, category=category)
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
    Route for scraping PDFs.
    """
    download_pdfs_from_lidl("downloads")
    return redirect(url_for("main.index"))
