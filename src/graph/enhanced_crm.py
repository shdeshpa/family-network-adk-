"""Enhanced CRM database with structured fields."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class PersonProfile:
    """Enhanced person profile."""
    id: Optional[int] = None
    first_name: str = ""
    last_name: str = ""
    gender: str = ""
    age: Optional[int] = None
    
    phone: str = ""
    email: str = ""
    preferred_currency: str = "USD"
    
    city: str = ""
    state: str = ""
    country: str = ""
    
    gothra: str = ""
    nakshatra: str = ""
    
    general_interests: list = field(default_factory=list)
    temple_interests: list = field(default_factory=list)
    
    notes: str = ""
    is_archived: bool = False
    family_id: Optional[int] = None
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class EnhancedCRM:
    """Enhanced CRM with structured fields."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "data/crm/enhanced.db"
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT,
                    gender TEXT,
                    age INTEGER,
                    phone TEXT,
                    email TEXT,
                    preferred_currency TEXT DEFAULT 'USD',
                    city TEXT,
                    state TEXT,
                    country TEXT,
                    gothra TEXT,
                    nakshatra TEXT,
                    general_interests TEXT DEFAULT '[]',
                    temple_interests TEXT DEFAULT '[]',
                    notes TEXT,
                    is_archived INTEGER DEFAULT 0,
                    family_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS families (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    is_archived INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON profiles(first_name, last_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_city ON profiles(city)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_family ON profiles(family_id)")
    
    def add_person(self, profile: PersonProfile) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO profiles (
                    first_name, last_name, gender, age, phone, email, preferred_currency,
                    city, state, country, gothra, nakshatra,
                    general_interests, temple_interests, notes, family_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.first_name, profile.last_name, profile.gender, profile.age,
                profile.phone, profile.email, profile.preferred_currency,
                profile.city, profile.state, profile.country,
                profile.gothra, profile.nakshatra,
                json.dumps(profile.general_interests),
                json.dumps(profile.temple_interests),
                profile.notes, profile.family_id
            ))
            return cursor.lastrowid
    
    def get_person(self, person_id: int) -> Optional[PersonProfile]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM profiles WHERE id = ?", (person_id,)).fetchone()
            return self._row_to_profile(row) if row else None
    
    def update_person(self, person_id: int, **kwargs) -> bool:
        for key in ['general_interests', 'temple_interests']:
            if key in kwargs and isinstance(kwargs[key], list):
                kwargs[key] = json.dumps(kwargs[key])
        kwargs['updated_at'] = datetime.now().isoformat()
        
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [person_id]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"UPDATE profiles SET {set_clause} WHERE id = ?", values)
            return cursor.rowcount > 0
    
    def delete_person(self, person_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM profiles WHERE id = ?", (person_id,))
            return cursor.rowcount > 0
    
    def archive_person(self, person_id: int) -> bool:
        return self.update_person(person_id, is_archived=1)
    
    def search(self, query: str = None, city: str = None, gothra: str = None, 
               include_archived: bool = False) -> list[PersonProfile]:
        conditions = []
        params = []
        
        if not include_archived:
            conditions.append("is_archived = 0")
        if query:
            conditions.append("(first_name LIKE ? OR last_name LIKE ? OR notes LIKE ?)")
            params.extend([f"%{query}%"] * 3)
        if city:
            conditions.append("city LIKE ?")
            params.append(f"%{city}%")
        if gothra:
            conditions.append("gothra LIKE ?")
            params.append(f"%{gothra}%")
        
        where = " AND ".join(conditions) if conditions else "1=1"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"SELECT * FROM profiles WHERE {where}", params).fetchall()
            return [self._row_to_profile(row) for row in rows]
    
    def get_all(self, include_archived: bool = False) -> list[PersonProfile]:
        return self.search(include_archived=include_archived)
    
    # Family management
    def create_family(self, name: str, description: str = "") -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO families (name, description) VALUES (?, ?)",
                (name, description)
            )
            return cursor.lastrowid
    
    def get_families(self, include_archived: bool = False) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            where = "" if include_archived else "WHERE is_archived = 0"
            rows = conn.execute(f"SELECT * FROM families {where}").fetchall()
            return [dict(row) for row in rows]
    
    def archive_family(self, family_id: int) -> int:
        """Archive entire family."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE families SET is_archived = 1 WHERE id = ?", (family_id,))
            cursor = conn.execute("UPDATE profiles SET is_archived = 1 WHERE family_id = ?", (family_id,))
            return cursor.rowcount
    
    def _row_to_profile(self, row) -> PersonProfile:
        return PersonProfile(
            id=row["id"],
            first_name=row["first_name"],
            last_name=row["last_name"] or "",
            gender=row["gender"] or "",
            age=row["age"],
            phone=row["phone"] or "",
            email=row["email"] or "",
            preferred_currency=row["preferred_currency"] or "USD",
            city=row["city"] or "",
            state=row["state"] or "",
            country=row["country"] or "",
            gothra=row["gothra"] or "",
            nakshatra=row["nakshatra"] or "",
            general_interests=json.loads(row["general_interests"] or "[]"),
            temple_interests=json.loads(row["temple_interests"] or "[]"),
            notes=row["notes"] or "",
            is_archived=bool(row["is_archived"]),
            family_id=row["family_id"]
        )
