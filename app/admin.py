from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app.scraper import parse_maxima_sales, parse_rimi_sales, categorize_maxima_items
import os  

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')

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
        parse_maxima_sales()
        flash("Maxima sales parsed successfully", "success")
    except Exception as e:
        current_app.logger.error("Error in parsing Maxima sales: %s", e)
        flash("Error in parsing Maxima sales", "danger")
    return redirect(url_for('admin.index'))

@admin_bp.route('/run_rimi', methods=['POST'])
def run_rimi():
    try:
        parse_rimi_sales()
        flash("Rimi sales parsed successfully", "success")
    except Exception as e:
        current_app.logger.error("Error in parsing Rimi sales: %s", e)
        flash("Error in parsing Rimi sales", "danger")
    return redirect(url_for('admin.index'))

@admin_bp.route('/categorize', methods=['POST'])
def categorize():
    try:
        categorize_maxima_items()
        flash("Categorized Maxima items successfully", "success")
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
