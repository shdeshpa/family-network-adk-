"""SQLite store for person attributes."""

import sqlite3
import json
from pathlib import Path
from typing import Optional
from datetime import date, datetime

from src.models import Person
from src.config import settings


class PersonStore:
    """Store person attributes in SQLite."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.database.persons_db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS persons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    gender TEXT,
                    birth_date TEXT,
                    phone TEXT,
                    email TEXT,
                    location TEXT,
                    interests TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON persons(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_phone ON persons(phone)")
    
    def add_person(self, person: Person) -> int:
        """Add a person and return their ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO persons (name, gender, birth_date, phone, email, location, interests)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                person.name,
                person.gender,
                person.birth_date.isoformat() if person.birth_date else None,
                person.phone,
                person.email,
                person.location,
                json.dumps(person.interests) if person.interests else "[]"
            ))
            return cursor.lastrowid
    
    def get_person(self, person_id: int) -> Optional[Person]:
        """Get person by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM persons WHERE id = ?", (person_id,)
            ).fetchone()
            
            if row:
                return self._row_to_person(row)
            return None
    
    def find_by_name(self, name: str) -> list[Person]:
        """Find persons by name (partial match)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM persons WHERE name LIKE ?", (f"%{name}%",)
            ).fetchall()
            return [self._row_to_person(row) for row in rows]
    
    def find_by_phone(self, phone: str) -> Optional[Person]:
        """Find person by phone number."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM persons WHERE phone = ?", (phone,)
            ).fetchone()
            return self._row_to_person(row) if row else None
    
    def update_person(self, person_id: int, **kwargs) -> bool:
        """Update person attributes."""
        allowed = {"name", "gender", "birth_date", "phone", "email", "location", "interests"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        
        if not updates:
            return False
        
        if "interests" in updates:
            updates["interests"] = json.dumps(updates["interests"])
        if "birth_date" in updates and updates["birth_date"]:
            updates["birth_date"] = updates["birth_date"].isoformat()
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [person_id]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE persons SET {set_clause} WHERE id = ?", values
            )
            return cursor.rowcount > 0
    
    def get_all(self) -> list[Person]:
        """Get all persons."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM persons").fetchall()
            return [self._row_to_person(row) for row in rows]
    
    def _row_to_person(self, row: sqlite3.Row) -> Person:
        """Convert database row to Person model."""
        return Person(
            id=row["id"],
            name=row["name"],
            gender=row["gender"],
            birth_date=date.fromisoformat(row["birth_date"]) if row["birth_date"] else None,
            phone=row["phone"],
            email=row["email"],
            location=row["location"],
            interests=json.loads(row["interests"]) if row["interests"] else []
        )
    
    def delete_person(self, person_id: int) -> bool:
        """Delete a person by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM persons WHERE id = ?", (person_id,))
            return cursor.rowcount > 0