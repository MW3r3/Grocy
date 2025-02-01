from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
from thefuzz import fuzz

db = SQLAlchemy()

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    discount = db.Column(db.Float, nullable=True, default=0.0)
    vendor = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    deadline = db.Column(db.DateTime, nullable=True)
    unit = db.Column(db.String(20), nullable=True)
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
        item = cls.get_by_id(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
        return item

    @classmethod
    def search_by_name(cls, search_term):
        return (
            cls.query.filter(cls.name.ilike(f"%{search_term}%"))
            .order_by(func.length(cls.name))
            .all()
        )

    @classmethod
    def fuzzy_search_by_name(cls, search_term, threshold=60, limit=10):     
        prefilter = search_term[:2] if len(search_term) >= 2 else search_term
        candidates = cls.query.filter(cls.name.ilike(f"%{prefilter}%")).all()  # Loose prefilter
        ranked_items = []
        for item in candidates:
            score = fuzz.ratio(item.name.lower(), search_term.lower())
            if score >= threshold:
                ranked_items.append((item, score))
        ranked_items.sort(key=lambda x: x[1], reverse=True)
        return [item for item, score in ranked_items][:limit]


