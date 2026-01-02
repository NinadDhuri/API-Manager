import sqlite3
import contextlib

DB_FILE = "gateway.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@contextlib.contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def init_db_schema():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                active BOOLEAN DEFAULT 1,
                rate_limit INTEGER DEFAULT 60
            )
        """)
        conn.commit()

def add_partner(name, api_key, rate_limit=60):
    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO partners (name, api_key, rate_limit) VALUES (?, ?, ?)",
                (name, api_key, rate_limit)
            )
            conn.commit()
            print(f"Added partner: {name}")
        except sqlite3.IntegrityError:
            print(f"Partner with key {api_key} already exists.")

def get_partner_by_key(api_key):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM partners WHERE api_key = ?", (api_key,))
        return cursor.fetchone()
