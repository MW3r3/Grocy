"""
Models module for the Flask application.
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from thefuzz import fuzz
from thefuzz import process  # Add this import with thefuzz imports

db = SQLAlchemy()

class Item(db.Model):
    """
    Model for items in the database.
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    discount = db.Column(db.Float, nullable=True, default=0.0)
    vendor = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    deadline = db.Column(db.DateTime, nullable=True)
    unit = db.Column(db.String(20), nullable=True)
    product_id = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Item {self.name}>"

    @classmethod
    def get_all(cls):
        """Return all items."""
        return cls.query.all()

    @classmethod
    def get_by_id(cls, item_id):
        """Return a single item by id."""
        return cls.query.get(item_id)

    @classmethod
    def create(cls, **kwargs):
        """Create a new item with given fields."""
        new_item = cls(**kwargs)
        db.session.add(new_item)
        db.session.commit()
        return new_item

    @classmethod
    def update(cls, item_id, **kwargs):
        """Update an existing item with provided fields."""
        item = cls.get_by_id(item_id)
        if item:
            for key, value in kwargs.items():
                setattr(item, key, value)
            db.session.commit()
        return item

    @classmethod
    def delete(cls, item_id):
        """Delete an item by id."""
        item = cls.get_by_id(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
        return item

    @classmethod
    def search_by_name(cls, search_term):
        """Search for items by name."""
        return (
            cls.query.filter(cls.name.ilike(f"%{search_term}%"))
            .order_by(func.length(cls.name))
            .all()
        )

    @classmethod
    def fuzzy_search_by_name(cls, search_term, threshold=30, limit=10):
        """Fuzzy search for items by name using thefuzz process.extractBests."""
        candidates = cls.query.all()
        # Build mapping from name to list of items (in case of duplicates)
        name_to_items = {}
        for item in candidates:
            name_to_items.setdefault(item.name, []).append(item)
        # Extract best matching names using process.extractBests
        results = process.extractBests(search_term, list(name_to_items.keys()),
                                       scorer=fuzz.ratio, score_cutoff=threshold, limit=limit)
        # Flatten items from matched names preserving order by score
        final_items = []
        for match_name, score in results:
            final_items.extend(name_to_items[match_name])
        return final_items

    @classmethod
    def fts_search_by_name(cls, search_term):
        """Full-text search for items by name using SQLite FTS5.
           Ensure that the SQLite FTS virtual table 'items_fts' is set up
           and kept in sync with the item table."""
        query = "SELECT rowid FROM items_fts WHERE items_fts MATCH ?"
        result = db.engine.execute(query, (search_term,)).fetchall()
        ids = [row[0] for row in result]
        return cls.query.filter(cls.id.in_(ids)).all()

    @classmethod
    def combined_search_by_name_precise(cls, search_term, fuzzy_threshold=30, fuzzy_limit=10):
        """Combined FTS and fuzzy search with ranking for more accurate results."""
        fts_results = set(cls.fts_search_by_name(search_term))
        fuzzy_results = set(cls.fuzzy_search_by_name(search_term, threshold=fuzzy_threshold, limit=fuzzy_limit))
        # Take union of both result sets.
        combined_set = fts_results.union(fuzzy_results)
        # Score each candidate using fuzz.ratio.
        ranked = [(item, fuzz.ratio(search_term.lower(), item.name.lower())) for item in combined_set]
        # Sort candidates by descending score.
        ranked_sorted = sorted(ranked, key=lambda x: x[1], reverse=True)
        # Return sorted list of items.
        return [item for item, score in ranked_sorted]
