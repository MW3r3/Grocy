from flask import Blueprint, render_template, request, redirect, url_for, flash
from .scraper import scrape_pdf
from .models import db, Item

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('base.html')

@main.route('/upload', methods=['GET', 'POST'])
def upload_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part.')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file.')
            return redirect(request.url)
        if file:
            # Save file temporarily
            file_path = f"/tmp/{file.filename}"
            file.save(file_path)
            
            # Process the PDF using your scrape_pdf function
            items_data = scrape_pdf(file_path)
            
            # Example logic: Assume items_data returns a list of dictionaries with 'name' and 'quantity'
            for item in items_data:
                new_item = Item(name=item.get('name'), quantity=item.get('quantity', 0))
                db.session.add(new_item)
            db.session.commit()
            
            flash('File uploaded and processed successfully.')
            return redirect(url_for('main.home'))
    return render_template('upload.html')

