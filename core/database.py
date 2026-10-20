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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seen_roles (
                    dedup_key TEXT PRIMARY KEY,
                    company TEXT,
                    title TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    AGENCY_ALLOWLIST = {
        "epunkt", "isg", "hays", "michael page", "amoria bond",
        "randstad", "adecco", "robert half", "wienit", "iventa",
        "pmc international", "schulmeister", "karriere.at"
    }

    @classmethod
    def is_agency(cls, company_name: str) -> bool:
        if not company_name:
            return False
        norm = company_name.strip().lower()
        return any(agency in norm for agency in cls.AGENCY_ALLOWLIST)

    @classmethod
    def generate_role_key(cls, company: str, title: str) -> str:
        import re
        norm_company = re.sub(r'[^a-z0-9]', '', (company or "").strip().lower())
        raw_title = (title or "").strip().lower()
        # Strip gender tags like (m/w/d), (all genders), (f/m/d), etc.
        clean_title = re.sub(r'\(.*?\)', '', raw_title)
        norm_title = re.sub(r'[^a-z0-9]', '', clean_title)

        if cls.is_agency(company):
            return f"agency:{norm_company}:{norm_title}"
        return f"role:{norm_company}:{norm_title}"

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

    def is_role_seen(self, company: str, title: str) -> bool:
        key = self.generate_role_key(company, title)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM seen_roles WHERE dedup_key = ?', (key,))
            return cursor.fetchone() is not None

    def mark_role_seen(self, company: str, title: str):
        key = self.generate_role_key(company, title)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO seen_roles (dedup_key, company, title) VALUES (?, ?, ?)',
                (key, company.strip(), title.strip())
            )
            # Also record in seen_companies for backward compatibility unless it is an agency
            if not self.is_agency(company):
                safe_name = company.strip().lower()
                cursor.execute('INSERT OR IGNORE INTO seen_companies (company_name) VALUES (?)', (safe_name,))
            conn.commit()

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
