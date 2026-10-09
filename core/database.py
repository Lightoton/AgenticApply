import sqlite3
import os
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'agentic_apply.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seen_urls (
                    url TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seen_companies (
                    company_name TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def is_url_seen(self, url: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM seen_urls WHERE url = ?', (url,))
            return cursor.fetchone() is not None

    def mark_url_seen(self, url: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO seen_urls (url) VALUES (?)', (url,))
            conn.commit()
            
    def get_all_seen_urls(self) -> set:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT url FROM seen_urls')
            return set(row[0] for row in cursor.fetchall())

    def is_company_seen(self, company_name: str) -> bool:
        safe_name = company_name.strip().lower()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM seen_companies WHERE company_name = ?', (safe_name,))
            return cursor.fetchone() is not None

    def mark_company_seen(self, company_name: str):
        safe_name = company_name.strip().lower()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO seen_companies (company_name) VALUES (?)', (safe_name,))
            conn.commit()

db = DatabaseManager()
