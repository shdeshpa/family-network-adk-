"""
Storage Agent - Multi-storage orchestrator for family data.

This agent coordinates storage across multiple systems:
1. GraphLite (FamilyGraph) - Relationship graph for tree visualization
2. CRM V2 (SQLite) - Structured relational data (profiles, donations, events)
3. Qdrant (Future) - Vector storage for semantic search of text blocks

Architecture:
    Extraction → Storage Agent → GraphLite + CRM V2 + Qdrant

Author: Shrinivas Deshpande
Date: December 6, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
import asyncio
from collections import defaultdict

from src.mcp.client import call_crm_tool
from src.graph.family_graph import FamilyGraph
from src.graph.person_store import PersonStore
from src.graph.crm_store_v2 import CRMStoreV2


@dataclass
class StoredPerson:
    """Person stored in CRM."""
    person_id: int
    name: str
    family_code: Optional[str] = None
    existing: bool = False


@dataclass
class StoredFamily:
    """Family stored in CRM."""
    family_id: int
    family_code: str
    surname: str
    city: str


@dataclass
class DuplicatePerson:
    """Person identified as duplicate."""
    name: str
    existing_id: int
    existing_name: str
    reason: str


@dataclass
class StorageResult:
    """Result from storage agent."""
    success: bool = True
    families_created: List[StoredFamily] = field(default_factory=list)
    persons_created: List[StoredPerson] = field(default_factory=list)
    duplicates_skipped: List[DuplicatePerson] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    summary: str = ""


class StorageAgent:
    """
    Multi-storage orchestrator for family data.

    Coordinates storage across:
    1. GraphLite (FamilyGraph) - Relationship graph
    2. CRM V2 (SQLite) - Structured relational data
    3. Qdrant (Future) - Vector storage for semantic search
    """

    def __init__(self):
        self.family_graph = FamilyGraph()
        self.person_store = PersonStore()
        self.crm_store = CRMStoreV2()
        self.name_to_graph_id: Dict[str, int] = {}  # Track name -> GraphLite person ID

    async def store(self, extraction: dict) -> StorageResult:
        """
        Store extraction results across multiple storage systems.

        Storage Pipeline:
        1. GraphLite (FamilyGraph) - Persons + relationships for graph queries
        2. CRM V2 (SQLite) - Structured profiles, donations, events
        3. Qdrant (Future) - Raw text blocks for semantic search

        Args:
            extraction: Dict with 'persons' and 'relationships' keys
                       Expected format from extraction_agent

        Returns:
            StorageResult with details of what was stored
        """
        result = StorageResult()

        if not extraction.get("success"):
            result.success = False
            result.errors.append("Invalid extraction result")
            return result

        persons = extraction.get("persons", [])
        relationships = extraction.get("relationships", [])

        if not persons:
            result.success = True
            result.summary = "No persons to store"
            return result

        try:
            # STEP 0: Separate duplicates from new persons
            new_persons = []
            for person in persons:
                if person.get("existing_id"):
                    # This is a duplicate - don't store, just record it
                    existing_id = person["existing_id"]
                    result.duplicates_skipped.append(DuplicatePerson(
                        name=person.get("name", "Unknown"),
                        existing_id=existing_id,
                        existing_name=person.get("name", "Unknown"),
                        reason=f"Auto-merged with existing person #{existing_id} (high similarity)"
                    ))
                    print(f"[StorageAgent] SKIPPING duplicate: {person.get('name')} (existing #{existing_id})")
                else:
                    # This is a new person - store it
                    new_persons.append(person)

            # If all persons are duplicates, we still need to store relationships
            if not new_persons:
                # No new persons to create, but we may have relationships to store
                print(f"[StorageAgent] All persons are duplicates. Storing relationships only...")

                # Store relationships (for quick CRM queries)
                await self._store_relationships_crm(relationships, result)

                # Also store relationships in GraphLite
                self._store_in_graphlite([], relationships, result)

                result.success = True
                result.summary = self._generate_summary(result)
                return result

            # TOOL 1: Populate GraphLite (FamilyGraph) for tree visualization - ONLY new persons
            self._store_in_graphlite(new_persons, relationships, result)

            # TOOL 2: Populate CRM V2 (SQLite) for structured queries - ONLY new persons
            # Step 2a: Group persons by family
            family_groups, person_to_family_key = self._group_by_family_smart(new_persons, relationships)

            # Step 2b: Create or find families
            family_map = await self._ensure_families(family_groups, result)

            # Step 2c: Store person profiles
            await self._store_persons(new_persons, family_map, person_to_family_key, result)

            # Step 2d: Store relationships (for quick CRM queries)
            await self._store_relationships_crm(relationships, result)

            # TOOL 3: Populate Qdrant (Future)
            # await self._store_in_qdrant(raw_text, result)

            # Generate summary
            result.summary = self._generate_summary(result)
            result.success = True

        except Exception as e:
            result.success = False
            result.errors.append(f"Storage error: {str(e)}")

        return result

    def _group_by_family_smart(self, persons: list, relationships: list) -> tuple[dict, dict]:
        """
        Group persons by family using relationships and speaker information.

        This improved version uses relationships to group related people together.

        Returns:
            Tuple of:
            - Dict mapping (surname, city) -> list of persons
            - Dict mapping person_name -> (surname, city) family key
        """
        # First, identify the speaker (primary person)
        speaker = None
        speaker_surname = None
        speaker_city = None

        for person in persons:
            if person.get("is_speaker"):
                speaker = person
                name = person.get("name") or ""
                name = name.strip() if isinstance(name, str) else ""
                name_parts = name.split()
                speaker_surname = name_parts[-1] if name_parts else "Unknown"
                location = person.get("location") or ""
                speaker_city = location.strip() if isinstance(location, str) and location else "Unknown"
                break

        # Build a relationship graph to find connected people
        person_connections = defaultdict(set)
        for rel in relationships:
            p1 = rel.get("person1", "")
            p2 = rel.get("person2", "")
            if p1 and p2:
                person_connections[p1].add(p2)
                person_connections[p2].add(p1)

        # Group persons and track person-to-family mapping
        groups = defaultdict(list)
        person_to_family_key = {}  # Track which family each person belongs to
        speaker_group_key = None

        for person in persons:
            name = person.get("name") or ""
            name = name.strip() if isinstance(name, str) else ""
            if not name:
                continue

            name_parts = name.split()
            surname = name_parts[-1] if name_parts else "Unknown"
            location = person.get("location") or ""
            city = location.strip() if isinstance(location, str) and location else "Unknown"

            # If this person is connected to the speaker, use speaker's family
            if speaker and speaker_surname:
                speaker_name = speaker.get("name", "")
                if (name in person_connections.get(speaker_name, set()) or
                    speaker_name in person_connections.get(name, set()) or
                    name == speaker_name):
                    # This person is related to the speaker, use speaker's family
                    if not speaker_group_key:
                        speaker_group_key = (speaker_surname, speaker_city)
                    groups[speaker_group_key].append(person)
                    person_to_family_key[name] = speaker_group_key
                    continue

            # Otherwise, group by surname and city as before
            family_key = (surname, city)
            groups[family_key].append(person)
            person_to_family_key[name] = family_key

        return dict(groups), person_to_family_key

    def _group_by_family(self, persons: list) -> tuple[dict, dict]:
        """
        LEGACY: Group persons by family based on surname and city.

        Returns:
            Tuple of:
            - Dict mapping (surname, city) -> list of persons
            - Dict mapping person_name -> (surname, city) family key
        """
        groups = defaultdict(list)
        person_to_family_key = {}

        for person in persons:
            name = person.get("name") or ""
            name = name.strip() if isinstance(name, str) else ""
            location = person.get("location") or ""

            if not name:
                continue

            # Extract surname (assume last part of name)
            name_parts = name.split()
            surname = name_parts[-1] if name_parts else "Unknown"

            # Use location as city (default to "Unknown" if missing)
            city = location.strip() if isinstance(location, str) and location else "Unknown"

            family_key = (surname, city)
            groups[family_key].append(person)
            person_to_family_key[name] = family_key

        return dict(groups), person_to_family_key

    async def _ensure_families(self, family_groups: dict, result: StorageResult) -> dict:
        """
        Create or find families for each group.

        Returns:
            Dict mapping (surname, city) -> family_code
        """
        family_map = {}

        for (surname, city), persons in family_groups.items():
            try:
                # Check if family already exists
                search_result = await call_crm_tool("list_families", {
                    "surname": surname,
                    "city": city
                })

                if search_result.get("count", 0) > 0:
                    # Use existing family
                    family = search_result["families"][0]
                    family_code = family.get("family_code", "")
                    family_map[(surname, city)] = family_code
                else:
                    # Create new family
                    create_result = await call_crm_tool("create_family", {
                        "surname": surname,
                        "city": city,
                        "description": f"Family created from extraction with {len(persons)} member(s)"
                    })

                    if create_result.get("success"):
                        family_data = create_result.get("family", {})
                        # Family.to_dict() returns "code" and "id", not "family_code" and "family_id"
                        family_code = family_data.get("code", "")
                        family_id = family_data.get("id", 0)

                        if family_code and family_id:
                            family_map[(surname, city)] = family_code

                            result.families_created.append(StoredFamily(
                                family_id=family_id,
                                family_code=family_code,
                                surname=surname,
                                city=city
                            ))
                        else:
                            result.errors.append(f"Invalid family data for {surname}-{city}: {family_data}")
                    else:
                        result.errors.append(f"Failed to create family {surname}-{city}")

            except Exception as e:
                result.errors.append(f"Family creation error for {surname}-{city}: {str(e)}")

        return family_map

    async def _store_persons(self, persons: list, family_map: dict, person_to_family_key: dict, result: StorageResult):
        """Store individual person profiles."""
        for person_data in persons:
            try:
                name = person_data.get("name", "")
                if not name:
                    continue

                # Handle None values safely
                name = name.strip() if name else ""
                if not name:
                    continue

                # Extract name components
                name_parts = name.split()
                first_name = name_parts[0] if name_parts else name
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

                # Get location (handle None)
                location = person_data.get("location") or ""
                city = location.strip() if location else "Unknown"

                # Get family code from the person-to-family mapping
                family_key = person_to_family_key.get(name)
                family_code = family_map.get(family_key, "") if family_key else ""

                # Note: Duplicates are now filtered out BEFORE this function is called
                # So we no longer need to check for existing_id here

                # Check if person already exists (fallback search for safety)
                search_result = await call_crm_tool("search_persons", {
                    "query": name,
                    "family_code": family_code
                })

                if search_result.get("count", 0) > 0:
                    # Person exists
                    existing_person = search_result["persons"][0]
                    person_id = existing_person.get("person_id", 0)

                    if person_id:
                        print(f"[StorageAgent] Found existing person #{person_id}: {name}")
                        result.persons_created.append(StoredPerson(
                            person_id=person_id,
                            name=name,
                            family_code=family_code,
                            existing=True
                        ))
                    continue

                # Create new person
                raw_mentions = person_data.get("raw_mentions", [])
                if isinstance(raw_mentions, list):
                    mentions_str = ", ".join(str(m) for m in raw_mentions)
                else:
                    mentions_str = str(raw_mentions)

                # Extract and categorize interests/activities
                interests = person_data.get("interests", "")

                # Parse interests into categories
                religious_interests = ""
                spiritual_interests = ""
                social_interests = ""
                hobbies = ""

                if interests:
                    interests_lower = interests.lower()

                    # Keywords for religious interests
                    religious_keywords = ['temple', 'church', 'mosque', 'puja', 'prayer', 'religious', 'worship', 'devotional']
                    # Keywords for spiritual interests
                    spiritual_keywords = ['meditation', 'yoga', 'spirituality', 'mindfulness', 'mantra']
                    # Keywords for social interests
                    social_keywords = ['volunteer', 'community', 'service', 'charity', 'social', 'donation']

                    # Split interests by comma or semicolon
                    interest_items = [item.strip() for item in interests.replace(';', ',').split(',') if item.strip()]

                    # Categorize each interest
                    for item in interest_items:
                        item_lower = item.lower()
                        if any(keyword in item_lower for keyword in religious_keywords):
                            religious_interests += (", " if religious_interests else "") + item
                        elif any(keyword in item_lower for keyword in spiritual_keywords):
                            spiritual_interests += (", " if spiritual_interests else "") + item
                        elif any(keyword in item_lower for keyword in social_keywords):
                            social_interests += (", " if social_interests else "") + item
                        else:
                            # Default to hobbies
                            hobbies += (", " if hobbies else "") + item

                    # If no categorization happened, put everything in hobbies
                    if not (religious_interests or spiritual_interests or social_interests or hobbies):
                        hobbies = interests

                add_result = await call_crm_tool("add_person", {
                    "first_name": first_name,
                    "last_name": last_name,
                    "gender": person_data.get("gender") or "",
                    "occupation": person_data.get("occupation") or "",
                    "phone": person_data.get("phone") or "",
                    "email": person_data.get("email") or "",
                    "city": city,
                    "family_code": family_code,
                    "religious_interests": religious_interests,
                    "spiritual_interests": spiritual_interests,
                    "social_interests": social_interests,
                    "hobbies": hobbies,
                    "notes": f"Created from extraction. Raw mentions: {mentions_str}"
                })

                # Handle case where result is a string (error message)
                if isinstance(add_result, str):
                    result.errors.append(f"MCP tool returned string for {name}: {add_result}")
                    continue

                if add_result.get("success"):
                    person_id = add_result.get("person_id", 0)
                    person_data_returned = add_result.get("person", {})

                    # Try to get person_id from either location
                    if not person_id:
                        person_id = person_data_returned.get("person_id", 0)

                    if person_id:
                        result.persons_created.append(StoredPerson(
                            person_id=person_id,
                            name=name,
                            family_code=family_code,
                            existing=False
                        ))
                    else:
                        result.errors.append(f"Failed to get person_id for: {name}. Response: {add_result}")
                else:
                    result.errors.append(f"Failed to add person: {name}")

            except Exception as e:
                result.errors.append(f"Person storage error for {person_data.get('name', 'unknown')}: {str(e)}")

    def _store_in_graphlite(self, persons: list, relationships: list, result: StorageResult):
        """
        TOOL 1: Store persons and relationships in GraphLite for tree visualization.

        GraphLite (FamilyGraph + PersonStore) is optimized for:
        - Graph traversal
        - Relationship queries
        - Tree visualization
        """
        self.name_to_graph_id.clear()

        # Step 1: Add persons to PersonStore
        for person_data in persons:
            try:
                name = person_data.get("name", "")
                if not name:
                    continue

                # Check if person already exists
                existing = self.person_store.find_by_name(name)
                if existing:
                    # Use existing person
                    self.name_to_graph_id[name] = existing[0].id
                    continue

                # Create new person in PersonStore
                from src.models import Person
                location = person_data.get("location", "")

                person_obj = Person(
                    name=name,
                    location=location,
                    gender=person_data.get("gender"),
                    interests=person_data.get("interests", "").split(",") if person_data.get("interests") else []
                )
                person_id = self.person_store.add_person(person_obj)
                self.name_to_graph_id[name] = person_id

            except Exception as e:
                result.errors.append(f"GraphLite person storage error for {person_data.get('name')}: {str(e)}")

        # Step 2: Add relationships to FamilyGraph
        for rel_data in relationships:
            try:
                person1_name = rel_data.get("person1", "")
                person2_name = rel_data.get("person2", "")
                relation_term = rel_data.get("relation_term", "").lower()

                if not person1_name or not person2_name:
                    continue

                # Get GraphLite IDs - check newly created persons first
                person1_id = self.name_to_graph_id.get(person1_name)
                person2_id = self.name_to_graph_id.get(person2_name)

                # If person not found in current batch, search in PersonStore for existing person
                if not person1_id:
                    existing = self.person_store.find_by_name(person1_name)
                    if existing:
                        person1_id = existing[0].id
                        self.name_to_graph_id[person1_name] = person1_id  # Cache for future lookups

                if not person2_id:
                    existing = self.person_store.find_by_name(person2_name)
                    if existing:
                        person2_id = existing[0].id
                        self.name_to_graph_id[person2_name] = person2_id  # Cache for future lookups

                if not person1_id or not person2_id:
                    print(f"[StorageAgent] Skipping GraphLite relationship {person1_name} -> {person2_name}: Person not found")
                    continue

                # Add relationship to FamilyGraph based on term
                if relation_term in {"wife", "husband", "spouse", "bayko", "navra", "pati", "patni"}:
                    self.family_graph.add_spouse(person1_id, person2_id)
                elif relation_term in {"son", "daughter", "child", "mulga", "mulgi"}:
                    # person1 has son/daughter person2 -> person1 is parent of person2
                    self.family_graph.add_parent_child(person1_id, person2_id)
                elif relation_term in {"father", "mother", "parent"}:
                    # person1 has father/mother person2 -> person2 is parent of person1
                    self.family_graph.add_parent_child(person2_id, person1_id)
                elif relation_term in {"brother", "sister", "sibling", "bhau", "bhai", "behen"}:
                    self.family_graph.add_sibling(person1_id, person2_id)

                print(f"[StorageAgent] Created GraphLite relationship: {person1_name} ({person1_id}) --{relation_term}--> {person2_name} ({person2_id})")

            except Exception as e:
                result.errors.append(f"GraphLite relationship storage error: {str(e)}")

    async def _store_relationships_crm(self, relationships: list, result: StorageResult):
        """
        TOOL 2d: Store relationships in CRM V2 for quick SQL queries.

        This duplicates relationships in SQL for:
        - Fast relational queries
        - Reporting and analytics
        - Data integrity constraints
        """
        if not relationships:
            return

        # Build a name-to-ID mapping from stored persons
        name_to_id = {}
        for stored_person in result.persons_created:
            name_to_id[stored_person.name] = stored_person.person_id

        for rel_data in relationships:
            try:
                person1_name = rel_data.get("person1", "")
                person2_name = rel_data.get("person2", "")
                relation_term = rel_data.get("relation_term", "")
                relation_type = rel_data.get("relation_type", "")

                if not person1_name or not person2_name:
                    continue

                # Get person IDs - check newly created persons first
                person1_id = name_to_id.get(person1_name)
                person2_id = name_to_id.get(person2_name)

                # If person not found in current batch, search in CRM for existing person
                if not person1_id:
                    # Use CRM store directly (search_persons MCP tool is broken)
                    all_persons = self.crm_store.get_all()
                    matches = [p for p in all_persons if p.full_name == person1_name]
                    if matches:
                        person1_id = matches[0].id
                        name_to_id[person1_name] = person1_id  # Cache for future lookups
                        print(f"[StorageAgent] Found existing person in CRM: {person1_name} (ID: {person1_id})")

                if not person2_id:
                    # Use CRM store directly (search_persons MCP tool is broken)
                    all_persons = self.crm_store.get_all()
                    matches = [p for p in all_persons if p.full_name == person2_name]
                    if matches:
                        person2_id = matches[0].id
                        name_to_id[person2_name] = person2_id  # Cache for future lookups
                        print(f"[StorageAgent] Found existing person in CRM: {person2_name} (ID: {person2_id})")

                if not person1_id or not person2_id:
                    # Person not found in this extraction batch or CRM database
                    print(f"[StorageAgent] Skipping relationship {person1_name} -> {person2_name}: Person not found")
                    continue

                # Map relation_type if not provided
                if not relation_type:
                    relation_type = self._infer_relation_type(relation_term)

                # Store relationship via MCP tool
                await call_crm_tool("add_relationship", {
                    "person1_id": person1_id,
                    "person2_id": person2_id,
                    "relation_type": relation_type,
                    "relation_term": relation_term
                })

                print(f"[StorageAgent] Created relationship: {person1_name} ({person1_id}) --{relation_term}--> {person2_name} ({person2_id})")

            except Exception as e:
                result.errors.append(f"CRM relationship storage error: {str(e)}")

    def _infer_relation_type(self, relation_term: str) -> str:
        """Infer relation_type from relation_term."""
        term_lower = relation_term.lower()

        spouse_terms = {"wife", "husband", "spouse", "bayko", "navra", "pati", "patni"}
        parent_child_terms = {"son", "daughter", "child", "father", "mother", "parent", "mulga", "mulgi"}
        sibling_terms = {"brother", "sister", "sibling", "bhau", "bhai", "behen"}
        friend_terms = {"friend"}
        colleague_terms = {"colleague", "coworker", "boss", "manager", "employee"}
        fan_terms = {"fan", "fan of", "follower", "admirer"}
        mentor_terms = {"mentor", "mentee", "teacher", "student"}
        neighbor_terms = {"neighbor"}
        roommate_terms = {"roommate"}
        classmate_terms = {"classmate"}

        if term_lower in spouse_terms:
            return "spouse"
        elif term_lower in parent_child_terms:
            return "parent_child"
        elif term_lower in sibling_terms:
            return "sibling"
        elif term_lower in friend_terms:
            return "friend_of"
        elif term_lower in colleague_terms:
            return "colleague"
        elif term_lower in fan_terms:
            return "fan_of"
        elif term_lower in mentor_terms:
            return "mentor"
        elif term_lower in neighbor_terms:
            return "neighbor"
        elif term_lower in roommate_terms:
            return "roommate"
        elif term_lower in classmate_terms:
            return "classmate"
        else:
            return "other"

    def _generate_summary(self, result: StorageResult) -> str:
        """Generate human-readable summary."""
        families_count = len(result.families_created)
        persons_new = sum(1 for p in result.persons_created if not p.existing)
        persons_existing = sum(1 for p in result.persons_created if p.existing)
        duplicates_count = len(result.duplicates_skipped)
        errors_count = len(result.errors)

        parts = []

        if families_count > 0:
            parts.append(f"Created {families_count} familie(s)")

        if persons_new > 0:
            parts.append(f"Added {persons_new} new person(s)")

        if persons_existing > 0:
            parts.append(f"Found {persons_existing} existing person(s)")

        if duplicates_count > 0:
            parts.append(f"Skipped {duplicates_count} duplicate(s)")

        if errors_count > 0:
            parts.append(f"{errors_count} error(s)")

        return ", ".join(parts) if parts else "No changes"


async def store_extraction(extraction: dict) -> StorageResult:
    """
    Store extraction results in CRM V2.

    Convenience function for direct use.

    Args:
        extraction: Dict from extraction_agent with persons and relationships

    Returns:
        StorageResult with details of what was stored
    """
    agent = StorageAgent()
    return await agent.store(extraction)
