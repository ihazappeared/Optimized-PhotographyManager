import os
import json
import sqlite3
import hashlib
from typing import Optional

class MetadataCache:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    checksum TEXT PRIMARY KEY,
                    metadata_json TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS filepaths (
                    path TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    FOREIGN KEY(checksum) REFERENCES metadata(checksum)
                )
            """)

    @staticmethod
    def compute_checksum(path: str, block_size: int = 4096) -> str:
        try:
            size = os.path.getsize(path)
            with open(path, 'rb') as f:
                start = f.read(block_size)
            return hashlib.md5(start + str(size).encode()).hexdigest()
        except Exception:
            return ""

    def get_metadata_by_path(self, path: str) -> Optional[dict]:
        cursor = self.conn.execute(
            "SELECT metadata.checksum, metadata.metadata_json FROM metadata "
            "JOIN filepaths ON metadata.checksum = filepaths.checksum "
            "WHERE filepaths.path = ?", (path,)
        )
        row = cursor.fetchone()
        if row:
            checksum, metadata_json = row
            return {"checksum": checksum, "metadata_json": metadata_json}
        return None

    def store(self, checksum: str, metadata_dict: dict, path: str) -> None:
        metadata_json = json.dumps(metadata_dict)
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO metadata (checksum, metadata_json) VALUES (?, ?)",
                (checksum, metadata_json)
            )
            self.conn.execute(
                "INSERT OR REPLACE INTO filepaths (path, checksum) VALUES (?, ?)",
                (path, checksum)
            )

    def prune_orphaned_paths(self, current_paths: set) -> None:
        placeholders = ','.join('?' for _ in current_paths) or "''"
        with self.conn:
            self.conn.execute(
                f"DELETE FROM filepaths WHERE path NOT IN ({placeholders})",
                tuple(current_paths)
            )

    def close(self) -> None:
        self.conn.close()
