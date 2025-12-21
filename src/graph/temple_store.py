"""
Temple Store - SQLite storage for temples and temple-follower relationships.

This is a DATA LAYER component:
- Handles database operations for temples and temple_followers tables
- NO business logic (agents decide coordination between stores)
- Manages many-to-many relationships between temples and persons

Database: Shares crm_v2.db with CRMStoreV2 for referential integrity.

Tables:
- temples: Temple/spiritual center records
- temple_followers: Many-to-many relationship between temples and persons

Author: Shrinivas Deshpande
Date: December 20, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from src.graph.models_v2 import Temple, TempleFollower


# Shared database path - same DB as CRMStoreV2
DEFAULT_DB_PATH = "data/crm/crm_v2.db"


class TempleStore:
    """Storage for temples and temple-follower relationships."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize temples and temple_followers tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Temples table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS temples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,

                    name TEXT NOT NULL,
                    deity TEXT,
                    temple_type TEXT,

                    address TEXT,
                    city TEXT,
                    state TEXT,
                    country TEXT,
                    pincode TEXT,

                    phone TEXT,
                    email TEXT,
                    website TEXT,

                    established_year INTEGER,
                    description TEXT,
                    facilities TEXT,
                    timings TEXT,

                    notes TEXT,
                    is_archived INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Temple followers (many-to-many relationship)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS temple_followers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    temple_id INTEGER NOT NULL,
                    person_id INTEGER NOT NULL,

                    relationship_type TEXT,
                    since_year INTEGER,
                    role TEXT,

                    frequency TEXT,
                    activities TEXT,

                    notes TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (temple_id) REFERENCES temples(id) ON DELETE CASCADE,
                    FOREIGN KEY (person_id) REFERENCES profiles(id) ON DELETE CASCADE,
                    UNIQUE(temple_id, person_id)
                )
            """)

            # Indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_temples_city ON temples(city)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_temples_deity ON temples(deity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_temples_type ON temples(temple_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_temple_followers_temple ON temple_followers(temple_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_temple_followers_person ON temple_followers(person_id)")

    # =========================================================================
    # TEMPLE OPERATIONS (CRUD)
    # =========================================================================

    def add_temple(self, temple: Temple) -> int:
        """
        Add a new temple.

        Returns: ID of created temple
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO temples (
                    uuid, name, deity, temple_type,
                    address, city, state, country, pincode,
                    phone, email, website,
                    established_year, description, facilities, timings,
                    notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                temple.uuid, temple.name, temple.deity, temple.temple_type,
                temple.address, temple.city, temple.state, temple.country, temple.pincode,
                temple.phone, temple.email, temple.website,
                temple.established_year, temple.description, temple.facilities, temple.timings,
                temple.notes
            ))
            return cursor.lastrowid

    def get_temple(self, temple_id: int) -> Optional[Temple]:
        """Get temple by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM temples WHERE id = ?",
                (temple_id,)
            ).fetchone()
            return self._row_to_temple(row) if row else None

    def update_temple(self, temple_id: int, **kwargs) -> bool:
        """
        Update temple fields.

        Args:
            temple_id: ID of temple to update
            **kwargs: Fields to update (e.g., phone="123", city="Mumbai")

        Returns: True if updated
        """
        if not kwargs:
            return False

        kwargs['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [temple_id]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE temples SET {set_clause} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0

    def delete_temple(self, temple_id: int) -> bool:
        """
        Delete temple and its followers.

        Returns: True if deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            # Followers deleted via CASCADE, but explicit for clarity
            conn.execute("DELETE FROM temple_followers WHERE temple_id = ?", (temple_id,))
            cursor = conn.execute("DELETE FROM temples WHERE id = ?", (temple_id,))
            return cursor.rowcount > 0

    def archive_temple(self, temple_id: int) -> bool:
        """Soft delete - set is_archived = 1."""
        return self.update_temple(temple_id, is_archived=1)

    def unarchive_temple(self, temple_id: int) -> bool:
        """Restore archived temple."""
        return self.update_temple(temple_id, is_archived=0)

    # =========================================================================
    # TEMPLE QUERIES
    # =========================================================================

    def get_all_temples(self, include_archived: bool = False) -> List[Temple]:
        """Get all temples."""
        where = "1=1" if include_archived else "is_archived = 0"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM temples WHERE {where} ORDER BY name"
            ).fetchall()
            return [self._row_to_temple(row) for row in rows]

    def search_temples(
        self,
        query: str = None,
        city: str = None,
        deity: str = None,
        temple_type: str = None,
        include_archived: bool = False
    ) -> List[Temple]:
        """
        Search temples with filters.

        Args:
            query: Search in name, description
            city: Partial match on city
            deity: Partial match on deity
            temple_type: Exact match on temple_type
            include_archived: Include archived temples

        Returns: List of matching temples
        """
        conditions = []
        params = []

        if not include_archived:
            conditions.append("is_archived = 0")

        if query:
            conditions.append("(name LIKE ? OR description LIKE ?)")
            params.extend([f"%{query}%"] * 2)

        if city:
            conditions.append("city LIKE ?")
            params.append(f"%{city}%")

        if deity:
            conditions.append("deity LIKE ?")
            params.append(f"%{deity}%")

        if temple_type:
            conditions.append("temple_type = ?")
            params.append(temple_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM temples WHERE {where_clause} ORDER BY name",
                params
            ).fetchall()
            return [self._row_to_temple(row) for row in rows]

    def get_temples_by_city(self, city: str) -> List[Temple]:
        """Get all temples in a city."""
        return self.search_temples(city=city)

    def get_temples_by_deity(self, deity: str) -> List[Temple]:
        """Get all temples for a deity."""
        return self.search_temples(deity=deity)

    def get_cities(self) -> List[str]:
        """Get distinct cities (for dropdowns)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT DISTINCT city FROM temples
                WHERE city IS NOT NULL AND city != '' AND is_archived = 0
                ORDER BY city
            """).fetchall()
            return [row[0] for row in rows]

    def get_deities(self) -> List[str]:
        """Get distinct deities (for dropdowns)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT DISTINCT deity FROM temples
                WHERE deity IS NOT NULL AND deity != '' AND is_archived = 0
                ORDER BY deity
            """).fetchall()
            return [row[0] for row in rows]

    # =========================================================================
    # TEMPLE FOLLOWER OPERATIONS (CRUD)
    # =========================================================================

    def add_follower(self, follower: TempleFollower) -> int:
        """
        Add a follower relationship.

        Returns: ID of created relationship
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO temple_followers (
                    temple_id, person_id, relationship_type, since_year, role,
                    frequency, activities, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                follower.temple_id, follower.person_id, follower.relationship_type,
                follower.since_year, follower.role, follower.frequency,
                follower.activities, follower.notes
            ))
            return cursor.lastrowid

    def get_follower(self, follower_id: int) -> Optional[TempleFollower]:
        """Get follower relationship by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM temple_followers WHERE id = ?",
                (follower_id,)
            ).fetchone()
            return self._row_to_follower(row) if row else None

    def update_follower(self, follower_id: int, **kwargs) -> bool:
        """Update follower relationship fields."""
        if not kwargs:
            return False

        kwargs['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [follower_id]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE temple_followers SET {set_clause} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0

    def delete_follower(self, follower_id: int) -> bool:
        """Delete a follower relationship."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM temple_followers WHERE id = ?",
                (follower_id,)
            )
            return cursor.rowcount > 0

    def deactivate_follower(self, follower_id: int) -> bool:
        """Soft delete - set is_active = 0."""
        return self.update_follower(follower_id, is_active=0)

    def activate_follower(self, follower_id: int) -> bool:
        """Reactivate follower."""
        return self.update_follower(follower_id, is_active=1)

    # =========================================================================
    # TEMPLE FOLLOWER QUERIES
    # =========================================================================

    def get_temple_followers(self, temple_id: int, include_inactive: bool = False) -> List[dict]:
        """
        Get all followers of a temple with person details.

        Returns: List of dicts with follower and person info
        """
        where = "tf.temple_id = ?" if include_inactive else "tf.temple_id = ? AND tf.is_active = 1"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"""
                SELECT
                    tf.*,
                    p.first_name, p.last_name, p.family_code,
                    p.phone, p.email, p.city, p.state
                FROM temple_followers tf
                JOIN profiles p ON tf.person_id = p.id
                WHERE {where}
                ORDER BY p.first_name, p.last_name
            """, (temple_id,)).fetchall()

            return [{
                "follower": self._row_to_follower(row).to_dict(),
                "person_name": f"{row['first_name']} {row['last_name']}".strip(),
                "family_code": row['family_code'] or "",
                "phone": row['phone'] or "",
                "email": row['email'] or "",
                "location": f"{row['city']}, {row['state']}".strip(", ") if row['city'] or row['state'] else ""
            } for row in rows]

    def get_person_temples(self, person_id: int, include_inactive: bool = False) -> List[dict]:
        """
        Get all temples a person is associated with.

        Returns: List of dicts with temple and follower info
        """
        where = "tf.person_id = ?" if include_inactive else "tf.person_id = ? AND tf.is_active = 1"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"""
                SELECT
                    tf.*,
                    t.name, t.deity, t.city, t.state, t.temple_type
                FROM temple_followers tf
                JOIN temples t ON tf.temple_id = t.id
                WHERE {where}
                ORDER BY t.name
            """, (person_id,)).fetchall()

            return [{
                "follower": self._row_to_follower(row).to_dict(),
                "temple_name": row['name'],
                "deity": row['deity'] or "",
                "temple_type": row['temple_type'] or "",
                "location": f"{row['city']}, {row['state']}".strip(", ") if row['city'] or row['state'] else ""
            } for row in rows]

    def get_follower_by_temple_person(self, temple_id: int, person_id: int) -> Optional[TempleFollower]:
        """Get follower relationship by temple and person."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM temple_followers WHERE temple_id = ? AND person_id = ?",
                (temple_id, person_id)
            ).fetchone()
            return self._row_to_follower(row) if row else None

    def get_follower_count(self, temple_id: int) -> int:
        """Get count of active followers for a temple."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM temple_followers WHERE temple_id = ? AND is_active = 1",
                (temple_id,)
            ).fetchone()
            return row[0] if row else 0

    def get_temples_with_follower_counts(self, include_archived: bool = False) -> List[dict]:
        """Get all temples with their follower counts."""
        where = "1=1" if include_archived else "t.is_archived = 0"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"""
                SELECT
                    t.*,
                    COUNT(CASE WHEN tf.is_active = 1 THEN 1 END) as follower_count
                FROM temples t
                LEFT JOIN temple_followers tf ON t.id = tf.temple_id
                WHERE {where}
                GROUP BY t.id
                ORDER BY t.name
            """).fetchall()

            return [{
                "temple": self._row_to_temple(row).to_dict(),
                "follower_count": row['follower_count']
            } for row in rows]

    # =========================================================================
    # TEMPLE DONATION OPERATIONS (CRUD)
    # =========================================================================

    def add_donation(self, donation) -> int:
        """
        Add a temple donation.

        Args:
            donation: Donation object with temple_id set

        Returns: ID of created donation
        """
        from src.graph.models_v2 import Donation

        # Auto-generate receipt number if not provided
        if not donation.receipt_number:
            with sqlite3.connect(self.db_path) as conn:
                # Get temple info for receipt prefix
                temple = self.get_temple(donation.temple_id) if donation.temple_id else None
                temple_prefix = temple.name[:3].upper() if temple else "GEN"

                # Get count of temple donations for sequence number
                count = conn.execute(
                    "SELECT COUNT(*) FROM donations WHERE temple_id = ?",
                    (donation.temple_id,)
                ).fetchone()[0]

                # Format: TEMPLECODE-YYYYMMDD-NNNN
                from datetime import datetime
                date_str = datetime.now().strftime("%Y%m%d")
                donation.receipt_number = f"{temple_prefix}-{date_str}-{count+1:04d}"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO donations (
                    person_id, temple_id, amount, currency, cause, deity,
                    donation_date, payment_method, receipt_number, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                donation.person_id, donation.temple_id, donation.amount, donation.currency,
                donation.cause, donation.deity, donation.donation_date, donation.payment_method,
                donation.receipt_number, donation.notes
            ))
            return cursor.lastrowid

    def get_temple_donations(
        self,
        temple_id: int,
        offset: int = 0,
        limit: int = 15,
        search_query: str = None
    ) -> dict:
        """
        Get donations for a temple with pagination and search.

        Args:
            temple_id: Temple ID
            offset: Starting position (for pagination)
            limit: Number of results per page
            search_query: Search by person name, phone, email, or city (wildcard)

        Returns: dict with 'donations' list, 'total' count, 'page', 'total_pages'
        """
        conditions = ["d.temple_id = ?"]
        params = [temple_id]

        if search_query:
            conditions.append("""(
                p.first_name LIKE ? OR
                p.last_name LIKE ? OR
                p.phone LIKE ? OR
                p.email LIKE ? OR
                p.city LIKE ?
            )""")
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern] * 5)

        where_clause = " AND ".join(conditions)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get total count
            count_query = f"""
                SELECT COUNT(*) FROM donations d
                JOIN profiles p ON d.person_id = p.id
                WHERE {where_clause}
            """
            total = conn.execute(count_query, params).fetchone()[0]

            # Get paginated results
            data_query = f"""
                SELECT
                    d.*,
                    p.first_name, p.last_name, p.phone, p.email, p.city, p.state
                FROM donations d
                JOIN profiles p ON d.person_id = p.id
                WHERE {where_clause}
                ORDER BY d.donation_date DESC, d.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(data_query, params + [limit, offset]).fetchall()

            donations = []
            for row in rows:
                donations.append({
                    "id": row["id"],
                    "person_id": row["person_id"],
                    "person_name": f"{row['first_name']} {row['last_name']}".strip(),
                    "phone": row["phone"] or "",
                    "email": row["email"] or "",
                    "city": row["city"] or "",
                    "state": row["state"] or "",
                    "amount": row["amount"],
                    "currency": row["currency"],
                    "cause": row["cause"] or "",
                    "deity": row["deity"] or "",
                    "donation_date": row["donation_date"] or "",
                    "payment_method": row["payment_method"] or "",
                    "receipt_number": row["receipt_number"] or "",
                    "notes": row["notes"] or "",
                    "created_at": row["created_at"] or ""
                })

            return {
                "donations": donations,
                "total": total,
                "page": (offset // limit) + 1 if limit > 0 else 1,
                "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
                "limit": limit
            }

    def get_person_temple_donations(self, person_id: int) -> List[dict]:
        """
        Get all temple donations made by a person.

        Returns: List of dicts with donation and temple info
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT
                    d.*,
                    t.name as temple_name, t.city as temple_city, t.state as temple_state
                FROM donations d
                LEFT JOIN temples t ON d.temple_id = t.id
                WHERE d.person_id = ?
                ORDER BY d.donation_date DESC, d.created_at DESC
            """, (person_id,)).fetchall()

            return [{
                "donation_id": row["id"],
                "temple_id": row["temple_id"],
                "temple_name": row["temple_name"] or "General Donation",
                "temple_location": f"{row['temple_city']}, {row['temple_state']}".strip(", ") if row["temple_city"] or row["temple_state"] else "",
                "amount": row["amount"],
                "currency": row["currency"],
                "cause": row["cause"] or "",
                "deity": row["deity"] or "",
                "donation_date": row["donation_date"] or "",
                "payment_method": row["payment_method"] or "",
                "receipt_number": row["receipt_number"] or "",
                "notes": row["notes"] or ""
            } for row in rows]

    def get_temple_donation_stats(self, temple_id: int) -> dict:
        """Get donation statistics for a temple."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_donations,
                    COALESCE(SUM(amount), 0) as total_amount,
                    COALESCE(AVG(amount), 0) as avg_amount,
                    COUNT(DISTINCT person_id) as unique_donors
                FROM donations
                WHERE temple_id = ?
            """, (temple_id,)).fetchone()

            return {
                "total_donations": row[0],
                "total_amount": row[1],
                "avg_amount": row[2],
                "unique_donors": row[3]
            }

    def search_all_donations(
        self,
        search_query: str = None,
        temple_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 15
    ) -> dict:
        """
        Search donations across all temples with wildcard support.

        Args:
            search_query: Search by person name, phone, email, or city
            temple_id: Filter by specific temple (optional)
            offset: Starting position
            limit: Results per page

        Returns: Paginated results with donations
        """
        conditions = []
        params = []

        if temple_id:
            conditions.append("d.temple_id = ?")
            params.append(temple_id)

        if search_query:
            conditions.append("""(
                p.first_name LIKE ? OR
                p.last_name LIKE ? OR
                p.phone LIKE ? OR
                p.email LIKE ? OR
                p.city LIKE ? OR
                t.name LIKE ?
            )""")
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern] * 6)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Count total
            count_query = f"""
                SELECT COUNT(*) FROM donations d
                JOIN profiles p ON d.person_id = p.id
                LEFT JOIN temples t ON d.temple_id = t.id
                WHERE {where_clause}
            """
            total = conn.execute(count_query, params).fetchone()[0]

            # Get data
            data_query = f"""
                SELECT
                    d.*,
                    p.first_name, p.last_name, p.phone, p.email, p.city, p.state,
                    t.name as temple_name
                FROM donations d
                JOIN profiles p ON d.person_id = p.id
                LEFT JOIN temples t ON d.temple_id = t.id
                WHERE {where_clause}
                ORDER BY d.donation_date DESC, d.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(data_query, params + [limit, offset]).fetchall()

            donations = []
            for row in rows:
                donations.append({
                    "id": row["id"],
                    "person_name": f"{row['first_name']} {row['last_name']}".strip(),
                    "phone": row["phone"] or "",
                    "email": row["email"] or "",
                    "city": row["city"] or "",
                    "temple_name": row["temple_name"] or "General",
                    "amount": row["amount"],
                    "currency": row["currency"],
                    "donation_date": row["donation_date"] or "",
                    "receipt_number": row["receipt_number"] or "",
                    "cause": row["cause"] or ""
                })

            return {
                "donations": donations,
                "total": total,
                "page": (offset // limit) + 1 if limit > 0 else 1,
                "total_pages": (total + limit - 1) // limit if limit > 0 else 1
            }

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _row_to_temple(self, row) -> Temple:
        """Convert database row to Temple."""
        return Temple(
            id=row["id"],
            uuid=row["uuid"],
            name=row["name"],
            deity=row["deity"] or "",
            temple_type=row["temple_type"] or "",
            address=row["address"] or "",
            city=row["city"] or "",
            state=row["state"] or "",
            country=row["country"] or "",
            pincode=row["pincode"] or "",
            phone=row["phone"] or "",
            email=row["email"] or "",
            website=row["website"] or "",
            established_year=row["established_year"],
            description=row["description"] or "",
            facilities=row["facilities"] or "",
            timings=row["timings"] or "",
            notes=row["notes"] or "",
            is_archived=bool(row["is_archived"]),
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or ""
        )

    def _row_to_follower(self, row) -> TempleFollower:
        """Convert database row to TempleFollower."""
        return TempleFollower(
            id=row["id"],
            temple_id=row["temple_id"],
            person_id=row["person_id"],
            relationship_type=row["relationship_type"] or "",
            since_year=row["since_year"],
            role=row["role"] or "",
            frequency=row["frequency"] or "",
            activities=row["activities"] or "",
            notes=row["notes"] or "",
            is_active=bool(row["is_active"]),
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or ""
        )
