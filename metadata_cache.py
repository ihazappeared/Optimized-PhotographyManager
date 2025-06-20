import os
import json
import sqlite3
import hashlib
from typing import Optional


class MetadataCache:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
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
                    mod_time REAL NOT NULL,
                    FOREIGN KEY(checksum) REFERENCES metadata(checksum)
                )
            """)

    def load_into_memory(self) -> dict[str, dict]:
        index = {}
        cursor = self.conn.execute("""
            SELECT metadata.checksum, metadata.metadata_json, filepaths.mod_time, filepaths.path
            FROM metadata
            JOIN filepaths ON metadata.checksum = filepaths.checksum
        """)
        for checksum, metadata_json, mod_time, path in cursor:
            metadata = json.loads(metadata_json)
            index[checksum] = {
                "path": path,
                "mod_time": mod_time,
                "date_taken": metadata.get("date_taken"),
            }
        return index

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
            """
            SELECT metadata.checksum, metadata.metadata_json, filepaths.mod_time
            FROM metadata JOIN filepaths ON metadata.checksum = filepaths.checksum
            WHERE filepaths.path = ?
            """,
            (path,)
        )
        row = cursor.fetchone()
        if row:
            checksum, metadata_json, mod_time = row
            return {
                "checksum": checksum,
                "metadata_json": metadata_json,
                "mod_time": mod_time,
            }
        return None

    def store(self, checksum: str, metadata_dict: dict, path: str, mod_time: float) -> None:
        metadata_json = json.dumps(metadata_dict)
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO metadata (checksum, metadata_json) VALUES (?, ?)",
                (checksum, metadata_json)
            )
            self.conn.execute(
                "INSERT OR REPLACE INTO filepaths (path, checksum, mod_time) VALUES (?, ?, ?)",
                (path, checksum, mod_time)
            )

    def prune_orphaned_paths(self, current_paths: set[str]) -> None:
        if not current_paths:
            # Delete all if no current paths
            with self.conn:
                self.conn.execute("DELETE FROM filepaths")
            return
        placeholders = ','.join('?' for _ in current_paths)
        with self.conn:
            self.conn.execute(
                f"DELETE FROM filepaths WHERE path NOT IN ({placeholders})",
                tuple(current_paths)
            )

    def close(self) -> None:
        self.conn.close()
