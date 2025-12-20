"""Tool definitions for ADK agents - syncs to both databases."""

from typing import Optional
import requests

from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.crm_store import CRMStore
from src.graph.enhanced_crm import EnhancedCRM, PersonProfile
from src.models import Person

# Lazy-initialized stores
_person_store: Optional[PersonStore] = None
_family_graph: Optional[FamilyGraph] = None
_crm_store: Optional[CRMStore] = None
_enhanced_crm: Optional[EnhancedCRM] = None


def _get_stores():
    """Get or initialize stores."""
    global _person_store, _family_graph, _crm_store, _enhanced_crm
    if _person_store is None:
        _person_store = PersonStore()
        _family_graph = FamilyGraph()
        _crm_store = CRMStore()
        _enhanced_crm = EnhancedCRM()
    return _person_store, _family_graph, _crm_store, _enhanced_crm


def add_person_to_graph(
    name: str,
    gender: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    location: Optional[str] = None,
    age: Optional[int] = None
) -> dict:
    """Add a person to both family graph and enhanced CRM."""
    store, _, crm, enhanced = _get_stores()
    
    # Check for existing in PersonStore
    existing = store.find_by_name(name)
    for p in existing:
        if p.name.lower() == name.lower():
            return {"success": True, "person_id": p.id, "name": name, "existing": True}
    
    # Split name into first/last
    name_parts = name.split()
    first_name = name_parts[0] if name_parts else name
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    
    # Add to PersonStore (for family graph)
    person = Person(
        name=name,
        gender=gender,
        phone=phone,
        email=email,
        location=location,
        age=age
    )
    person_id = store.add_person(person)
    
    # Add to EnhancedCRM (for CRM tab)
    profile = PersonProfile(
        first_name=first_name,
        last_name=last_name,
        gender=gender or "",
        age=age,
        phone=phone or "",
        email=email or "",
        city=location or "",  # Use location as city
    )
    enhanced.add_person(profile)
    
    # Add contact info to old CRM
    if phone or email:
        crm.add_contact(person_id, phone=phone, email=email)
    
    return {"success": True, "person_id": person_id, "name": name, "existing": False}


def add_relationship(person1_name: str, person2_name: str, relationship_type: str) -> dict:
    """Add a relationship between two people using fuzzy name matching."""
    store, graph, _, _ = _get_stores()

    # Use fuzzy matching MCP tool for better name resolution
    try:
        # Match person 1 using fuzzy matching
        response1 = requests.post(
            "http://localhost:8003/tools/fuzzy_match_person",
            json={"query": person1_name, "similarity_threshold": 0.75},
            timeout=10
        )
        match1_data = response1.json()

        # Match person 2 using fuzzy matching
        response2 = requests.post(
            "http://localhost:8003/tools/fuzzy_match_person",
            json={"query": person2_name, "similarity_threshold": 0.75},
            timeout=10
        )
        match2_data = response2.json()

        # Check if we found matches
        if not match1_data.get("success") or not match1_data.get("best_match"):
            reasoning = match1_data.get("reasoning", [])
            return {
                "success": False,
                "error": f"Person not found: {person1_name}",
                "reasoning": reasoning
            }

        if not match2_data.get("success") or not match2_data.get("best_match"):
            reasoning = match2_data.get("reasoning", [])
            return {
                "success": False,
                "error": f"Person not found: {person2_name}",
                "reasoning": reasoning
            }

        # Get person IDs from CRM matches (need to look up in PersonStore by name)
        person1_crm_name = match1_data["best_match"]["full_name"]
        person2_crm_name = match2_data["best_match"]["full_name"]

        # Look up in PersonStore by exact name match
        p1_matches = store.find_by_name(person1_crm_name)
        p2_matches = store.find_by_name(person2_crm_name)

        if not p1_matches:
            return {
                "success": False,
                "error": f"Person '{person1_crm_name}' found in CRM but not in PersonStore (graph database)",
                "reasoning": match1_data.get("reasoning", [])
            }
        if not p2_matches:
            return {
                "success": False,
                "error": f"Person '{person2_crm_name}' found in CRM but not in PersonStore (graph database)",
                "reasoning": match2_data.get("reasoning", [])
            }

        # Get exact person IDs
        p1_id = p1_matches[0].id
        p2_id = p2_matches[0].id

        # Add relationship to graph
        if relationship_type == "parent_child":
            graph.add_parent_child(p1_id, p2_id)
        elif relationship_type == "spouse":
            graph.add_spouse(p1_id, p2_id)
        elif relationship_type == "sibling":
            graph.add_sibling(p1_id, p2_id)
        else:
            return {"success": False, "error": f"Unknown relationship: {relationship_type}"}

        # Build detailed reasoning for UI display
        reasoning_steps = []
        reasoning_steps.append(f"🔍 FUZZY MATCHING FOR '{person1_name}' → '{person2_name}' relationship:")
        reasoning_steps.append(f"\n📌 Person 1: '{person1_name}' (query)")
        reasoning_steps.extend([f"  • {step}" for step in match1_data.get("reasoning", [])])
        reasoning_steps.append(f"  ✓ Matched to: '{person1_crm_name}' (confidence: {match1_data['best_match'].get('confidence', 0):.1%})")

        reasoning_steps.append(f"\n📌 Person 2: '{person2_name}' (query)")
        reasoning_steps.extend([f"  • {step}" for step in match2_data.get("reasoning", [])])
        reasoning_steps.append(f"  ✓ Matched to: '{person2_crm_name}' (confidence: {match2_data['best_match'].get('confidence', 0):.1%})")

        reasoning_steps.append(f"\n✅ Relationship created: {person1_crm_name} --[{relationship_type}]--> {person2_crm_name}")

        return {
            "success": True,
            "type": relationship_type,
            "person1_id": p1_id,
            "person2_id": p2_id,
            "person1_matched": person1_crm_name,
            "person2_matched": person2_crm_name,
            "person1_reasoning": match1_data.get("reasoning", []),
            "person2_reasoning": match2_data.get("reasoning", []),
            "person1_confidence": match1_data["best_match"].get("confidence"),
            "person2_confidence": match2_data["best_match"].get("confidence"),
            "detailed_reasoning": reasoning_steps  # NEW: Formatted reasoning for UI
        }

    except requests.RequestException as e:
        # Fallback to old method if MCP server is not available
        print(f"⚠️  Fuzzy matching MCP server unavailable, using fallback: {e}")

        p1_matches = store.find_by_name(person1_name)
        p2_matches = store.find_by_name(person2_name)

        if not p1_matches:
            return {"success": False, "error": f"Person not found: {person1_name}"}
        if not p2_matches:
            return {"success": False, "error": f"Person not found: {person2_name}"}

        p1_id = p1_matches[0].id
        p2_id = p2_matches[0].id

        if relationship_type == "parent_child":
            graph.add_parent_child(p1_id, p2_id)
        elif relationship_type == "spouse":
            graph.add_spouse(p1_id, p2_id)
        elif relationship_type == "sibling":
            graph.add_sibling(p1_id, p2_id)
        else:
            return {"success": False, "error": f"Unknown relationship: {relationship_type}"}

        return {"success": True, "type": relationship_type, "person1_id": p1_id, "person2_id": p2_id}


def get_family_tree(person_name: str) -> dict:
    """Get family tree for a person."""
    store, graph, _, _ = _get_stores()
    
    matches = store.find_by_name(person_name)
    if not matches:
        return {"success": False, "error": f"Person not found: {person_name}"}
    
    person = matches[0]
    tree = graph.get_family_tree(person.id)
    
    def get_names(ids):
        return [store.get_person(pid).name for pid in ids if store.get_person(pid)]
    
    return {
        "success": True,
        "person": person.name,
        "parents": get_names(tree["parents"]),
        "spouse": get_names(tree["spouse"]),
        "siblings": get_names(tree["siblings"]),
        "children": get_names(tree["children"])
    }


def list_all_persons() -> dict:
    """List all persons in the graph."""
    store, _, _, _ = _get_stores()
    persons = store.get_all()
    
    return {
        "success": True,
        "count": len(persons),
        "persons": [{"id": p.id, "name": p.name, "location": p.location} for p in persons]
    }


def delete_person_from_graph(person_id: int) -> dict:
    """Delete a person from both databases."""
    store, _, _, enhanced = _get_stores()
    
    person = store.get_person(person_id)
    if not person:
        return {"success": False, "error": "Person not found"}
    
    name = person.name
    
    # Delete from PersonStore
    deleted = store.delete_person(person_id)
    
    # Try to delete from EnhancedCRM by name match
    name_parts = name.split()
    first_name = name_parts[0] if name_parts else name
    enhanced_persons = enhanced.search(query=first_name)
    for ep in enhanced_persons:
        if ep.full_name.lower() == name.lower():
            enhanced.delete_person(ep.id)
            break
    
    return {"success": deleted, "name": name, "person_id": person_id}
