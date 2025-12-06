"""
Test CRM MCP Server tools.

Tests the FastMCP tools that agents will call.
Verifies tool responses match expected format.

Run:
    PYTHONPATH=. uv run python tests/test_crm_mcp_server.py
"""

import tempfile
import os

# Redirect data to temp directory for testing
_tmpdir = tempfile.mkdtemp()
os.environ['CRM_DB_PATH'] = f"{_tmpdir}/test.db"

passed = 0
failed = 0


def test(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name} - {detail}")
        failed += 1


def test_family_tools():
    """Test family MCP tools."""
    print("\n👨‍👩‍👧 Testing Family Tools...")
    
    from src.mcp.servers.crm_server import (
        create_family, preview_family_code, get_family, 
        list_families, archive_family
    )
    
    # Test create_family
    result = create_family("Sharma", "Hyderabad", "Test family")
    test("create_family returns success", result["success"])
    test("create_family has family", "family" in result)
    test("family has code", result["family"]["code"] == "SHARM-HYD-001")
    family_id = result["family"]["id"]
    
    # Test preview_family_code
    result = preview_family_code("Patel", "Mumbai")
    test("preview returns code", result["preview_code"] == "PATEL-MUM-001")
    
    # Test get_family by code
    result = get_family(code="SHARM-HYD-001")
    test("get_family found", result["found"])
    test("get_family correct", result["family"]["id"] == family_id)
    
    # Test get_family not found
    result = get_family(code="NOTEXIST-XXX-999")
    test("get_family not found", not result["found"])
    
    # Test list_families
    create_family("Sharma", "Mumbai")
    create_family("Patel", "Delhi")
    result = list_families()
    test("list_families count", result["count"] == 3)
    
    # Test list with filter
    result = list_families(surname="Sharma")
    test("list filtered", result["count"] == 2)
    
    # Test archive
    result = archive_family(family_id)
    test("archive_family", result["success"])


def test_person_tools():
    """Test person MCP tools."""
    print("\n👤 Testing Person Tools...")
    
    from src.mcp.servers.crm_server import (
        add_person, get_person, update_person, 
        search_persons, list_persons, delete_person,
        get_family_codes, create_family
    )
    
    # Create family first
    family = create_family("Reddy", "Chennai")["family"]
    
    # Test add_person
    result = add_person(
        first_name="Venkat",
        last_name="Reddy",
        gender="M",
        birth_year=1975,
        occupation="Doctor",
        phone="9876543210",
        city="Chennai",
        family_id=family["id"],
        family_code=family["code"]
    )
    test("add_person success", result["success"])
    test("add_person has id", result["person_id"] > 0)
    person_id = result["person_id"]
    
    # Test add_person validation
    result = add_person(first_name="")
    test("add_person requires name", not result["success"])
    
    # Test get_person
    result = get_person(person_id)
    test("get_person found", result["found"])
    test("get_person name", result["person"]["full_name"] == "Venkat Reddy")
    test("get_person age", result["person"]["approximate_age"] == 2025 - 1975)
    
    # Test update_person
    result = update_person(person_id, phone="1111111111", occupation="Senior Doctor")
    test("update_person success", result["success"])
    test("update_person phone", result["person"]["phone"] == "1111111111")
    
    # Add second person
    add_person(first_name="Lakshmi", last_name="Reddy", city="Chennai", family_code=family["code"])
    
    # Test search_persons
    result = search_persons(query="Reddy")
    test("search by name", result["count"] == 2)
    
    result = search_persons(city="Chennai")
    test("search by city", result["count"] == 2)
    
    result = search_persons(family_code=family["code"])
    test("search by family", result["count"] == 2)
    
    # Test list_persons
    result = list_persons()
    test("list_persons", result["count"] >= 2)
    
    # Test get_family_codes
    result = get_family_codes()
    test("get_family_codes", family["code"] in result["codes"])
    
    # Test delete_person
    result = delete_person(person_id)
    test("delete_person", result["success"])
    result = get_person(person_id)
    test("person deleted", not result["found"])


def test_donation_tools():
    """Test donation MCP tools."""
    print("\n💰 Testing Donation Tools...")
    
    from src.mcp.servers.crm_server import (
        add_person, add_donation, get_donations,
        get_donation_summary, search_donations,
        update_donation, delete_donation
    )
    
    # Create person first
    person = add_person(first_name="Donor", last_name="Test")
    person_id = person["person_id"]
    
    # Test add_donation
    result = add_donation(
        person_id=person_id,
        amount=5000.00,
        currency="INR",
        cause="Temple Construction",
        deity="Lord Ganesha",
        donation_date="2024-01-15",
        payment_method="upi"
    )
    test("add_donation success", result["success"])
    test("add_donation has id", result["donation_id"] > 0)
    donation_id = result["donation_id"]
    
    # Test validation
    result = add_donation(person_id=person_id, amount=-100)
    test("donation requires positive amount", not result["success"])
    
    result = add_donation(person_id=99999, amount=100)
    test("donation requires valid person", not result["success"])
    
    # Add second donation
    add_donation(person_id=person_id, amount=100, currency="USD", cause="Education", deity="Goddess Saraswati")
    
    # Test get_donations
    result = get_donations(person_id)
    test("get_donations count", result["count"] == 2)
    
    # Test get_donation_summary
    result = get_donation_summary(person_id)
    test("summary has INR", "INR" in result["summary"]["by_currency"])
    test("summary has USD", "USD" in result["summary"]["by_currency"])
    
    # Test search_donations by cause
    result = search_donations(cause="Temple")
    test("search by cause", result["count"] >= 1)
    
    # Test search_donations by deity
    result = search_donations(deity="Ganesha")
    test("search by deity", result["count"] >= 1)
    
    # Test update_donation
    result = update_donation(donation_id, amount=6000.00)
    test("update_donation", result["success"])
    
    # Test delete_donation
    result = delete_donation(donation_id)
    test("delete_donation", result["success"])
    result = get_donations(person_id)
    test("donation deleted", result["count"] == 1)


def main():
    print("=" * 60)
    print("CRM MCP Server Tools Test")
    print("=" * 60)
    
    # Reset singletons for fresh test DB
    import src.mcp.servers.crm_server as server
    server._registry = None
    server._store = None
    
    try:
        test_family_tools()
        test_person_tools()
        test_donation_tools()
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    # Cleanup
    import shutil
    shutil.rmtree(_tmpdir, ignore_errors=True)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
