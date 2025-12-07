"""Check what's actually in the CRM V2 database."""

import sqlite3
from pathlib import Path

db_path = Path("data") / "crm" / "crm_v2.db"

if not db_path.exists():
    print(f"Database not found at: {db_path}")
    exit(1)

print(f"Checking database: {db_path}")
print("=" * 80)

with sqlite3.connect(db_path) as conn:
    conn.row_factory = sqlite3.Row

    # Get all persons
    cursor = conn.execute("SELECT * FROM profiles WHERE first_name LIKE '%Rajesh%' OR last_name LIKE '%Kumar%'")
    rows = cursor.fetchall()

    if not rows:
        print("No persons named Rajesh Kumar found in database")
    else:
        for row in rows:
            print(f"\nPerson ID: {row['id']}")
            print(f"Name: {row['first_name']} {row['last_name']}")
            print(f"Gender: {row['gender']}")
            print(f"City: {row['city']}")
            print(f"Phone: {row['phone']}")  # CHECK THIS
            print(f"Email: {row['email']}")  # CHECK THIS
            print(f"Hobbies: {row['hobbies']}")  # CHECK THIS
            print(f"Religious Interests: {row['religious_interests']}")
            print(f"Notes: {row['notes'][:100] if row['notes'] else 'None'}")
            print("-" * 80)
