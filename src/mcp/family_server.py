"""FastMCP server for family graph and CRM operations."""

from typing import Optional

from fastmcp import FastMCP

from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.crm_store import CRMStore
from src.models import Person

# Create MCP server
mcp = FastMCP(
    "family-network-server",
    instructions="Family network management: persons, relationships, CRM"
)

# Lazy-initialized services
_person_store: Optional[PersonStore] = None
_family_graph: Optional[FamilyGraph] = None
_crm_store: Optional[CRMStore] = None


def get_person_store() -> PersonStore:
    global _person_store
    if _person_store is None:
        _person_store = PersonStore()
    return _person_store


def get_family_graph() -> FamilyGraph:
    global _family_graph
    if _family_graph is None:
        _family_graph = FamilyGraph()
    return _family_graph


def get_crm_store() -> CRMStore:
    global _crm_store
    if _crm_store is None:
        _crm_store = CRMStore()
    return _crm_store


# ============ Person Tools ============

@mcp.tool()
def add_person(
    name: str,
    gender: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    location: Optional[str] = None
) -> dict:
    """Add a new person to the family network."""
    person = Person(
        name=name,
        gender=gender,
        phone=phone,
        email=email,
        location=location
    )
    person_id = get_person_store().add_person(person)
    
    # Also add to CRM if contact info provided
    if phone or email:
        get_crm_store().add_contact(person_id, phone=phone, email=email)
    
    return {"success": True, "person_id": person_id, "name": name}


@mcp.tool()
def get_person(person_id: int) -> dict:
    """Get person details by ID."""
    person = get_person_store().get_person(person_id)
    if person:
        return {"success": True, "person": person.model_dump()}
    return {"success": False, "error": "Person not found"}


@mcp.tool()
def find_persons(name: str) -> dict:
    """Find persons by name (partial match)."""
    persons = get_person_store().find_by_name(name)
    return {
        "success": True,
        "count": len(persons),
        "persons": [p.model_dump() for p in persons]
    }


# ============ Relationship Tools ============

@mcp.tool()
def add_parent_child(parent_id: int, child_id: int) -> dict:
    """Add parent-child relationship."""
    get_family_graph().add_parent_child(parent_id, child_id)
    return {"success": True, "parent_id": parent_id, "child_id": child_id}


@mcp.tool()
def add_spouse(person1_id: int, person2_id: int) -> dict:
    """Add spouse relationship."""
    get_family_graph().add_spouse(person1_id, person2_id)
    return {"success": True, "person1_id": person1_id, "person2_id": person2_id}


@mcp.tool()
def add_sibling(person1_id: int, person2_id: int) -> dict:
    """Add sibling relationship."""
    get_family_graph().add_sibling(person1_id, person2_id)
    return {"success": True, "person1_id": person1_id, "person2_id": person2_id}


@mcp.tool()
def get_family_tree(person_id: int) -> dict:
    """Get complete family tree for a person."""
    tree = get_family_graph().get_family_tree(person_id)
    return {"success": True, "tree": tree}


@mcp.tool()
def get_relatives(person_id: int, relation: str) -> dict:
    """
    Get relatives of a specific type.
    
    Args:
        person_id: The person's ID
        relation: One of: parents, children, spouse, siblings, grandparents, grandchildren
    """
    graph = get_family_graph()
    
    relation_map = {
        "parents": graph.get_parents,
        "children": graph.get_children,
        "spouse": graph.get_spouse,
        "siblings": graph.get_siblings,
        "grandparents": graph.get_grandparents,
        "grandchildren": graph.get_grandchildren
    }
    
    if relation not in relation_map:
        return {"success": False, "error": f"Unknown relation: {relation}"}
    
    ids = relation_map[relation](person_id)
    return {"success": True, "relation": relation, "person_ids": ids}


# ============ CRM Tools ============

@mcp.tool()
def add_interest(person_id: int, interest: str) -> dict:
    """Add an interest to a person's profile."""
    added = get_crm_store().add_interest(person_id, interest)
    return {"success": added, "person_id": person_id, "interest": interest}


@mcp.tool()
def find_by_interest(interest: str) -> dict:
    """Find all persons with a specific interest."""
    person_ids = get_crm_store().find_by_interest(interest)
    return {"success": True, "interest": interest, "person_ids": person_ids}


@mcp.tool()
def find_by_location(location: str) -> dict:
    """Find all persons in a location."""
    person_ids = get_crm_store().find_by_location(location)
    return {"success": True, "location": location, "person_ids": person_ids}


@mcp.tool()
def log_interaction(person_id: int, interaction_type: str, notes: str = None) -> dict:
    """Log an interaction with a person (call, visit, email, etc.)."""
    interaction_id = get_crm_store().add_interaction(person_id, interaction_type, notes)
    return {"success": True, "interaction_id": interaction_id}


@mcp.tool()
def get_contact_info(person_id: int) -> dict:
    """Get contact information and interaction history."""
    contact = get_crm_store().get_contact(person_id)
    interactions = get_crm_store().get_interactions(person_id)
    interests = get_crm_store().get_interests(person_id)
    
    return {
        "success": True,
        "contact": contact,
        "interactions": interactions,
        "interests": interests
    }


def run_server(host: str = "0.0.0.0", port: int = 8002):
    """Run the MCP server with HTTP transport."""
    mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    run_server()