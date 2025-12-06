"""CRM database for contacts and engagement tracking."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.config import settings


class CRMStore:
    """CRM database for contact management and outreach."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.database.crm_db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize CRM schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    phone TEXT,
                    email TEXT,
                    preferred_contact TEXT DEFAULT 'phone',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    interaction_type TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    interest TEXT NOT NULL,
                    UNIQUE(person_id, interest)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contact_person ON contacts(person_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interest_person ON interests(person_id)")
    
    def add_contact(self, person_id: int, phone: str = None, email: str = None) -> int:
        """Add or update contact info for a person."""
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM contacts WHERE person_id = ?", (person_id,)
            ).fetchone()
            
            if existing:
                conn.execute("""
                    UPDATE contacts SET phone = ?, email = ?, updated_at = ?
                    WHERE person_id = ?
                """, (phone, email, datetime.now().isoformat(), person_id))
                return existing[0]
            else:
                cursor = conn.execute("""
                    INSERT INTO contacts (person_id, phone, email)
                    VALUES (?, ?, ?)
                """, (person_id, phone, email))
                return cursor.lastrowid
    
    def get_contact(self, person_id: int) -> Optional[dict]:
        """Get contact info for a person."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM contacts WHERE person_id = ?", (person_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def add_interaction(self, person_id: int, interaction_type: str, notes: str = None) -> int:
        """Log an interaction with a person."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO interactions (person_id, interaction_type, notes)
                VALUES (?, ?, ?)
            """, (person_id, interaction_type, notes))
            return cursor.lastrowid
    
    def get_interactions(self, person_id: int) -> list[dict]:
        """Get all interactions for a person."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM interactions WHERE person_id = ? ORDER BY created_at DESC",
                (person_id,)
            ).fetchall()
            return [dict(row) for row in rows]
    
    def add_interest(self, person_id: int, interest: str) -> bool:
        """Add an interest for a person."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    "INSERT INTO interests (person_id, interest) VALUES (?, ?)",
                    (person_id, interest.lower())
                )
                return True
            except sqlite3.IntegrityError:
                return False
    
    def get_interests(self, person_id: int) -> list[str]:
        """Get all interests for a person."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT interest FROM interests WHERE person_id = ?", (person_id,)
            ).fetchall()
            return [row[0] for row in rows]
    
    def find_by_interest(self, interest: str) -> list[int]:
        """Find all person IDs with a given interest."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT person_id FROM interests WHERE interest LIKE ?",
                (f"%{interest.lower()}%",)
            ).fetchall()
            return [row[0] for row in rows]
    
    def find_by_location(self, location: str) -> list[int]:
        """Find persons by location (requires join with persons table)."""
        from src.graph.person_store import PersonStore
        store = PersonStore()
        persons = store.get_all()
        return [p.id for p in persons if p.location and location.lower() in p.location.lower()]