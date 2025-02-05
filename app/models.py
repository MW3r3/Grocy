"""
Models module for the Flask application.
"""

import os
import json
import unicodedata
from flask import current_app
from bson.objectid import ObjectId

schema_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'dbschema.json')
with open(schema_path, 'r') as f:
    DBSCHEMA = json.load(f)

class Item:
    @staticmethod
    def collection():
        mongo = current_app.extensions.get("pymongo")
        if not mongo:
            mongo = getattr(current_app, "mongo", None)
        if not mongo:
            raise Exception("PyMongo extension not attached to current_app")
        return mongo.db.items

    @classmethod
    def get_all(cls):
        return list(cls.collection().find())

    @classmethod
    def get_by_id(cls, item_id):
        return cls.collection().find_one({"_id": ObjectId(item_id)})

    @classmethod
    def create(cls, data):
        result = cls.collection().insert_one(data)
        data["_id"] = result.inserted_id
        return data

    @classmethod
    def update(cls, item_id, data):
        update_doc = {
            "$set": data,
            "$currentDate": {"time.updated": True}
        }
        cls.collection().update_one({"_id": ObjectId(item_id)}, update_doc)
        return cls.get_by_id(item_id)

    @classmethod
    def delete(cls, item_id):
        return cls.collection().delete_one({"_id": ObjectId(item_id)})

    @classmethod
    def remove_diacritics(cls, text):
        # Normalize to NFD and filter out non-spacing marks
        return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    
    @classmethod
    def search_by_name(cls, search_term, filters=None):
        # Base search pipeline
        pipeline = [
            {
                "$search": {
                    "index": "search_name",
                    "text": {
                        "query": search_term,
                        "path": "search_name",  
                        "fuzzy": {}
                    }
                }
            }
        ]

        # Add filters if provided
        match_conditions = {}
        if filters:
            if 'stock' in filters:
                match_conditions['stock'] = filters['stock']
            if 'category' in filters:
                match_conditions['category'] = filters['category']
            if 'min_quantity' in filters:
                match_conditions['quantity'] = {'$gte': filters['min_quantity']}
            if 'max_quantity' in filters:
                match_conditions.setdefault('quantity', {})['$lte'] = filters['max_quantity']
            if 'store' in filters:
                match_conditions['store'] = filters['store']

        # Add match stage if there are any conditions
        if match_conditions:
            pipeline.append({"$match": match_conditions})

        pipeline.append({"$limit": 10})
        
        results = list(cls.collection().aggregate(pipeline))
        current_app.logger.info(
            "Search results for '%s' with filters %s: %s", 
            search_term, 
            filters, 
            results
        )
        return results

    @classmethod
    def init_collection(cls):
        mongo = getattr(current_app, "mongo", None)
        if not mongo:
            current_app.logger.error("PyMongo not initialized")
            return
        db = mongo.db
        if db is None:
            current_app.logger.error("MongoDB database not available")
            return
        try:
            colls = db.list_collection_names()
        except Exception as e:
            current_app.logger.error("Error listing collections: %s", e)
            return
        if "items" in colls:
            current_app.logger.info("Collection 'items' already exists. Skipping creation.")
        else:
            db.create_collection("items", validator={"$jsonSchema": DBSCHEMA})
            current_app.logger.info("Created collection 'items' with schema validation.")


