"""
Storage Agent - Stores extracted family data into CRM V2.

This agent takes extraction results and stores them using the CRM MCP server.
It handles:
- Family creation/lookup
- Person profile creation
- Linking persons to families
- Intelligent family grouping by surname and city

Author: Shrinivas Deshpande
Date: December 6, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from dataclasses import dataclass, field
from typing import Optional, List
import asyncio
from collections import defaultdict

from src.mcp.client import call_crm_tool


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
class StorageResult:
    """Result from storage agent."""
    success: bool = True
    families_created: List[StoredFamily] = field(default_factory=list)
    persons_created: List[StoredPerson] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    summary: str = ""


class StorageAgent:
    """Agent that stores extracted family data into CRM V2."""

    def __init__(self):
        pass

    async def store(self, extraction: dict) -> StorageResult:
        """
        Store extraction results in CRM V2.

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
            # Step 1: Group persons by family using relationships
            family_groups, person_to_family_key = self._group_by_family_smart(persons, relationships)

            # Step 2: Create or find families
            family_map = await self._ensure_families(family_groups, result)

            # Step 3: Store person profiles
            await self._store_persons(persons, family_map, person_to_family_key, result)

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
                name = person.get("name", "")
                name_parts = name.strip().split()
                speaker_surname = name_parts[-1] if name_parts else "Unknown"
                speaker_city = person.get("location", "").strip() or "Unknown"
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
            name = person.get("name", "")
            if not name:
                continue

            name_parts = name.strip().split()
            surname = name_parts[-1] if name_parts else "Unknown"
            location = person.get("location", "")
            city = location.strip() if location else "Unknown"

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
            name = person.get("name", "")
            location = person.get("location", "")

            if not name:
                continue

            # Extract surname (assume last part of name)
            name_parts = name.strip().split()
            surname = name_parts[-1] if name_parts else "Unknown"

            # Use location as city (default to "Unknown" if missing)
            city = location.strip() if location else "Unknown"

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

                # Extract name components
                name_parts = name.strip().split()
                first_name = name_parts[0] if name_parts else name
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

                # Get location
                location = person_data.get("location", "")
                city = location.strip() if location else "Unknown"

                # Get family code from the person-to-family mapping
                family_key = person_to_family_key.get(name)
                family_code = family_map.get(family_key, "") if family_key else ""

                # Check if person already exists
                search_result = await call_crm_tool("search_persons", {
                    "query": name,
                    "family_code": family_code
                })

                if search_result.get("count", 0) > 0:
                    # Person exists
                    existing_person = search_result["persons"][0]
                    person_id = existing_person.get("person_id", 0)

                    if person_id:
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

                # Extract interests/activities
                interests = person_data.get("interests", "")

                add_result = await call_crm_tool("add_person", {
                    "first_name": first_name,
                    "last_name": last_name,
                    "gender": person_data.get("gender") or "",
                    "occupation": person_data.get("occupation") or "",
                    "phone": person_data.get("phone") or "",
                    "email": person_data.get("email") or "",
                    "city": city,
                    "family_code": family_code,
                    "hobbies": interests or "",  # Store interests in hobbies field
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

    def _generate_summary(self, result: StorageResult) -> str:
        """Generate human-readable summary."""
        families_count = len(result.families_created)
        persons_new = sum(1 for p in result.persons_created if not p.existing)
        persons_existing = sum(1 for p in result.persons_created if p.existing)
        errors_count = len(result.errors)

        parts = []

        if families_count > 0:
            parts.append(f"Created {families_count} familie(s)")

        if persons_new > 0:
            parts.append(f"Added {persons_new} new person(s)")

        if persons_existing > 0:
            parts.append(f"Found {persons_existing} existing person(s)")

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
