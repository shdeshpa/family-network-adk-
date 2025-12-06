"""
Test script for CRM V2 data layer.

Tests:
1. FamilyRegistry - code generation, CRUD
2. CRMStoreV2 - profiles and donations
3. Integration - family + profiles together

Run from project root:
    PYTHONPATH=. uv run python tests/test_crm_v2.py
"""

import tempfile
import os
from pathlib import Path

# Test results tracking
passed = 0
failed = 0


def test(name: str, condition: bool, detail: str = ""):
    """Simple test helper."""
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name} - {detail}")
        failed += 1


def test_family_registry():
    """Test FamilyRegistry operations."""
    print("\n📁 Testing FamilyRegistry...")
    
    from src.graph.family_registry import FamilyRegistry
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.db"
        registry = FamilyRegistry(db_path)
        
        # Test 1: Create family
        family1 = registry.create_family("Sharma", "Hyderabad")
        test("Create family", family1.id is not None, f"id={family1.id}")
        test("Family code format", family1.code == "SHARM-HYD-001", f"got {family1.code}")
        test("Family has UUID", len(family1.uuid) == 36, f"uuid={family1.uuid}")
        
        # Test 2: Second family same surname/city gets sequence 002
        family2 = registry.create_family("Sharma", "Hyderabad")
        test("Second family sequence", family2.code == "SHARM-HYD-002", f"got {family2.code}")
        
        # Test 3: Different city resets sequence
        family3 = registry.create_family("Sharma", "Mumbai")
        test("Different city resets seq", family3.code == "SHARM-MUM-001", f"got {family3.code}")
        
        # Test 4: Different surname
        family4 = registry.create_family("Patel", "Mumbai")
        test("Different surname", family4.code == "PATEL-MUM-001", f"got {family4.code}")
        
        # Test 5: Get by code
        found = registry.get_by_code("SHARM-HYD-001")
        test("Get by code", found is not None and found.id == family1.id)
        
        # Test 6: Get by UUID
        found = registry.get_by_uuid(family1.uuid)
        test("Get by UUID", found is not None and found.code == family1.code)
        
        # Test 7: Find by surname
        results = registry.find(surname="Sharma")
        test("Find by surname", len(results) == 3, f"found {len(results)}")
        
        # Test 8: Find by city
        results = registry.find(city="Mumbai")
        test("Find by city", len(results) == 2, f"found {len(results)}")
        
        # Test 9: Get all
        all_families = registry.get_all()
        test("Get all families", len(all_families) == 4, f"found {len(all_families)}")
        
        # Test 10: Archive
        archived = registry.archive(family1.id)
        test("Archive family", archived)
        all_active = registry.get_all(include_archived=False)
        test("Archived excluded", len(all_active) == 3)
        
        # Test 11: Preview code (doesn't create)
        preview = registry.preview_code("NewFamily", "Delhi")
        test("Preview code", preview == "NEWFA-DEL-001", f"got {preview}")
        # Verify it wasn't created
        all_families = registry.get_all()
        test("Preview didn't create", len(all_families) == 3)
        
        # Test 12: Short surname padding
        family_short = registry.create_family("Li", "Beijing")
        test("Short name padded", family_short.code == "LIX-BEI-001", f"got {family_short.code}")
        
        # Test 13: to_dict
        d = family1.to_dict()
        test("to_dict has keys", "code" in d and "uuid" in d and "id" in d)


def test_crm_store():
    """Test CRMStoreV2 operations."""
    print("\n👤 Testing CRMStoreV2...")
    
    from src.graph.crm_store_v2 import CRMStoreV2
    from src.graph.models_v2 import PersonProfileV2, Donation
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.db"
        store = CRMStoreV2(db_path)
        
        # Test 1: Add person
        person1 = PersonProfileV2(
            first_name="Ramesh",
            last_name="Sharma",
            gender="M",
            birth_year=1980,
            occupation="Engineer",
            phone="9876543210",
            city="Hyderabad",
            family_code="SHARM-HYD-001"
        )
        person1_id = store.add_person(person1)
        test("Add person", person1_id > 0, f"id={person1_id}")
        
        # Test 2: Get person
        found = store.get_person(person1_id)
        test("Get person", found is not None)
        test("Person name correct", found.full_name == "Ramesh Sharma")
        test("Person age calculated", found.approximate_age == 2025 - 1980, f"age={found.approximate_age}")
        
        # Test 3: Update person
        updated = store.update_person(person1_id, phone="1234567890", occupation="Senior Engineer")
        test("Update person", updated)
        found = store.get_person(person1_id)
        test("Phone updated", found.phone == "1234567890")
        test("Occupation updated", found.occupation == "Senior Engineer")
        
        # Test 4: Add second person same family
        person2 = PersonProfileV2(
            first_name="Priya",
            last_name="Sharma",
            gender="F",
            birth_year=1985,
            city="Hyderabad",
            family_code="SHARM-HYD-001"
        )
        person2_id = store.add_person(person2)
        test("Add second person", person2_id > 0)
        
        # Test 5: Add person different family
        person3 = PersonProfileV2(
            first_name="Amit",
            last_name="Patel",
            gender="M",
            city="Mumbai",
            family_code="PATEL-MUM-001"
        )
        person3_id = store.add_person(person3)
        
        # Test 6: Get all
        all_persons = store.get_all()
        test("Get all persons", len(all_persons) == 3, f"found {len(all_persons)}")
        
        # Test 7: Search by query
        results = store.search(query="Sharma")
        test("Search by name", len(results) == 2, f"found {len(results)}")
        
        # Test 8: Search by family code
        results = store.get_by_family("SHARM-HYD-001")
        test("Get by family", len(results) == 2, f"found {len(results)}")
        
        # Test 9: Search by city
        results = store.search(city="Mumbai")
        test("Search by city", len(results) == 1)
        
        # Test 10: Get family codes
        codes = store.get_family_codes()
        test("Get family codes", len(codes) == 2, f"codes={codes}")
        
        # Test 11: Add donation
        donation1 = Donation(
            person_id=person1_id,
            amount=5000.00,
            currency="INR",
            cause="Temple Construction",
            deity="Lord Ganesha",
            donation_date="2024-01-15",
            payment_method="upi"
        )
        donation1_id = store.add_donation(donation1)
        test("Add donation", donation1_id > 0)
        
        # Test 12: Add second donation
        donation2 = Donation(
            person_id=person1_id,
            amount=100.00,
            currency="USD",
            cause="Education Fund",
            deity="Goddess Saraswati",
            donation_date="2024-06-01",
            payment_method="card"
        )
        donation2_id = store.add_donation(donation2)
        
        # Test 13: Get donations for person
        donations = store.get_donations_for_person(person1_id)
        test("Get donations for person", len(donations) == 2, f"found {len(donations)}")
        
        # Test 14: Get donation summary
        summary = store.get_donation_summary(person1_id)
        test("Donation summary count", summary["total_count"] == 2)
        test("Donation summary by currency", "INR" in summary["by_currency"] and "USD" in summary["by_currency"])
        
        # Test 15: Get donations by cause
        results = store.get_donations_by_cause("Temple")
        test("Get by cause", len(results) == 1)
        test("Cause result has person", results[0]["person_name"] == "Ramesh Sharma")
        
        # Test 16: Update donation
        updated = store.update_donation(donation1_id, amount=6000.00)
        test("Update donation", updated)
        d = store.get_donation(donation1_id)
        test("Donation amount updated", d.amount == 6000.00)
        
        # Test 17: Delete donation
        deleted = store.delete_donation(donation2_id)
        test("Delete donation", deleted)
        donations = store.get_donations_for_person(person1_id)
        test("Donation removed", len(donations) == 1)
        
        # Test 18: Archive person
        archived = store.archive_person(person3_id)
        test("Archive person", archived)
        all_active = store.get_all(include_archived=False)
        test("Archived excluded", len(all_active) == 2)
        
        # Test 19: Delete person (cascades donations)
        deleted = store.delete_person(person1_id)
        test("Delete person", deleted)
        donations = store.get_donations_for_person(person1_id)
        test("Donations cascaded", len(donations) == 0)
        
        # Test 20: to_dict
        found = store.get_person(person2_id)
        d = found.to_dict()
        test("Profile to_dict", "full_name" in d and "family_code" in d)


def test_integration():
    """Test FamilyRegistry + CRMStoreV2 together."""
    print("\n🔗 Testing Integration...")
    
    from src.graph.family_registry import FamilyRegistry
    from src.graph.crm_store_v2 import CRMStoreV2
    from src.graph.models_v2 import PersonProfileV2
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.db"
        
        # Both use same database
        registry = FamilyRegistry(db_path)
        store = CRMStoreV2(db_path)
        
        # Create family first
        family = registry.create_family("Reddy", "Chennai")
        test("Create family", family.code == "REDDY-CHE-001")
        
        # Add person with family info
        person = PersonProfileV2(
            first_name="Venkat",
            last_name="Reddy",
            family_id=family.id,
            family_uuid=family.uuid,
            family_code=family.code,
            city="Chennai"
        )
        person_id = store.add_person(person)
        test("Add person with family", person_id > 0)
        
        # Verify linkage
        found = store.get_person(person_id)
        test("Family ID linked", found.family_id == family.id)
        test("Family code linked", found.family_code == family.code)
        
        # Query by family
        members = store.get_by_family(family.code)
        test("Query by family code", len(members) == 1)
        
        # Verify same DB - family table exists in store's connection
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            test("Shared DB has families", "families" in table_names)
            test("Shared DB has profiles", "profiles" in table_names)
            test("Shared DB has donations", "donations" in table_names)


def main():
    """Run all tests."""
    print("=" * 60)
    print("CRM V2 Data Layer Tests")
    print("=" * 60)
    
    try:
        test_family_registry()
        test_crm_store()
        test_integration()
    except Exception as e:
        print(f"\n�� Error during tests: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
