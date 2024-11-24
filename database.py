import sqlite3
import system_log
from typing import final


class Database:
    def __init__(self, db_name : str) -> None:
        self.db_name = db_name

    def __enter__(self):
        self.connection = sqlite3.connect(self.db_name)
        self.cursor = self.connection.cursor()
        self.initialize_db()
        system_log.debug(f'DataBase {self.db_name} connection opened.')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            system_log.error(f"An exception occurred: {exc_value}")
        self.connection.commit()
        self.connection.close()
        system_log.debug(f"Database {self.db_name} connection closed.")

    def initialize_db(self,):
        raise NotImplementedError('this function needs to override by instance')

@final
class OpenInterest_database(Database):

    def initialize_db(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS open_interest (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_name TEXT NOT NULL,
            date DATE NOT NULL,
            strike DECIMAL(10, 2) NOT NULL,
            open_interest INTEGER NOT NULL,
            expiration_date DATE NOT NULL,
            record_time TIMESTAMP NOT NULL,
            UNIQUE(stock_name, date, strike, expiration_date)
        );
        """)
        self.connection.commit()
    
    def upsert_data(self,stock_name, insert_date, strike, open_interest, expiration_date, record_time):
        self.cursor.execute("""
        INSERT INTO open_interest (stock_name, date, strike, open_interest, expiration_date, record_time)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(stock_name, date, strike, expiration_date) DO UPDATE SET
        open_interest = excluded.open_interest,
        record_time = excluded.record_time;
        """, (stock_name, insert_date, strike, open_interest, expiration_date, record_time))
        self.connection.commit()

    def query_by_stock_and_expiration(self,stock_name, expiration_date):
        self.cursor.execute("""
        SELECT date, strike, open_interest, record_time FROM open_interest
        WHERE stock_name = ? AND expiration_date = ?;
        """, (stock_name, expiration_date))
        return self.cursor.fetchall()

    def query_by_time_range(self,start_time, end_time):
        self.cursor.execute("""
        SELECT stock_name, strike, open_interest, record_time
        FROM open_interest
        WHERE record_time BETWEEN ? AND ?;
        """, (start_time, end_time))
        return self.cursor.fetchall()
    
    def delete_expired_data(self,current_date):
        self.cursor.execute("""
        DELETE FROM open_interest WHERE expiration_date < ?;
        """, (current_date,))
        self.connection.commit()


if __name__ == "__main__":
    # 插入範例數據
    from datetime import datetime, date, timedelta
    import os 

    oi_db = os.path.join(os.path.dirname(__file__),'database','oi_database')

    with OpenInterest_database(db_name=oi_db) as db:
        data = [
            ("AAPL", date.today().isoformat(), 1500, 5000, (date.today() + timedelta(days=30)).isoformat(), datetime.now().isoformat()),
            ("AAPL", date.today().isoformat(), 1550, 4500, (date.today() + timedelta(days=30)).isoformat(), datetime.now().isoformat()),
            ("GOOG", date.today().isoformat(), 1500, 3000, (date.today() + timedelta(days=60)).isoformat(), datetime.now().isoformat()),
        ]
        for record in data:
            db.upsert_data(*record)

        # 4. 查詢數據
        def query_by_stock_and_expiration(stock_name, expiration_date):
            db.cursor.execute("""
            SELECT date, strike, open_interest, record_time FROM open_interest
            WHERE stock_name = ? AND expiration_date = ?;
            """, (stock_name, expiration_date))
            return db.cursor.fetchall()

        # 查詢 AAPL 行權日為 30 天後的數據
        expiration_date = (date.today() + timedelta(days=30)).isoformat()
        aapl_data = query_by_stock_and_expiration("AAPL", expiration_date)
        print(f"Data for AAPL with expiration date {expiration_date}:")
        for record in aapl_data:
            print(record)
