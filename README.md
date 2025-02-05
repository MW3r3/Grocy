# Grocy - Grocery Price Comparison App

A Flask application that scrapes and compares grocery prices from Latvian stores (Maxima and Rimi). The app collects discount information and helps users find the best deals across different supermarkets.

## Features

- Real-time price scraping from:
  - Maxima.lv
  - Rimi.lv
- Automated categorization of products
- Fuzzy search functionality
- Price comparison across stores
- Discount tracking and deadline monitoring
- MongoDB integration with schema validation
- Multi-threaded scraping for improved performance

## Prerequisites

- Python 3.x
- MongoDB Atlas account
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```sh
git clone <repository-url>
cd grocy
```

2. Create and activate a virtual environment:
```sh
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```sh
make install
# or
pip install -r requirements.txt
```

## Configuration

1. The MongoDB connection string is configured in 

__init__.py

. You can override it using the `MONGO_URI` environment variable.

2. Store scraping URLs are configured in 

links.txt

.

## Usage

### Running the Application

Start the development server:
```sh
make run-dev
# or
FLASK_APP=app FLASK_DEBUG=TRUE flask run
```

### Running with Gunicorn

To run the application with Gunicorn:
```sh
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

### Available Make Commands

- `make install`: Install dependencies
- `make run`: Run in production mode
- `make run-dev`: Run in development mode
- `make reset-db`: Reset the MongoDB collection
- `make test`: Run tests
- `make lint`: Run pylint checks
- 

make update-requirements

: Update 

requirements.txt



## Testing

Run the test suite:
```sh
make test
# or
pytest
```

## Project Structure

```
grocy/
├── app/
│   ├── __init__.py        # Flask app initialization
│   ├── models.py          # Database models
│   ├── routes.py          # API routes
│   ├── scraper.py         # Web scraping logic
│   ├── static/            # Static files
│   └── templates/         # HTML templates
├── tests/                 # Test files
├── scripts/              
│   └── isrgrootx1.pem    # MongoDB certificate
└── data/
    └── dbschema.json     # MongoDB schema
```

## API Endpoints

- `/`: Home page with search functionality
- `/search`: Product search endpoint
- `/scrape`: Trigger Maxima scraping
- `/scrape_rimi`: Trigger Rimi scraping
- `/categorize_maxima`: Categorize Maxima products

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the 

LICENSE

 file for details.
