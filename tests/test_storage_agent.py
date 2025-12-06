"""Test storage agent with CRM MCP server."""

import asyncio
import sys
sys.path.insert(0, ".")

from src.agents.adk.storage_agent import StorageAgent, store_extraction


async def test_storage_agent():
    """Test storage agent with sample extraction data."""
    print("=" * 60)
    print("Testing Storage Agent")
    print("=" * 60)

    # Sample extraction data
    extraction = {
        "success": True,
        "persons": [
            {
                "name": "Raj Sharma",
                "gender": "M",
                "age": 45,
                "location": "Hyderabad",
                "occupation": "Engineer",
                "is_speaker": True,
                "raw_mentions": ["Raj", "Raj Sharma"]
            },
            {
                "name": "Priya Sharma",
                "gender": "F",
                "age": 42,
                "location": "Hyderabad",
                "occupation": "Teacher",
                "is_speaker": False,
                "raw_mentions": ["Priya", "my wife"]
            },
            {
                "name": "Amit Sharma",
                "gender": "M",
                "age": 20,
                "location": "Hyderabad",
                "occupation": "Student",
                "is_speaker": False,
                "raw_mentions": ["Amit", "my son"]
            },
            {
                "name": "Sarah Patel",
                "gender": "F",
                "age": 38,
                "location": "Mumbai",
                "occupation": "Doctor",
                "is_speaker": False,
                "raw_mentions": ["Sarah", "Dr. Patel"]
            }
        ],
        "relationships": [
            {
                "person1": "Raj Sharma",
                "person2": "Priya Sharma",
                "relation_term": "wife",
                "relation_type": "spouse"
            },
            {
                "person1": "Raj Sharma",
                "person2": "Amit Sharma",
                "relation_term": "son",
                "relation_type": "parent_child"
            }
        ]
    }

    print("\n📥 Input Extraction Data:")
    print(f"  - Persons: {len(extraction['persons'])}")
    print(f"  - Relationships: {len(extraction['relationships'])}")

    print("\n🔄 Processing through Storage Agent...")

    try:
        # Test storage agent
        result = await store_extraction(extraction)

        print("\n✅ Storage Result:")
        print(f"  - Success: {result.success}")
        print(f"  - Families Created: {len(result.families_created)}")
        print(f"  - Persons Stored: {len(result.persons_created)}")
        print(f"  - Errors: {len(result.errors)}")
        print(f"  - Summary: {result.summary}")

        if result.families_created:
            print("\n👨‍👩‍👧‍👦 Families Created:")
            for family in result.families_created:
                print(f"  - {family.family_code} ({family.surname}, {family.city})")

        if result.persons_created:
            print("\n👤 Persons Stored:")
            for person in result.persons_created:
                status = "existing" if person.existing else "new"
                print(f"  - {person.name} (ID: {person.person_id}, {status}) → {person.family_code}")

        if result.errors:
            print("\n❌ Errors:")
            for error in result.errors:
                print(f"  - {error}")

        print("\n" + "=" * 60)
        print("✅ Test Completed Successfully")
        print("=" * 60)

        return result

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_orchestrator():
    """Test full orchestrator with storage agent."""
    print("\n" + "=" * 60)
    print("Testing Orchestrator with Storage Agent")
    print("=" * 60)

    from src.agents.adk.orchestrator import FamilyOrchestrator

    orchestrator = FamilyOrchestrator()

    test_text = """
    My name is Ramesh Kumar. I live in Bangalore.
    My wife is Lakshmi Kumar, she is a doctor.
    We have two children: Arun and Divya.
    """

    print(f"\n📝 Input Text:\n{test_text}")
    print("\n🔄 Processing through Orchestrator...")

    try:
        # Use async version since we're already in an event loop
        result = await orchestrator.process_text_async(test_text)

        print("\n✅ Orchestration Result:")
        print(f"  - Success: {result['success']}")
        print(f"  - Summary: {result['summary']}")

        print("\n📊 Pipeline Steps:")
        for step in result.get("steps", []):
            print(f"  - {step['agent']}: {step['status']}")

        if "storage" in result:
            storage = result["storage"]
            print("\n💾 Storage Details:")
            print(f"  - Families Created: {storage.get('families_created', 0)}")
            print(f"  - Persons Created: {storage.get('persons_created', 0)}")
            print(f"  - Summary: {storage.get('summary', 'N/A')}")

        print("\n" + "=" * 60)
        print("✅ Orchestrator Test Completed")
        print("=" * 60)

        return result

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n🧪 Storage Agent Test Suite\n")

    # Test 1: Direct storage agent
    print("Test 1: Direct Storage Agent")
    asyncio.run(test_storage_agent())

    # Test 2: Full orchestrator
    print("\n\nTest 2: Orchestrator with Storage")
    asyncio.run(test_orchestrator())
