"""Command-line CRM viewer - works without web server."""

import sys
sys.path.insert(0, ".")

from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.family_registry import FamilyRegistry

def main():
    print("=" * 80)
    print("📇 FAMILY NETWORK CRM - Command Line Viewer")
    print("=" * 80)

    store = CRMStoreV2()
    registry = FamilyRegistry()

    # Get statistics
    families = registry.get_all()
    persons = store.get_all_persons()

    print(f"\n📊 Statistics:")
    print(f"   👨‍👩‍👧‍👦 {len(families)} Families")
    print(f"   👤 {len(persons)} Persons")
    print()

    # Show families
    for family in families:
        print(f"\n{'=' * 80}")
        print(f"👨‍👩‍👧‍👦 Family: {family.code}")
        print(f"   Surname: {family.surname}")
        print(f"   City: {family.city}")
        if family.description:
            print(f"   Description: {family.description}")

        # Get family members
        members = store.get_by_family(family.code)
        print(f"\n   Members ({len(members)}):")

        for person in members:
            print(f"\n   👤 {person.first_name} {person.last_name}")
            if person.gender:
                print(f"      Gender: {person.gender}")
            if person.birth_year:
                print(f"      Birth Year: {person.birth_year}")
            if person.occupation:
                print(f"      Occupation: {person.occupation}")
            if person.city:
                print(f"      City: {person.city}")
            if person.phone:
                print(f"      Phone: {person.phone}")
            if person.email:
                print(f"      Email: {person.email}")

            # Show donations
            donations = store.get_donations(person.id)
            if donations:
                print(f"      💰 Donations: {len(donations)}")
                for don in donations:
                    print(f"         • {don.amount} {don.currency} - {don.cause or 'General'}")

    # Show unassigned persons
    unassigned = [p for p in persons if not p.family_code]
    if unassigned:
        print(f"\n{'=' * 80}")
        print(f"❓ Unassigned Persons ({len(unassigned)}):")
        for person in unassigned:
            print(f"\n   👤 {person.first_name} {person.last_name}")
            if person.city:
                print(f"      City: {person.city}")
            if person.notes:
                print(f"      Notes: {person.notes[:100]}...")

    print(f"\n{'=' * 80}")
    print("✅ Done!")
    print()

if __name__ == "__main__":
    main()
