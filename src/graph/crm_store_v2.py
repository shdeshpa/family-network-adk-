"""
CRM Store V2 - SQLite storage for profiles and donations.

This is a DATA LAYER component:
- Handles database operations for profiles and donations tables
- NO business logic (agents decide coordination between stores)
- Used by crm_server.py MCP tools

Database: Shares crm_v2.db with FamilyRegistry for referential integrity.

Tables:
- profiles: Person records with family linkage
- donations: Donation records linked to persons
"""

import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from src.graph.models_v2 import PersonProfileV2, Donation


# Shared database path - same DB as FamilyRegistry
DEFAULT_DB_PATH = "data/crm/crm_v2.db"


class CRMStoreV2:
    """Storage for person profiles and donations."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize profiles and donations tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Profiles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id INTEGER,
                    family_uuid TEXT,
                    family_code TEXT,
                    
                    first_name TEXT NOT NULL,
                    last_name TEXT,
                    gender TEXT,
                    birth_year INTEGER,
                    occupation TEXT,
                    
                    phone TEXT,
                    email TEXT,
                    preferred_currency TEXT DEFAULT 'USD',
                    
                    city TEXT,
                    state TEXT,
                    country TEXT,
                    
                    gothra TEXT,
                    nakshatra TEXT,
                    
                    religious_interests TEXT,
                    spiritual_interests TEXT,
                    social_interests TEXT,
                    hobbies TEXT,
                    
                    notes TEXT,
                    is_archived INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (family_id) REFERENCES families(id)
                )
            """)
            
            # Donations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS donations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    cause TEXT,
                    deity TEXT,
                    
                    donation_date TEXT,
                    payment_method TEXT,
                    receipt_number TEXT,
                    
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (person_id) REFERENCES profiles(id) ON DELETE CASCADE
                )
            """)
            
            # Relationships table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person1_id INTEGER NOT NULL,
                    person2_id INTEGER NOT NULL,
                    relation_type TEXT NOT NULL,
                    relation_term TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (person1_id) REFERENCES profiles(id) ON DELETE CASCADE,
                    FOREIGN KEY (person2_id) REFERENCES profiles(id) ON DELETE CASCADE
                )
            """)

            # Indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_profile_family_id ON profiles(family_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_profile_family_code ON profiles(family_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_profile_name ON profiles(last_name, first_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_profile_city ON profiles(city)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_profile_occupation ON profiles(occupation)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_donation_person ON donations(person_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_donation_cause ON donations(cause)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_donation_deity ON donations(deity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relationship_person1 ON relationships(person1_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relationship_person2 ON relationships(person2_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relationship_type ON relationships(relation_type)")
    
    # =========================================================================
    # PROFILE OPERATIONS (CRUD)
    # =========================================================================
    
    def add_person(self, profile: PersonProfileV2) -> int:
        """
        Add a new person profile.
        
        Returns: ID of created profile
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO profiles (
                    family_id, family_uuid, family_code,
                    first_name, last_name, gender, birth_year, occupation,
                    phone, email, preferred_currency,
                    city, state, country,
                    gothra, nakshatra,
                    religious_interests, spiritual_interests, social_interests, hobbies,
                    notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.family_id, profile.family_uuid, profile.family_code,
                profile.first_name, profile.last_name, profile.gender,
                profile.birth_year, profile.occupation,
                profile.phone, profile.email, profile.preferred_currency,
                profile.city, profile.state, profile.country,
                profile.gothra, profile.nakshatra,
                profile.religious_interests, profile.spiritual_interests,
                profile.social_interests, profile.hobbies,
                profile.notes
            ))
            return cursor.lastrowid
    
    def get_person(self, person_id: int) -> Optional[PersonProfileV2]:
        """Get person by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM profiles WHERE id = ?",
                (person_id,)
            ).fetchone()
            return self._row_to_profile(row) if row else None
    
    def update_person(self, person_id: int, **kwargs) -> bool:
        """
        Update person fields.
        
        Args:
            person_id: ID of person to update
            **kwargs: Fields to update (e.g., phone="123", city="Mumbai")
            
        Returns: True if updated
        """
        if not kwargs:
            return False
        
        kwargs['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [person_id]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE profiles SET {set_clause} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0
    
    def delete_person(self, person_id: int) -> bool:
        """
        Delete person and their donations.
        
        Returns: True if deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            # Donations deleted via CASCADE, but explicit for clarity
            conn.execute("DELETE FROM donations WHERE person_id = ?", (person_id,))
            cursor = conn.execute("DELETE FROM profiles WHERE id = ?", (person_id,))
            return cursor.rowcount > 0
    
    def archive_person(self, person_id: int) -> bool:
        """Soft delete - set is_archived = 1."""
        return self.update_person(person_id, is_archived=1)
    
    def unarchive_person(self, person_id: int) -> bool:
        """Restore archived person."""
        return self.update_person(person_id, is_archived=0)
    
    # =========================================================================
    # PROFILE QUERIES
    # =========================================================================
    
    def get_all(self, include_archived: bool = False) -> List[PersonProfileV2]:
        """Get all persons."""
        where = "1=1" if include_archived else "is_archived = 0"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM profiles WHERE {where} ORDER BY family_code, last_name, first_name"
            ).fetchall()
            return [self._row_to_profile(row) for row in rows]
    
    def search(
        self,
        query: str = None,
        family_code: str = None,
        city: str = None,
        occupation: str = None,
        gothra: str = None,
        include_archived: bool = False
    ) -> List[PersonProfileV2]:
        """
        Search persons with filters.
        
        Args:
            query: Search in name, notes, occupation
            family_code: Exact match on family code
            city: Partial match on city
            occupation: Partial match on occupation
            gothra: Partial match on gothra
            include_archived: Include archived profiles
            
        Returns: List of matching profiles
        """
        conditions = []
        params = []
        
        if not include_archived:
            conditions.append("is_archived = 0")
        
        if query:
            conditions.append("""
                (first_name LIKE ? OR last_name LIKE ? OR 
                 notes LIKE ? OR occupation LIKE ?)
            """)
            params.extend([f"%{query}%"] * 4)
        
        if family_code:
            conditions.append("family_code = ?")
            params.append(family_code.upper())
        
        if city:
            conditions.append("city LIKE ?")
            params.append(f"%{city}%")
        
        if occupation:
            conditions.append("occupation LIKE ?")
            params.append(f"%{occupation}%")
        
        if gothra:
            conditions.append("gothra LIKE ?")
            params.append(f"%{gothra}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM profiles WHERE {where_clause} ORDER BY family_code, last_name, first_name",
                params
            ).fetchall()
            return [self._row_to_profile(row) for row in rows]
    
    def get_by_family(self, family_code: str) -> List[PersonProfileV2]:
        """Get all persons in a family."""
        return self.search(family_code=family_code)
    
    def get_family_codes(self) -> List[str]:
        """Get distinct family codes (for dropdowns)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT DISTINCT family_code FROM profiles 
                WHERE family_code IS NOT NULL AND family_code != '' AND is_archived = 0
                ORDER BY family_code
            """).fetchall()
            return [row[0] for row in rows]
    
    # =========================================================================
    # DONATION OPERATIONS (CRUD)
    # =========================================================================
    
    def add_donation(self, donation: Donation) -> int:
        """
        Add a donation record.
        
        Returns: ID of created donation
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO donations (
                    person_id, amount, currency, cause, deity,
                    donation_date, payment_method, receipt_number, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                donation.person_id, donation.amount, donation.currency,
                donation.cause, donation.deity, donation.donation_date,
                donation.payment_method, donation.receipt_number, donation.notes
            ))
            return cursor.lastrowid
    
    def get_donation(self, donation_id: int) -> Optional[Donation]:
        """Get donation by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM donations WHERE id = ?",
                (donation_id,)
            ).fetchone()
            return self._row_to_donation(row) if row else None
    
    def update_donation(self, donation_id: int, **kwargs) -> bool:
        """Update donation fields."""
        if not kwargs:
            return False
        
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [donation_id]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE donations SET {set_clause} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0
    
    def delete_donation(self, donation_id: int) -> bool:
        """Delete a donation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM donations WHERE id = ?",
                (donation_id,)
            )
            return cursor.rowcount > 0
    
    # =========================================================================
    # DONATION QUERIES
    # =========================================================================
    
    def get_donations_for_person(self, person_id: int) -> List[Donation]:
        """Get all donations for a person."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM donations WHERE person_id = ? ORDER BY donation_date DESC",
                (person_id,)
            ).fetchall()
            return [self._row_to_donation(row) for row in rows]
    
    def get_donations_by_cause(self, cause: str) -> List[dict]:
        """Get donations by cause with person info."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT d.*, p.first_name, p.last_name, p.family_code
                FROM donations d
                JOIN profiles p ON d.person_id = p.id
                WHERE d.cause LIKE ?
                ORDER BY d.donation_date DESC
            """, (f"%{cause}%",)).fetchall()
            
            return [{
                "donation": self._row_to_donation(row).to_dict(),
                "person_name": f"{row['first_name']} {row['last_name']}".strip(),
                "family_code": row['family_code']
            } for row in rows]
    
    def get_donations_by_deity(self, deity: str) -> List[dict]:
        """Get donations by deity with person info."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT d.*, p.first_name, p.last_name, p.family_code
                FROM donations d
                JOIN profiles p ON d.person_id = p.id
                WHERE d.deity LIKE ?
                ORDER BY d.donation_date DESC
            """, (f"%{deity}%",)).fetchall()
            
            return [{
                "donation": self._row_to_donation(row).to_dict(),
                "person_name": f"{row['first_name']} {row['last_name']}".strip(),
                "family_code": row['family_code']
            } for row in rows]
    
    def get_donation_summary(self, person_id: int) -> dict:
        """Get donation summary for a person."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT currency, COUNT(*) as count, SUM(amount) as total
                FROM donations 
                WHERE person_id = ?
                GROUP BY currency
            """, (person_id,)).fetchall()
            
            if not rows:
                return {"total_count": 0, "by_currency": {}}
            
            by_currency = {row[0]: {"count": row[1], "total": row[2]} for row in rows}
            total_count = sum(c["count"] for c in by_currency.values())
            
            return {
                "total_count": total_count,
                "by_currency": by_currency
            }
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _row_to_profile(self, row) -> PersonProfileV2:
        """Convert database row to PersonProfileV2."""
        return PersonProfileV2(
            id=row["id"],
            family_id=row["family_id"],
            family_uuid=row["family_uuid"] or "",
            family_code=row["family_code"] or "",
            first_name=row["first_name"],
            last_name=row["last_name"] or "",
            gender=row["gender"] or "",
            birth_year=row["birth_year"],
            occupation=row["occupation"] or "",
            phone=row["phone"] or "",
            email=row["email"] or "",
            preferred_currency=row["preferred_currency"] or "USD",
            city=row["city"] or "",
            state=row["state"] or "",
            country=row["country"] or "",
            gothra=row["gothra"] or "",
            nakshatra=row["nakshatra"] or "",
            religious_interests=row["religious_interests"] or "",
            spiritual_interests=row["spiritual_interests"] or "",
            social_interests=row["social_interests"] or "",
            hobbies=row["hobbies"] or "",
            notes=row["notes"] or "",
            is_archived=bool(row["is_archived"]),
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or ""
        )
    
    def _row_to_donation(self, row) -> Donation:
        """Convert database row to Donation."""
        return Donation(
            id=row["id"],
            person_id=row["person_id"],
            amount=row["amount"],
            currency=row["currency"] or "USD",
            cause=row["cause"] or "",
            deity=row["deity"] or "",
            donation_date=row["donation_date"] or "",
            payment_method=row["payment_method"] or "",
            receipt_number=row["receipt_number"] or "",
            notes=row["notes"] or "",
            created_at=row["created_at"] or ""
        )

    def get_all_persons(self) -> List[PersonProfileV2]:
        """Get all persons from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM profiles WHERE is_archived = 0
                ORDER BY created_at DESC
            """)
            return [self._row_to_profile(row) for row in cursor.fetchall()]

    def search_persons(self, query: str = None, family_code: str = None) -> List[PersonProfileV2]:
        """Convenience method for UI - wraps search()."""
        return self.search(query=query, family_code=family_code)

    def get_donations(self, person_id: int) -> List[Donation]:
        """Convenience method for UI - wraps get_donations_for_person()."""
        return self.get_donations_for_person(person_id)

    # =========================================================================
    # RELATIONSHIP OPERATIONS
    # =========================================================================

    def add_relationship(self, person1_id: int, person2_id: int,
                        relation_type: str, relation_term: str = None,
                        notes: str = None) -> int:
        """
        Add a relationship between two persons.

        Args:
            person1_id: ID of first person
            person2_id: ID of second person
            relation_type: Type of relationship (spouse, parent_child, sibling)
            relation_term: Specific term (wife, husband, son, daughter, etc.)
            notes: Optional notes

        Returns: ID of created relationship
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO relationships (
                    person1_id, person2_id, relation_type, relation_term, notes
                ) VALUES (?, ?, ?, ?, ?)
            """, (person1_id, person2_id, relation_type, relation_term, notes))
            return cursor.lastrowid

    def get_relationships(self, person_id: int) -> List[dict]:
        """
        Get all relationships for a person.

        Returns: List of dicts with relationship info
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM relationships
                WHERE person1_id = ? OR person2_id = ?
            """, (person_id, person_id)).fetchall()

            return [dict(row) for row in rows]

    def get_children(self, person_id: int) -> List[int]:
        """Get IDs of all children of a person."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT person2_id FROM relationships
                WHERE person1_id = ? AND relation_type = 'parent_child'
            """, (person_id,)).fetchall()
            return [row[0] for row in rows]

    def get_spouses(self, person_id: int) -> List[int]:
        """Get IDs of all spouses of a person."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT person2_id FROM relationships
                WHERE person1_id = ? AND relation_type = 'spouse'
                UNION
                SELECT person1_id FROM relationships
                WHERE person2_id = ? AND relation_type = 'spouse'
            """, (person_id, person_id)).fetchall()
            return [row[0] for row in rows]

    def get_siblings(self, person_id: int) -> List[int]:
        """Get IDs of all siblings of a person."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT person2_id FROM relationships
                WHERE person1_id = ? AND relation_type = 'sibling'
                UNION
                SELECT person1_id FROM relationships
                WHERE person2_id = ? AND relation_type = 'sibling'
            """, (person_id, person_id)).fetchall()
            return [row[0] for row in rows]

    def delete_relationship(self, relationship_id: int) -> bool:
        """Delete a relationship."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM relationships WHERE id = ?", (relationship_id,))
            return True
