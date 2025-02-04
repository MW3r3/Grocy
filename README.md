# Grocy

Grocy is a Flask application designed to scrape discount booklets from grocery stores' websites, extract individual items and their discounts, and store the data in a SQLite database to show which market has the cheapest prices.

**Note: This project is still in progress.**

## Features

- Scrapes and downloads discount data from Maxima.lv
- Scrapes discount data from Rimi.lv
- Main database schema for storing data
- Displays the cheapest prices for items across different markets (to be implemented)
- Easy setup and configuration

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/grocy.git
   ```

2. Navigate to the project directory:
   ```
   cd grocy
   ```

3. Create a virtual environment:
   ```
   python -m venv venv
   ```

4. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

5. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the application, execute the following command:
```
flask run
```

Visit `http://127.0.0.1:5000` in your web browser to access the application.

## Scraping Data

To download price data from Maxima.lv, run the following script:
```
python app/scraper.py
```

## Using the Makefile

A Makefile is provided to simplify common tasks. You can use the following commands:

- Install dependencies:
  ```
  make install
  ```

- Run the application:
  ```
  make run
  ```

- Reset the database:
  ```
  make reset-db
  ```

- Initialize tests:
  ```
  make test
  ```

## Configuring Pylint

To get rid of `E1101` errors for SQLAlchemy dynamic attributes, you can run Pylint with the following options:
```
pylint --ignored-classes=SQLAlchemy,scoped_session --generated-members=Column,Integer,String,Float,DateTime,add,commit,delete app/models.py
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or features.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.