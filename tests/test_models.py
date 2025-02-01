import os
import json
import pytest
from datetime import datetime
from app import create_app
from app.models import db, Item

def populate_items_from_json():
    json_path = os.path.join(os.path.dirname(__file__), "..", "data", "example_items.json")
    with open(json_path, "r") as f:
        items_data = json.load(f)["items"]
    for item_data in items_data:
        if "deadline" in item_data and isinstance(item_data["deadline"], str):
            item_data["deadline"] = datetime.fromisoformat(item_data["deadline"])
        Item.create(**item_data)

@pytest.fixture(scope="module")
def test_app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_create_item(test_app):
    item = Item.create(name="TestItem", price=9.99, quantity=5)
    assert item.id is not None
    assert item.name == "TestItem"
    assert item.price == 9.99

def test_get_all_items(test_app):
    for item in Item.get_all():
        Item.delete(item.id)

    populate_items_from_json()
    items = Item.get_all()
    assert len(items) > 50

def test_update_item(test_app):
    item = Item.create(name="UpdateTest", price=15.0, quantity=3)
    updated_item = Item.update(item.id, price=20.0, quantity=4)
    assert updated_item.price == 20.0
    assert updated_item.quantity == 4

def test_delete_item(test_app):
    item = Item.create(name="DeleteTest", price=10.0, quantity=1)
    item_id = item.id
    assert Item.get_by_id(item_id) is not None
    Item.delete(item_id)
    assert Item.get_by_id(item_id) is None

def test_search_by_name(test_app):
    for item in Item.get_all():
        Item.delete(item.id)
    populate_items_from_json()
    results = Item.search_by_name("app")
    names = [item.name for item in results]
    assert any("Apple" in name for name in names)

def test_fuzzy_search(test_app):

    for item in Item.get_all():
        Item.delete(item.id)
    populate_items_from_json()
    
    fuzzy_tests = {
        "bannna": "Banana",
        "grapes": "Grapes",
        "applle": "Apple",
        "pech": "Peach"
    }
    
    for search_term, expected in fuzzy_tests.items():
        results = Item.fuzzy_search_by_name(search_term, threshold=50)
        names = [item.name for item in results]
        assert any(expected in name for name in names), f"Expected '{expected}' in fuzzy search results for '{search_term}'"

def test_nonexistent_item_operations(test_app):
    non_existent_id = 999999
    item = Item.get_by_id(non_existent_id)
    assert item is None, f"Expected None for non-existent item ID {non_existent_id}"
    
    updated_item = Item.update(non_existent_id, price=100.0)
    assert updated_item is None, "Expected None when updating a non-existent item"

    deleted_item = Item.delete(non_existent_id)
    assert deleted_item is None, "Expected None when deleting a non-existent item"