"""Simple test to verify storage agent works."""

import asyncio
import sys
sys.path.insert(0, ".")

from src.agents.adk.orchestrator import FamilyOrchestrator

async def main():
    print("=" * 60)
    print("SIMPLE STORAGE AGENT TEST")
    print("=" * 60)

    orchestrator = FamilyOrchestrator()

    test_text = """
    My name is Ramesh Kumar from Bangalore.
    I am an engineer. My wife Lakshmi Kumar is a doctor.
    We have two children: Arun and Divya.
    """

    print("\n📝 Input Text:")
    print(test_text)
    print("\n🔄 Processing...")

    try:
        # Use the async version
        result = await orchestrator.process_text_async(test_text)

        print("\n✅ Result:")
        print(f"Success: {result.get('success')}")
        print(f"Summary: {result.get('summary')}")

        # Show extraction
        ext = result.get("extraction", {})
        print(f"\n👥 Extraction:")
        print(f"  Persons: {len(ext.get('persons', []))}")
        for p in ext.get('persons', []):
            print(f"    - {p.get('name')} ({p.get('gender', '?')}, {p.get('location', '?')})")

        # Show storage
        storage = result.get("storage", {})
        if storage:
            print(f"\n💾 Storage:")
            print(f"  Summary: {storage.get('summary')}")
            print(f"  Families Created: {storage.get('families_created')}")
            print(f"  Persons Created: {storage.get('persons_created')}")
            if storage.get('errors'):
                print(f"  Errors: {storage.get('errors')}")

        print("\n" + "=" * 60)
        print("✅ TEST COMPLETE")
        print("=" * 60)

        # Now check database
        from src.graph.crm_store_v2 import CRMStoreV2
        store = CRMStoreV2()
        persons = store.get_all_persons()

        print(f"\n📊 Database Check:")
        print(f"Total persons in database: {len(persons)}")

        if persons:
            print("\nRecent 5 persons:")
            for p in persons[-5:]:
                print(f"  {p.id}. {p.first_name} {p.last_name} - {p.family_code or 'No family'}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
