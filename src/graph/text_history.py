"""Text input history storage."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class TextEntry:
    """Text input entry."""
    id: Optional[int] = None
    text: str = ""
    status: str = "pending"  # pending, processed, failed
    persons_found: int = 0
    relationships_found: int = 0
    created_at: str = ""
    processed_at: str = ""
    error_message: str = ""


class TextHistory:
    """Store and retrieve text input history."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "data/history/text_history.db"
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS text_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    persons_found INTEGER DEFAULT 0,
                    relationships_found INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    processed_at TEXT,
                    error_message TEXT
                )
            """)
    
    def add_entry(self, text: str) -> int:
        """Add a new text entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO text_entries (text, created_at) VALUES (?, ?)",
                (text, datetime.now().isoformat())
            )
            return cursor.lastrowid
    
    def update_status(self, entry_id: int, status: str, persons: int = 0, 
                      relationships: int = 0, error: str = ""):
        """Update entry status after processing."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE text_entries 
                SET status = ?, persons_found = ?, relationships_found = ?,
                    processed_at = ?, error_message = ?
                WHERE id = ?
            """, (status, persons, relationships, datetime.now().isoformat(), error, entry_id))
    
    def get_entry(self, entry_id: int) -> Optional[TextEntry]:
        """Get entry by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM text_entries WHERE id = ?", (entry_id,)).fetchone()
            return self._row_to_entry(row) if row else None
    
    def get_all(self, limit: int = 50) -> list[TextEntry]:
        """Get recent entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM text_entries ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [self._row_to_entry(row) for row in rows]
    
    def delete_entry(self, entry_id: int) -> bool:
        """Delete an entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM text_entries WHERE id = ?", (entry_id,))
            return cursor.rowcount > 0
    
    def clear_all(self) -> int:
        """Clear all history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM text_entries")
            return cursor.rowcount
    
    def _row_to_entry(self, row) -> TextEntry:
        return TextEntry(
            id=row["id"],
            text=row["text"],
            status=row["status"],
            persons_found=row["persons_found"] or 0,
            relationships_found=row["relationships_found"] or 0,
            created_at=row["created_at"] or "",
            processed_at=row["processed_at"] or "",
            error_message=row["error_message"] or ""
        )
