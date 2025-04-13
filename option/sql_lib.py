import sqlite3
import os
from pandas import DataFrame

OPTION_DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),"database","option_data.db")

def create_option_database(db_path : str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS option_snapshot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date DATE,
        dte INTEGER,
        expiration DATE,
        strike REAL,
        option_type TEXT,
        iv REAL,
        delta REAL,
        gamma REAL,
        theta REAL,
        vega REAL,
        rho REAL,
        oi INTEGER,
        volume INTEGER,
        last_price REAL
    );
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_snapshot_key
    ON option_snapshot(symbol, date, dte, strike, option_type);
    """)

    conn.commit()
    conn.close()

def insert_option_db(df : DataFrame):
    conn = sqlite3.connect(OPTION_DATABASE_PATH)
    df.to_sql("option_snapshot", conn, if_exists="append", index=False)
    conn.close()

if __name__ == "__main__":
    print(OPTION_DATABASE_PATH)
    create_option_database(OPTION_DATABASE_PATH)