import sqlite3
from datetime import datetime, timedelta, timezone
# 建立台灣時區 (UTC+8)
TW = timezone(timedelta(hours=8))

class TradingDB:
    def __init__(self, db_name='trading.db'):
        self.db = db_name
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS trading_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT,
                created_at TIMESTAMP,  -- 移除預設值
                processed INTEGER DEFAULT 0)''')

    def add_log(self, text):
        # 取得現在的台灣時間
        tw_time = datetime.now(TW).strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO trading_logs (message_text, created_at) VALUES (?, ?)", (text, tw_time))

    def get_logs_by_range(self, start_time, end_time):
        with sqlite3.connect(self.db) as conn:
            cursor = conn.cursor()
            query = "SELECT id, message_text FROM trading_logs WHERE created_at >= ? AND created_at < ? AND processed = 0"
            cursor.execute(query, (start_time, end_time))
            return cursor.fetchall()

    def mark_as_processed(self, ids):
        if not ids: return
        with sqlite3.connect(self.db) as conn:
            conn.execute(f"UPDATE trading_logs SET processed = 1 WHERE id IN ({','.join(['?']*len(ids))})", ids)