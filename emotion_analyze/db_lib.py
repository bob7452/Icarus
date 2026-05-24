import sqlite3
import os
import shutil
from datetime import datetime, timezone, timedelta

TW = timezone(timedelta(hours=8))

class TradingDB:
    def __init__(self, db_name='trading.db'):
        self.db = db_name
        self._ensure_path()
        self._init_db()

    def _ensure_path(self):
        """確保資料庫目錄存在"""
        db_dir = os.path.dirname(self.db)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def _init_db(self):
        """初始化表格，如果檔案遺失則會自動重建"""
        with sqlite3.connect(self.db) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS trading_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT,
                created_at TIMESTAMP,
                processed INTEGER DEFAULT 0)''')

    def _ensure_db_exists(self):
        """如果檔案真的不見了，重新建立連線與表格"""
        if not os.path.exists(self.db):
            self._init_db()

    def backup_db(self):
        """簡單備份功能"""
        if os.path.exists(self.db):
            shutil.copy(self.db, self.db + ".bak")

    def add_log(self, text):
        self._ensure_db_exists()
        tw_time = datetime.now(TW).strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO trading_logs (message_text, created_at) VALUES (?, ?)", (text, tw_time))

    def get_logs_by_range(self, start_time, end_time):
        self._ensure_db_exists()
        with sqlite3.connect(self.db) as conn:
            cursor = conn.cursor()
            query = "SELECT id, message_text FROM trading_logs WHERE created_at >= ? AND created_at < ? AND processed = 0"
            cursor.execute(query, (start_time, end_time))
            return cursor.fetchall()

    def mark_as_processed(self, ids):
        if not ids: return
        self._ensure_db_exists()
        with sqlite3.connect(self.db) as conn:
            # 加入交易鎖定，確保原子性
            conn.execute("BEGIN TRANSACTION")
            try:
                conn.execute(f"UPDATE trading_logs SET processed = 1 WHERE id IN ({','.join(['?']*len(ids))})", ids)
                conn.commit()
            except:
                conn.rollback()
                raise
