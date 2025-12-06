"""
Family Registry - Generates and manages family codes.

Format: SURNAME-CITY-SEQUENCE
Example: SHARMA-HYD-001, PATEL-MUM-002

This is a DATA LAYER component:
- Handles database operations for families table
- NO business logic (agents decide when to create families)
- Used by crm_server.py MCP tools

Database: Shares crm_v2.db with CRMStoreV2 for referential integrity.
"""

import sqlite3
import uuid
import re
from pathlib import Path
from typing import Optional, List

from src.graph.models_v2 import Family


# Shared database path - same DB as CRMStoreV2
DEFAULT_DB_PATH = "data/crm/crm_v2.db"


class FamilyRegistry:
    """Manages family identifiers and codes."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize families table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS families (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    surname TEXT NOT NULL,
                    city TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    description TEXT,
                    is_archived INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_family_code ON families(code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_family_uuid ON families(uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_family_surname_city ON families(surname, city)")
    
    def _normalize_for_code(self, text: str) -> str:
        """
        Normalize text for use in family code.
        
        - Removes special characters
        - Converts to uppercase
        - Pads short names, truncates long names
        """
        if not text:
            return "UNK"
        clean = re.sub(r'[^A-Za-z]', '', text).upper()
        if len(clean) < 3:
            clean = clean + "X" * (3 - len(clean))
        return clean[:5]  # Max 5 chars
    
    def _get_next_sequence(self, surname_norm: str, city_norm: str) -> int:
        """Get next sequence number for surname-city combo."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT MAX(sequence) FROM families 
                WHERE surname = ? AND city = ?
            """, (surname_norm, city_norm)).fetchone()
            
            current_max = result[0] if result[0] else 0
            return current_max + 1
    
    def preview_code(self, surname: str, city: str) -> str:
        """
        Preview what code would be generated (doesn't save).
        
        Useful for UI confirmation before creating.
        """
        surname_norm = self._normalize_for_code(surname)
        city_norm = self._normalize_for_code(city)[:3]
        sequence = self._get_next_sequence(surname_norm, city_norm)
        return f"{surname_norm}-{city_norm}-{sequence:03d}"
    
    def create_family(
        self, 
        surname: str, 
        city: str, 
        description: str = ""
    ) -> Family:
        """
        Create a new family with auto-generated code.
        
        Args:
            surname: Family surname (e.g., "Sharma")
            city: City name (e.g., "Hyderabad")
            description: Optional description
            
        Returns:
            Family object with generated code and UUID
        """
        surname_norm = self._normalize_for_code(surname)
        city_norm = self._normalize_for_code(city)[:3]
        sequence = self._get_next_sequence(surname_norm, city_norm)
        
        family_uuid = str(uuid.uuid4())
        family_code = f"{surname_norm}-{city_norm}-{sequence:03d}"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO families (uuid, code, surname, city, sequence, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (family_uuid, family_code, surname_norm, city_norm, sequence, description))
            
            return Family(
                id=cursor.lastrowid,
                uuid=family_uuid,
                code=family_code,
                surname=surname,
                city=city,
                description=description
            )
    
    def get_by_id(self, family_id: int) -> Optional[Family]:
        """Get family by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM families WHERE id = ? AND is_archived = 0", 
                (family_id,)
            ).fetchone()
            return self._row_to_family(row) if row else None
    
    def get_by_code(self, code: str) -> Optional[Family]:
        """Get family by code (e.g., SHARMA-HYD-001)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM families WHERE code = ? AND is_archived = 0", 
                (code.upper(),)
            ).fetchone()
            return self._row_to_family(row) if row else None
    
    def get_by_uuid(self, family_uuid: str) -> Optional[Family]:
        """Get family by UUID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM families WHERE uuid = ? AND is_archived = 0", 
                (family_uuid,)
            ).fetchone()
            return self._row_to_family(row) if row else None
    
    def find(
        self, 
        surname: str = None, 
        city: str = None,
        include_archived: bool = False
    ) -> List[Family]:
        """
        Search families by surname and/or city.
        
        Args:
            surname: Filter by surname (partial match)
            city: Filter by city (partial match)
            include_archived: Include archived families
            
        Returns:
            List of matching Family objects
        """
        conditions = []
        params = []
        
        if not include_archived:
            conditions.append("is_archived = 0")
        
        if surname:
            surname_norm = self._normalize_for_code(surname)
            conditions.append("surname LIKE ?")
            params.append(f"%{surname_norm}%")
        
        if city:
            city_norm = self._normalize_for_code(city)[:3]
            conditions.append("city LIKE ?")
            params.append(f"%{city_norm}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM families WHERE {where_clause} ORDER BY code",
                params
            ).fetchall()
            return [self._row_to_family(row) for row in rows]
    
    def get_all(self, include_archived: bool = False) -> List[Family]:
        """Get all families."""
        return self.find(include_archived=include_archived)
    
    def update(self, family_id: int, description: str) -> bool:
        """Update family description."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE families SET description = ? WHERE id = ?",
                (description, family_id)
            )
            return cursor.rowcount > 0
    
    def archive(self, family_id: int) -> bool:
        """Archive a family (soft delete)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE families SET is_archived = 1 WHERE id = ?",
                (family_id,)
            )
            return cursor.rowcount > 0
    
    def delete(self, family_id: int) -> bool:
        """
        Permanently delete a family.
        
        WARNING: This will break foreign key references in profiles.
        Use archive() for soft delete instead.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM families WHERE id = ?",
                (family_id,)
            )
            return cursor.rowcount > 0
    
    def _row_to_family(self, row) -> Family:
        """Convert database row to Family object."""
        return Family(
            id=row["id"],
            uuid=row["uuid"],
            code=row["code"],
            surname=row["surname"],
            city=row["city"],
            description=row["description"] or "",
            is_archived=bool(row["is_archived"]),
            created_at=row["created_at"]
        )
