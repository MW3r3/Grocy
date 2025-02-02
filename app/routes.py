"""
Routes module for the Flask application.
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for
from .models import db, Item
from .scraper import download_pdfs_from_lidl, download_pdfs_from_maxima

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
    quantity = request.form["quantity"]
    discount = request.form["discount"]
    vendor = request.form["vendor"]
    category = request.form["category"]
    unit = request.form["unit"]
    item = Item(name=name, price=price, quantity=quantity, discount=discount, vendor=vendor, category=category, unit=unit)
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

@main.route("/upload", methods=["GET", "POST"])
def upload():
    """
    Route for uploading PDFs.
    """
    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = os.path.join("uploads", file.filename)
            file.save(file_path)
            # Placeholder for processing the uploaded PDF
            # process_pdf(file_path)
            return redirect(url_for("main.index"))
    return render_template("upload.html")

@main.route("/scrape")
def scrape():
    """
    Route for scraping PDFs.
    """
    download_pdfs_from_lidl("downloads")
    download_pdfs_from_maxima("downloads")
    return redirect(url_for("main.index"))
