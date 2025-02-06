from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app.scraper import parse_maxima_sales, parse_rimi_sales, categorize_maxima_items, upload_all_images
import os
from threading import Thread
from flask import copy_current_request_context

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')

# Helper to run tasks in background threads with request context
def run_in_background(task, *args, **kwargs):
    @copy_current_request_context
    def wrapper():
        task(*args, **kwargs)
    Thread(target=wrapper).start()

@admin_bp.before_request
def require_login():
    if request.endpoint in ('admin.login', 'admin.static'):
        return
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get("password")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin")
        if password == admin_password:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.index"))
        flash("Incorrect password", "danger")
    return render_template("login.html")

@admin_bp.route('/logout', methods=['GET'])
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))

@admin_bp.route('/', methods=['GET'])
def index():
    return render_template('admin.html')

@admin_bp.route('/run_maxima', methods=['POST'])
def run_maxima():
    try:
        run_in_background(parse_maxima_sales)
        flash("Maxima sales parsing started in the background.", "success")
    except Exception as e:
        current_app.logger.error("Error in parsing Maxima sales: %s", e)
        flash("Error in parsing Maxima sales", "danger")
    return redirect(url_for('admin.index'))

@admin_bp.route('/run_rimi', methods=['POST'])
def run_rimi():
    try:
        run_in_background(parse_rimi_sales)
        flash("Rimi sales parsing started in the background.", "success")
    except Exception as e:
        current_app.logger.error("Error in parsing Rimi sales: %s", e)
        flash("Error in parsing Rimi sales", "danger")
    return redirect(url_for('admin.index'))

@admin_bp.route('/categorize', methods=['POST'])
def categorize():
    try:
        run_in_background(categorize_maxima_items)
        flash("Categorizing Maxima items started in the background.", "success")
    except Exception as e:
        current_app.logger.error("Error in categorizing Maxima items: %s", e)
        flash("Error in categorizing Maxima items", "danger")
    return redirect(url_for('admin.index'))

@admin_bp.route('/search', methods=['GET'])
def search():
    query = request.args.get("query", "")
    from app.models import Item
    if query:
        items = list(Item.collection().find({"name": {"$regex": query, "$options": "i"}}))
    else:
        items = []
    return render_template("admin_search.html", items=items, query=query)

@admin_bp.route("/upload_images", methods=["POST"])
def upload_images():
    """
    Route to upload images for all items.
    """
    try:
        run_in_background(upload_all_images)
        flash("Image upload started in the background.", "success")
    except Exception as e:
        flash(f"Error during image upload: {e}", "error")
    return redirect(url_for("admin.index"))
