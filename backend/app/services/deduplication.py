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
        """
        Initializes the internal SQLite tracking database.

        Creates the 'processed_files' table if it doesn't exist to persistently 
        store file hashes across application restarts. This ensures incremental ingestion 
        is maintained even after container rebuilds.
        """
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
        """
        Computes a cryptographic MD5 hash of the file's binary content.

        Used to generate a unique fingerprint for the file, allowing the system 
        to identify duplicate content regardless of the filename.

        Args:
            file_content (bytes): The raw binary content of the uploaded file.

        Returns:
            str: The hexadecimal MD5 hash string.
        """
        return hashlib.md5(file_content).hexdigest()

    def is_duplicate(self, content_hash: str) -> bool:
        """
        Checks if a file's content hash has already been processed.

        Queries the SQLite database to prevent redundant embedding generation 
        and storage costs for files that are already indexed.

        Args:
            content_hash (str): The pre-calculated MD5 hash of the file.

        Returns:
            bool: True if the file exists in the database, False otherwise.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM processed_files WHERE content_hash = ?', (content_hash,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def register_file(self, content_hash: str, filename: str):
        """
        Records a successfully processed file into the tracking database.

        Called at the end of the ingestion pipeline to mark the file hash as 'seen'.
        Handles race conditions gracefully via SQLite constraints.

        Args:
            content_hash (str): The unique hash of the processed file.
            filename (str): The original name of the file (for logging purposes).
        """
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
