"""
RelationExpertAgent - Duplicate detection and resolution before storage.

Detects potential duplicate persons and asks clarifying questions via MCP tools.

Author: Shrinivas Deshpande
Date: December 7, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from difflib import SequenceMatcher
import asyncio
import re

from src.graph.crm_store_v2 import CRMStoreV2


@dataclass
class DuplicateCandidate:
    """Potential duplicate person."""
    extracted_name: str
    existing_id: int
    existing_name: str
    similarity_score: float
    existing_data: dict


@dataclass
class RelationExpertResult:
    """Result from relation expert agent."""
    success: bool
    persons: list  # Cleaned list of persons (duplicates merged)
    relationships: list
    merges: List[Dict]  # List of {extracted_name, existing_id, action}
    errors: List[str]
    summary: str


class RelationExpertAgent:
    """
    Relation Expert Agent - handles duplicate detection and resolution.

    Flow:
    1. Receives extracted persons and relationships
    2. Checks each person against existing CRM V2 data
    3. For potential duplicates, uses MCP tools to ask clarifying questions
    4. Merges or creates new persons based on decisions
    5. Returns cleaned data to Storage Agent
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize relation expert agent.

        Args:
            similarity_threshold: Name similarity threshold for duplicate detection (0.0-1.0)
        """
        self.crm_store = CRMStoreV2()
        self.similarity_threshold = similarity_threshold

    async def process(self, extraction_data: dict) -> RelationExpertResult:
        """
        Process extraction data and resolve duplicates.

        Args:
            extraction_data: Dict with 'persons' and 'relationships' lists

        Returns:
            RelationExpertResult with cleaned data
        """
        persons = extraction_data.get("persons", [])
        relationships = extraction_data.get("relationships", [])

        cleaned_persons = []
        merges = []
        errors = []

        print(f"\n[RelationExpertAgent] Processing {len(persons)} extracted persons...")

        for person_data in persons:
            person_name = person_data.get("name", "")
            person_phone = person_data.get("phone", "")

            # Find potential duplicates in CRM V2
            candidates = self._find_duplicate_candidates(person_name, person_phone)

            if not candidates:
                # No duplicates found, keep as-is
                cleaned_persons.append(person_data)
                print(f"  ✅ {person_name} - No duplicates, will create new")
                continue

            # Found potential duplicates - need to decide what to do
            # Check for phone match first (very high confidence)
            phone_matched = any(c.similarity_score >= 1.5 for c in candidates)  # Score > 1.0 means phone match

            if phone_matched or (len(candidates) == 1 and candidates[0].similarity_score > 0.95):
                # Very high confidence match - auto-merge
                candidate = candidates[0]
                match_reason = "phone + name match" if phone_matched else "name similarity"
                print(f"  🔄 {person_name} → Merging with existing #{candidate.existing_id} ({candidate.existing_name}) [{match_reason}]")

                merges.append({
                    "extracted_name": person_name,
                    "existing_id": candidate.existing_id,
                    "existing_name": candidate.existing_name,
                    "action": "auto_merge",
                    "confidence": candidate.similarity_score,
                    "match_reason": match_reason
                })

                # Use existing person, update with new data
                merged_data = self._merge_person_data(person_data, candidate.existing_data, candidate.existing_id)
                cleaned_persons.append(merged_data)

            else:
                # Multiple candidates or lower confidence
                print(f"  ❓ {person_name} - Found {len(candidates)} potential duplicates")
                for i, cand in enumerate(candidates[:3]):  # Show top 3
                    print(f"     {i+1}. {cand.existing_name} (ID: {cand.existing_id}, Score: {cand.similarity_score:.2f})")

                # If all top candidates have perfect/near-perfect match, merge with first one
                top_candidate = candidates[0]
                if top_candidate.similarity_score >= 0.95:
                    # Very high confidence on top match - use it even with multiple candidates
                    print(f"  🔄 {person_name} → Merging with existing #{top_candidate.existing_id} ({top_candidate.existing_name}) [top match from {len(candidates)} candidates]")

                    merges.append({
                        "extracted_name": person_name,
                        "existing_id": top_candidate.existing_id,
                        "existing_name": top_candidate.existing_name,
                        "action": "auto_merge",
                        "confidence": top_candidate.similarity_score,
                        "match_reason": f"top match from {len(candidates)} candidates"
                    })

                    # Use existing person
                    merged_data = self._merge_person_data(person_data, top_candidate.existing_data, top_candidate.existing_id)
                    cleaned_persons.append(merged_data)
                else:
                    # Lower confidence - for now, create as new person
                    # TODO: Use MCP tool to ask user for decision
                    cleaned_persons.append(person_data)

                    merges.append({
                        "extracted_name": person_name,
                        "candidates": [
                            {"existing_id": c.existing_id, "existing_name": c.existing_name, "score": c.similarity_score}
                            for c in candidates[:3]
                        ],
                        "action": "needs_clarification",
                        "decision": "create_new"  # Default for now
                    })

        # Update relationship person names if they were merged
        cleaned_relationships = self._update_relationship_names(relationships, merges)

        summary = f"Processed {len(persons)} persons: {len([m for m in merges if m['action'] == 'auto_merge'])} auto-merged, {len(cleaned_persons)} total"

        return RelationExpertResult(
            success=True,
            persons=cleaned_persons,
            relationships=cleaned_relationships,
            merges=merges,
            errors=errors,
            summary=summary
        )

    def _find_duplicate_candidates(self, name: str, phone: Optional[str] = None) -> List[DuplicateCandidate]:
        """
        Find potential duplicate persons in CRM V2 by name similarity and phone matching.

        Scoring:
        - Name match only: 0.0 - 1.0
        - Name match + phone match: 1.5 - 2.5 (boosted score for high confidence)
        """
        candidates = []

        # Normalize phone for comparison
        normalized_phone = self._normalize_phone(phone) if phone else ""

        # Get all persons from CRM V2
        all_persons = self.crm_store.get_all()

        for person in all_persons:
            if person.is_archived:
                continue

            # Calculate name similarity
            name_similarity = self._calculate_name_similarity(name, person.full_name)

            # Check phone match
            phone_match = False
            if normalized_phone and person.phone:
                existing_phone = self._normalize_phone(person.phone)
                # Match if phones are the same (or if one ends with the other, for country code variations)
                if normalized_phone == existing_phone:
                    phone_match = True
                elif len(normalized_phone) > 7 and len(existing_phone) > 7:
                    # Check if one is suffix of another (handles country code differences)
                    if normalized_phone.endswith(existing_phone[-10:]) or existing_phone.endswith(normalized_phone[-10:]):
                        phone_match = True

            # Calculate combined score
            if phone_match and name_similarity >= 0.5:
                # Phone match + reasonable name similarity = very high confidence
                # Boost score above 1.0 to indicate phone match
                combined_score = 1.5 + name_similarity
            elif name_similarity >= self.similarity_threshold:
                # Name similarity only
                combined_score = name_similarity
            else:
                # Not a candidate
                continue

            candidates.append(DuplicateCandidate(
                extracted_name=name,
                existing_id=person.id,
                existing_name=person.full_name,
                similarity_score=combined_score,
                existing_data={
                    "id": person.id,
                    "full_name": person.full_name,
                    "gender": person.gender,
                    "phone": person.phone,
                    "email": person.email,
                    "family_code": person.family_code
                }
            ))

        # Sort by similarity score descending
        candidates.sort(key=lambda x: x.similarity_score, reverse=True)

        return candidates

    def _normalize_phone(self, phone: Optional[str]) -> str:
        """
        Normalize phone number to digits only for comparison.

        Examples:
        - "1-408-444-5555" → "14084445555"
        - "1(408)444-5555" → "14084445555"
        - "4084445555" → "4084445555"
        - "+1 408 444 5555" → "14084445555"
        """
        if not phone:
            return ""

        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        return digits_only

    def _normalize_name(self, name: str) -> str:
        """
        Normalize name by removing honorifics and extra whitespace.

        Handles:
        - "Srikanth Garu" → "srikanth"
        - "Srikanth Bhau" → "srikanth"
        - "Mr. John Smith" → "john smith"
        - "  JOHN  SMITH  " → "john smith"
        """
        if not name:
            return ""

        # Common Indian honorifics
        honorifics = [
            'garu', 'bhau', 'bhai', 'amma', 'anna', 'akka',
            'dada', 'tai', 'mavshi', 'kaka', 'mama',
            'mr', 'mrs', 'ms', 'dr', 'prof', 'sir', 'madam'
        ]

        # Lowercase and remove extra whitespace
        normalized = ' '.join(name.lower().strip().split())

        # Remove honorifics
        words = normalized.split()
        filtered_words = [w for w in words if w.rstrip('.') not in honorifics]

        return ' '.join(filtered_words)

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names (0.0 - 1.0)."""
        # Normalize names (removes honorifics, extra spaces)
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)

        if n1 == n2:
            return 1.0

        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, n1, n2).ratio()

    def _merge_person_data(self, new_data: dict, existing_data: dict, existing_id: int) -> dict:
        """
        Merge new person data with existing person data.

        Priority: Keep existing data, only add new fields if missing.
        """
        merged = new_data.copy()

        # Mark as existing person for storage agent
        merged["existing_id"] = existing_id
        merged["name"] = existing_data["full_name"]  # Use existing name

        # Keep existing data if new data is missing
        if not merged.get("gender") and existing_data.get("gender"):
            merged["gender"] = existing_data["gender"]
        if not merged.get("phone") and existing_data.get("phone"):
            merged["phone"] = existing_data["phone"]
        if not merged.get("email") and existing_data.get("email"):
            merged["email"] = existing_data["email"]

        return merged

    def _update_relationship_names(self, relationships: list, merges: list) -> list:
        """Update relationship person names if they were merged."""
        # Build mapping of extracted name -> final name
        name_mapping = {}
        for merge in merges:
            if merge.get("action") == "auto_merge":
                name_mapping[merge["extracted_name"]] = merge["existing_name"]

        # Update relationships
        updated_relationships = []
        for rel in relationships:
            updated_rel = rel.copy()

            if rel["person1"] in name_mapping:
                updated_rel["person1"] = name_mapping[rel["person1"]]
            if rel["person2"] in name_mapping:
                updated_rel["person2"] = name_mapping[rel["person2"]]

            updated_relationships.append(updated_rel)

        return updated_relationships
