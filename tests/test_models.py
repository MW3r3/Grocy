from bson.objectid import ObjectId
import pytest
from datetime import datetime
from flask import Flask
from app.models import Item

# Fake collection implementation for testing
class FakeCollection:
    def __init__(self):
        self.data = {}
    def find(self, *args, **kwargs):
        return list(self.data.values())
    def find_one(self, query):
        for doc in self.data.values():
            match = True
            for k, v in query.items():
                if k == "_id":
                    if doc.get("_id") != v:
                        match = False
                        break
                elif doc.get(k) != v:
                    match = False
                    break
            if match:
                return doc
        return None
    def insert_one(self, data):
        _id = ObjectId()  # generate a valid ObjectId
        data["_id"] = _id
        self.data[_id] = data
        class Result:
            inserted_id = _id
        return Result()
    def update_one(self, query, update_doc):
        doc = self.find_one(query)
        if doc:
            for k, v in update_doc.get("$set", {}).items():
                doc[k] = v
    def delete_one(self, query):
        doc = self.find_one(query)
        if doc:
            _id = doc["_id"]
            del self.data[_id]
    def aggregate(self, pipeline):
        return list(self.data.values())

# Fixture to setup a fake collection and patch Item.collection and init_collection
@pytest.fixture(autouse=True)
def fake_db(monkeypatch):
    fake_collection = FakeCollection()
    monkeypatch.setattr(Item, "collection", lambda: fake_collection)
    monkeypatch.setattr(Item, "init_collection", lambda: None)
    return fake_collection

def test_create_and_get_item(fake_db):
    now = datetime.utcnow()
    data = {
        "name": "Test Product",
        "product_id": "123",
        "description": "",
        "search_name": "test product",
        "image_url": "",
        "store": "TestStore",
        "category": "TestCategory",
        "stock": True,
        "unit": "g",
        "quantity": 100,
        "brand": "TestBrand",
        "price": {
            "value": 10.0,
            "old_value": 10.0,
            "discount": 0,
            "currency": "EUR",
            "price_per_unit": 0.1
        },
        "time": {
            "created": now,
            "updated": now,
            "discount_deadline": None
        }
    }
    created = Item.create(data)
    item = Item.collection().find_one({"_id": created["_id"]})
    assert item is not None
    assert item["name"] == "Test Product"

def test_update_item(fake_db):
    now = datetime.utcnow()
    data = {
        "name": "Update Product",
        "product_id": "456",
        "description": "",
        "search_name": "update product",
        "image_url": "",
        "store": "TestStore",
        "category": "OldCategory",
        "stock": True,
        "unit": "g",
        "quantity": 200,
        "brand": "TestBrand",
        "price": {
            "value": 20.0,
            "old_value": 20.0,
            "discount": 0,
            "currency": "EUR",
            "price_per_unit": 0.1
        },
        "time": {
            "created": now,
            "updated": now,
            "discount_deadline": None
        }
    }
    created = Item.create(data)
    updated_item = Item.update(created["_id"], {"category": "NewCategory"})
    assert updated_item["category"] == "NewCategory"

def test_delete_item(fake_db):
    now = datetime.utcnow()
    data = {
        "name": "Delete Product",
        "product_id": "789",
        "description": "",
        "search_name": "delete product",
        "image_url": "",
        "store": "TestStore",
        "category": "TestCategory",
        "stock": True,
        "unit": "g",
        "quantity": 300,
        "brand": "TestBrand",
        "price": {
            "value": 30.0,
            "old_value": 30.0,
            "discount": 0,
            "currency": "EUR",
            "price_per_unit": 0.1
        },
        "time": {
            "created": now,
            "updated": now,
            "discount_deadline": None
        }
    }
    created = Item.create(data)
    Item.delete(created["_id"])
    deleted = Item.collection().find_one({"_id": created["_id"]})
    assert deleted is None

def test_remove_diacritics():
    text_with_diacritics = "čćžšđ"
    normalized = Item.remove_diacritics(text_with_diacritics)
    assert normalized != text_with_diacritics

def test_search_by_name(fake_db, monkeypatch):
    # Wrap test logic in a Flask app context to avoid "working outside application context" error
    test_app = Flask("test_app")
    test_app.app_context().push()
    now = datetime.utcnow()
    items = [
        {
            "name": "Café Latte",
            "product_id": "001",
            "description": "",
            "search_name": "cafe latte",
            "image_url": "",
            "store": "TestStore",
            "category": "Beverages",
            "stock": True,
            "unit": "ml",
            "quantity": 250,
            "brand": "CoffeeBrand",
            "price": {
                "value": 3.5,
                "old_value": 3.5,
                "discount": 0,
                "currency": "EUR",
                "price_per_unit": 14.0
            },
            "time": {
                "created": now,
                "updated": now,
                "discount_deadline": None
            }
        },
        {
            "name": "Cafe Latte",
            "product_id": "002",
            "description": "",
            "search_name": "cafe latte",
            "image_url": "",
            "store": "TestStore",
            "category": "Beverages",
            "stock": True,
            "unit": "ml",
            "quantity": 250,
            "brand": "CoffeeBrand",
            "price": {
                "value": 3.5,
                "old_value": 3.5,
                "discount": 0,
                "currency": "EUR",
                "price_per_unit": 14.0
            },
            "time": {
                "created": now,
                "updated": now,
                "discount_deadline": None
            }
        }
    ]
    for data in items:
        Item.create(data)
    results = Item.search_by_name("cafe")
    # Since our fake aggregate returns all docs, ensure both appear
    assert len(results) >= 2