from .models import db  # Changed to a relative import

def setup_fts():
    sql_file = '/Users/melihbulut/Grocy/migrations/fts_setup.sql'
    with open(sql_file, 'r') as f:
        sql = f.read()
    conn = db.engine.raw_connection()
    try:
        cursor = conn.cursor()
        cursor.executescript(sql)
        conn.commit()
    finally:
        conn.close()

if __name__ == '__main__':
    setup_fts()
    print("FTS table and triggers created.")
