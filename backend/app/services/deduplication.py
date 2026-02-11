import hashlib
import sqlite3
import os
from typing import Optional

DB_PATH = "/app/data/ingestion_history.db"

class DeduplicationService:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes the tracking table if it does not exist."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_files (
                content_hash TEXT PRIMARY KEY,
                filename TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def calculate_hash(self, file_content: bytes) -> str:
        """Calculates the MD5 hash of the file's binary content."""
        return hashlib.md5(file_content).hexdigest()

    def is_duplicate(self, content_hash: str) -> bool:
        """Checks whether the hash already exists in the database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM processed_files WHERE content_hash = ?', (content_hash,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def register_file(self, content_hash: str, filename: str):
        """Registers a successfully processed file."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO processed_files (content_hash, filename) VALUES (?, ?)',
                (content_hash, filename)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Already exists (rare race condition case)
        finally:
            conn.close()

# Singleton to be used in the application
deduplication_service = DeduplicationService()
