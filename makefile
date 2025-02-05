install:
	@echo "Installing dependencies from requirements.txt..."
	. .venv/bin/activate && pip install -r requirements.txt

run:
	FLASK_APP=app flask run

run-dev:
	FLASK_APP=app FLASK_DEBUG=TRUE flask run

reset-db:
	@echo "Resetting MongoDB 'items' collection..."
	. .venv/bin/activate && python3 -c "from app.models import Item; from app import create_app; app=create_app(); app.app_context().push(); Item.collection().drop(); print('MongoDB items collection has been reset.')"

test:
	@echo "Running tests..."
	. .venv/bin/activate && export PYTHONPATH=. && pytest

update-requirements:
	@echo "Updating requirements.txt..."
	. .venv/bin/activate && pip3 freeze > requirements.txt

lint:
	pylint app/