"""
Relation Expert MCP Server - Tools for duplicate detection and resolution.

This server provides tools that the RelationExpertAgent uses to:
- Find potential duplicate persons
- Ask clarifying questions about duplicates
- Merge or create persons based on user decisions

Architecture:
    RelationExpertAgent → MCP Protocol → relation_expert_server.py → CRM V2 → SQLite

Author: Shrinivas Deshpande
Date: December 7, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from mcp.server.fastmcp import FastMCP
from typing import Optional, List, Dict
from difflib import SequenceMatcher

from src.graph.crm_store_v2 import CRMStoreV2


# Initialize MCP server
mcp = FastMCP("relation-expert-server")

# Lazy-loaded singleton
_store: Optional[CRMStoreV2] = None


def get_store() -> CRMStoreV2:
    """Get or create CRMStoreV2 instance."""
    global _store
    if _store is None:
        _store = CRMStoreV2()
    return _store


# =============================================================================
# DUPLICATE DETECTION TOOLS
# =============================================================================

@mcp.tool()
def find_similar_persons(name: str, similarity_threshold: float = 0.85) -> List[Dict]:
    """
    Find persons in CRM with similar names.

    Use this tool to detect potential duplicates before creating a new person.

    Args:
        name: Name to search for
        similarity_threshold: Minimum similarity score (0.0-1.0, default 0.85)

    Returns:
        List of similar persons with their details and similarity scores
    """
    store = get_store()
    all_persons = store.get_all()

    similar = []

    for person in all_persons:
        if person.is_archived:
            continue

        # Calculate name similarity
        similarity = SequenceMatcher(None, name.lower().strip(), person.full_name.lower().strip()).ratio()

        if similarity >= similarity_threshold:
            similar.append({
                "id": person.id,
                "name": person.full_name,
                "gender": person.gender or "Unknown",
                "phone": person.phone or "N/A",
                "email": person.email or "N/A",
                "family_code": person.family_code or "N/A",
                "similarity_score": round(similarity, 3)
            })

    # Sort by similarity descending
    similar.sort(key=lambda x: x["similarity_score"], reverse=True)

    return similar


@mcp.tool()
def get_person_details(person_id: int) -> Dict:
    """
    Get detailed information about a specific person.

    Use this to show full details when asking user about a potential duplicate.

    Args:
        person_id: CRM person ID

    Returns:
        Person details including relationships and notes
    """
    store = get_store()

    person = store.get(person_id)
    if not person:
        return {"error": f"Person {person_id} not found"}

    # Get relationships
    relationships = store.get_relationships(person_id)

    return {
        "id": person.id,
        "full_name": person.full_name,
        "gender": person.gender,
        "phone": person.phone,
        "email": person.email,
        "family_code": person.family_code,
        "notes": person.notes or "",
        "created_at": person.created_at,
        "updated_at": person.updated_at,
        "relationships": [
            {
                "person1_id": r["person1_id"],
                "person2_id": r["person2_id"],
                "relation_type": r["relation_type"],
                "relation_term": r.get("relation_term", "")
            }
            for r in relationships
        ]
    }


@mcp.tool()
def ask_duplicate_decision(
    extracted_name: str,
    extracted_data: Dict,
    candidates: List[Dict]
) -> Dict:
    """
    Ask user to decide what to do with a potential duplicate.

    This tool formats a question for the user and returns their decision.

    Args:
        extracted_name: Name extracted from text
        extracted_data: Data extracted for this person (gender, phone, etc.)
        candidates: List of potential duplicates from find_similar_persons

    Returns:
        User decision: {"action": "merge"/"create_new", "merge_with_id": int}
    """
    # Format the question
    question = f"\n{'='*80}\n"
    question += f"DUPLICATE DETECTION: '{extracted_name}'\n"
    question += f"{'='*80}\n\n"

    question += "Extracted data:\n"
    for key, value in extracted_data.items():
        if value:
            question += f"  - {key}: {value}\n"

    question += f"\nFound {len(candidates)} similar person(s) in database:\n\n"

    for i, cand in enumerate(candidates, 1):
        question += f"{i}. {cand['name']} (ID: {cand['id']}, Score: {cand['similarity_score']})\n"
        question += f"   Gender: {cand.get('gender', 'Unknown')}, Phone: {cand.get('phone', 'N/A')}, Email: {cand.get('email', 'N/A')}\n"
        question += f"   Family: {cand.get('family_code', 'N/A')}\n\n"

    question += "Options:\n"
    for i in range(len(candidates)):
        question += f"  [{i+1}] Merge with person #{candidates[i]['id']} ({candidates[i]['name']})\n"
    question += f"  [0] Create new person (not a duplicate)\n"

    # For now, print and return default (in future, this would use MCP prompts)
    print(question)
    print("[RelationExpertAgent] Default action: Create new person (user interaction not yet implemented)")

    # TODO: Implement actual user interaction via MCP prompt/input
    return {
        "action": "create_new",
        "merge_with_id": None,
        "reason": "User interaction not yet implemented"
    }


@mcp.tool()
def merge_person_data(
    new_data: Dict,
    existing_person_id: int,
    update_strategy: str = "prefer_existing"
) -> Dict:
    """
    Merge new person data with existing person.

    Args:
        new_data: New person data extracted from text
        existing_person_id: ID of existing person to merge with
        update_strategy: "prefer_existing" or "prefer_new"

    Returns:
        Merged person data
    """
    store = get_store()

    existing = store.get(existing_person_id)
    if not existing:
        return {"error": f"Person {existing_person_id} not found"}

    merged = {
        "existing_id": existing.id,
        "name": existing.full_name,
        "gender": existing.gender,
        "phone": existing.phone,
        "email": existing.email,
        "family_code": existing.family_code
    }

    # Merge strategy
    if update_strategy == "prefer_new":
        # Overwrite with new data if available
        for key, value in new_data.items():
            if value and key in merged:
                merged[key] = value
    else:  # prefer_existing
        # Only add new data if existing is missing
        for key, value in new_data.items():
            if key in merged and not merged[key] and value:
                merged[key] = value

    return merged


@mcp.tool()
def get_duplicate_statistics() -> Dict:
    """
    Get statistics about potential duplicates in the database.

    Returns:
        Statistics on duplicate names, similar entries, etc.
    """
    store = get_store()
    all_persons = store.get_all()

    active_persons = [p for p in all_persons if not p.is_archived]

    # Find potential duplicates (names with similarity > 0.9)
    potential_duplicates = []
    checked = set()

    for i, p1 in enumerate(active_persons):
        for p2 in active_persons[i+1:]:
            pair_key = tuple(sorted([p1.id, p2.id]))
            if pair_key in checked:
                continue

            similarity = SequenceMatcher(None, p1.full_name.lower(), p2.full_name.lower()).ratio()

            if similarity > 0.9:
                potential_duplicates.append({
                    "id1": p1.id,
                    "name1": p1.full_name,
                    "id2": p2.id,
                    "name2": p2.full_name,
                    "similarity": round(similarity, 3)
                })
                checked.add(pair_key)

    return {
        "total_persons": len(active_persons),
        "potential_duplicates": len(potential_duplicates),
        "duplicate_pairs": potential_duplicates[:10]  # Top 10
    }


# Run the server
if __name__ == "__main__":
    mcp.run()
