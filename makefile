install:
	@echo "Installing dependencies from requirements.txt..."
	. .venv/bin/activate && pip install -r requirements.txt

run:
	FLASK_APP=app flask run

reset-db:
	@echo "Creating data folder if it doesn't exist..."
	mkdir -p data
	@echo "Removing existing database file..."
	rm -f data/site.db
	@echo "Creating new database..."
	python3 -c "from app import create_app; from app.models import db; app=create_app(); app.app_context().push(); db.create_all(); print('Database has been reset.')"

test:
	@echo "Running tests..."
	. .venv/bin/activate && export PYTHONPATH=. && pytest

update-requirements:
	@echo "Updating requirements.txt..."
	. .venv/bin/activate && pip3 freeze > requirements.txt

lint:
	pylint app/