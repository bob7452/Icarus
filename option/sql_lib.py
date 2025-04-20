import sqlite3
import os
from pandas import DataFrame
import pandas as pd
from datetime import datetime


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

def create_skew_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skew_snapshot (
            snapshot_date TEXT NOT NULL,
            expiration TEXT NOT NULL,
            put_10delta_skew REAL,
            put_25delta_skew REAL,
            call_put_skew REAL,
            PRIMARY KEY (snapshot_date, expiration)
        )
    """)

    # Add indexes if not exist
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_date ON skew_snapshot (snapshot_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expiration ON skew_snapshot (expiration);")

    conn.commit()
    conn.close()
    print(f"Initialized DB at: {db_path}")

def insert_option_db(df : DataFrame):
    conn = sqlite3.connect(OPTION_DATABASE_PATH)
    df.to_sql("option_snapshot", conn, if_exists="append", index=False)
    conn.close()

def insert_skew_db(df : DataFrame):
    conn = sqlite3.connect(OPTION_DATABASE_PATH)
    df.to_sql("skew_snapshot", conn, if_exists="append", index=False)
    conn.close()

def fetch_data_from_option_db(query : str) -> DataFrame:
    conn = sqlite3.connect(OPTION_DATABASE_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_oi_snapshot_by_date(symbols: list[str], date: datetime) -> pd.DataFrame:
    placeholders = ",".join(f"'{s}'" for s in symbols)
    query = f"""
        SELECT symbol, strike, option_type, expiration, oi
        FROM option_snapshot
        WHERE date = '{date.strftime("%Y-%m-%d")}' AND symbol IN ({placeholders})
    """
    return fetch_data_from_option_db(query)

def get_latest_available_date(symbol: str) -> datetime | None:
    query = f"""
        SELECT MAX(date) AS max_date
        FROM option_snapshot
        WHERE symbol = '{symbol}'
    """
    df = fetch_data_from_option_db(query)
    result = df["max_date"].iloc[0]
    return datetime.strptime(result, "%Y-%m-%d") if pd.notnull(result) else None



if __name__ == "__main__":
    print(OPTION_DATABASE_PATH)
    create_skew_db(OPTION_DATABASE_PATH)