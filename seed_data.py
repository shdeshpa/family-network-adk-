"""
Seed script for Family Network ADK - Populates database with sample family data.

This script:
1. Clears all existing data from GraphLite and SQLite
2. Creates sample families with complete information including:
   - Phone numbers, emails
   - Gothra, Nakshatra (Hindu religious data)
   - Religious interests, hobbies
   - Various relationships (family, friends, colleagues)

Run this script to start with a clean slate:
    python seed_data.py
"""

import asyncio
from pathlib import Path
import shutil

from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.family_registry import FamilyRegistry
from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.agents.adk.orchestrator import FamilyOrchestrator


def clear_all_databases():
    """Remove all database files to start fresh."""
    print("=" * 80)
    print("CLEARING ALL DATABASES")
    print("=" * 80)

    # Database paths
    crm_db = Path("data/crm/crm_v2.db")
    graphlite_db = Path(".graphlite/data/default.db")

    # Remove CRM database
    if crm_db.exists():
        crm_db.unlink()
        print(f"✅ Deleted: {crm_db}")
    else:
        print(f"⚠️  Not found: {crm_db}")

    # Remove GraphLite database directory
    graphlite_dir = Path(".graphlite")
    if graphlite_dir.exists():
        shutil.rmtree(graphlite_dir)
        print(f"✅ Deleted: {graphlite_dir}")
    else:
        print(f"⚠️  Not found: {graphlite_dir}")

    print("\n✅ All databases cleared!\n")


async def seed_sample_data():
    """Create comprehensive sample family data."""
    print("=" * 80)
    print("SEEDING SAMPLE FAMILY DATA")
    print("=" * 80)

    orchestrator = FamilyOrchestrator(llm_provider="ollama/llama3")

    # Sample data entries with complete information
    sample_entries = [
        # ========== KAWTHALKAR FAMILY (Pune) ==========
        """
        My name is Tejas Kawthalkar from Pune, Maharashtra. I'm a software engineer at Google.
        Born in 1985. Phone: 1-408-555-0101. Email: tejas@example.com.
        Gothra: Kashyap. Nakshatra: Rohini.
        Religious interests: Daily puja, temple visits. Hobbies: Cricket, reading Bhagavad Gita.

        My wife is Priya Kawthalkar from Pune.
        She was born in 1987. Phone: 1-408-555-0102. Email: priya.k@example.com.
        Gothra: Bharadwaj. Nakshatra: Ashwini.
        She's a teacher. Religious interests: Bhajan singing, fasting on Thursdays.
        Hobbies: Cooking, yoga, classical music.

        We have a son Aarav Kawthalkar from Pune.
        Born in 2010. Phone: 408-555-0103. Email: aarav.k@example.com.
        Nakshatra: Pushya. Student in 8th grade.
        Hobbies: Video games, football, robotics.

        My father is Sanjay Kawthalkar, living in Pune.
        Born in 1955. Retired bank manager. Phone: +91-20-5550-1001. Email: sanjay.k@example.com.
        Gothra: Kashyap. Nakshatra: Uttara Phalguni.
        Very religious person. Religious interests: Daily Hanuman Chalisa, temple committee member.
        Hobbies: Morning walks, gardening, spiritual books.

        My mother is Anjali Kawthalkar, wife of Sanjay.
        From Pune. Born in 1958. Phone: +91-20-5550-1002. Email: anjali.k@example.com.
        Gothra: Vatsa. Nakshatra: Hasta.
        Homemaker. Religious interests: Satyanarayan puja, Krishna bhakti.
        Hobbies: Cooking traditional recipes, knitting.
        """,

        # ========== DESHPANDE FAMILY (Hyderabad) ==========
        """
        My name is Srikanth Deshpande from Hyderabad, Telangana.
        Born in 1980. Software architect at Microsoft. Phone: 1-425-555-0201. Email: srikanth.d@example.com.
        Gothra: Kaushik. Nakshatra: Mrigashira.
        Religious interests: Visiting Tirupati every year, daily meditation.
        Hobbies: Photography, trekking, classical guitar.

        My wife is Lakshmi Deshpande from Hyderabad.
        Born in 1982. Doctor specializing in pediatrics. Phone: 425-555-0202. Email: lakshmi.d@example.com.
        Gothra: Atri. Nakshatra: Anuradha.
        Religious interests: Lakshmi puja on Fridays, Varalakshmi Vratham.
        Hobbies: Bharatanatyam dance, ayurvedic cooking.

        Our son is Ishaan Deshpande from Hyderabad. Born in 2012. Email: ishaan.d@example.com.
        Student in 6th grade. Nakshatra: Revati.
        Hobbies: Chess, coding, reading mythology stories.
        """,

        # ========== SHARMA FAMILY (Mumbai) ==========
        """
        My name is Ramesh Sharma from Mumbai, Maharashtra. Born in 1975.
        Business owner running a restaurant chain. Phone: +91-22-5550-3001. Email: ramesh.s@example.com.
        Gothra: Gautam. Nakshatra: Punarvasu.
        Religious interests: Ganesh bhakti, sponsors community Ganesh festival.
        Hobbies: Cooking, traveling to pilgrimage sites.

        My wife is Meera Sharma from Mumbai.
        Born in 1977. Interior designer. Phone: +91-22-5550-3002. Email: meera.s@example.com.
        Gothra: Sandilya. Nakshatra: Swati.
        Religious interests: Durga puja, Navratri fasting.
        Hobbies: Painting, classical dance, temple architecture.

        Our daughter is Ananya Sharma from Mumbai.
        Born in 2005. Phone: 22-5550-3003. Email: ananya.s@example.com.
        Nakshatra: Vishakha. College student studying architecture.
        Religious interests: Volunteers at temple events.
        Hobbies: Sketching, volunteering, Kathak dance.

        Our son is Arjun Sharma from Mumbai. Born in 2008. Email: arjun.s@example.com.
        Nakshatra: Jyeshtha. High school student.
        Hobbies: Cricket, music production, gaming.
        """,

        # ========== PATEL FAMILY (Ahmedabad) ==========
        """
        My name is Vikram Patel from Ahmedabad, Gujarat. Born in 1978.
        Businessman in textiles. Phone: +91-79-5550-4001. Email: vikram.p@example.com.
        Gothra: Bharadwaj. Nakshatra: Magha.
        Religious interests: Jain temple visits, follows Jain fasting.
        Hobbies: Stock market, badminton.

        My wife is Kavita Patel from Ahmedabad.
        Born in 1980. Runs a fashion boutique. Phone: +91-79-5550-4002. Email: kavita.p@example.com.
        Gothra: Agastya. Nakshatra: Purva Phalguni.
        Religious interests: Mata ni pachedi, Navratri garba organizer.
        Hobbies: Fashion design, garba dancing, social work.
        """,

        # ========== NON-FAMILY RELATIONSHIPS ==========
        """
        I am Rajesh Mehta from Pune, Maharashtra. Born in 1984.
        Software engineer and colleague of Tejas Kawthalkar at Google.
        Phone: 408-555-0501. Email: rajesh.m@example.com.
        Gothra: Vishwamitra. Nakshatra: Chitra.
        Religious interests: Shiv bhakti, monthly fasting.
        Hobbies: Hiking, astronomy.
        """,

        """
        My name is Amit Verma from Hyderabad. Born in 1979.
        I am a college friend of Srikanth Deshpande. I work in finance.
        Phone: 1-212-555-0601. Email: amit.v@example.com.
        Gothra: Jamadagni. Nakshatra: Dhanishta.
        Religious interests: Ram bhakti, Hanuman chalisa.
        Hobbies: Marathon running, stock trading.
        """,
    ]

    print(f"\nProcessing {len(sample_entries)} sample entries...\n")

    for i, entry in enumerate(sample_entries, 1):
        print(f"[{i}/{len(sample_entries)}] Processing entry...")
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: orchestrator.process_text(entry.strip())
            )

            if result.get('success'):
                print(f"  ✅ Success")
                if result.get('storage'):
                    storage = result['storage']
                    print(f"     Persons created: {storage.get('persons_created', 0)}")
                    print(f"     Relationships created: {storage.get('relationships_created', 0)}")
            else:
                print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"  ❌ Exception: {e}")

        print()

    print("=" * 80)
    print("SEED DATA SUMMARY")
    print("=" * 80)

    # Show summary
    crm = CRMStoreV2()
    all_persons = crm.get_all()
    active_persons = [p for p in all_persons if not p.is_archived]

    print(f"\n✅ Total persons created: {len(active_persons)}")
    print(f"\nPersons by family:")

    families = {}
    for p in active_persons:
        family_code = p.family_code or "No Family"
        if family_code not in families:
            families[family_code] = []
        families[family_code].append(p.full_name)

    for family_code, members in sorted(families.items()):
        print(f"\n  {family_code}:")
        for member in members:
            print(f"    - {member}")

    print("\n" + "=" * 80)
    print("SEED COMPLETE! 🎉")
    print("=" * 80)
    print("\nYou can now:")
    print("  1. Start the UI: python run_ui.py")
    print("  2. View the family tree at http://localhost:8080")
    print("  3. Test adding: 'I am Rajkumar Rao. Film actor. I am fan of Tejas Kawthalkar who lives in Pune'")
    print("\nTo reset and re-seed: python seed_data.py")
    print("=" * 80)


async def main():
    """Main function."""
    # Step 1: Clear databases
    clear_all_databases()

    # Step 2: Seed sample data
    await seed_sample_data()


if __name__ == "__main__":
    asyncio.run(main())
