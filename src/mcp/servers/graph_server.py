"""GraphLite MCP server with robust parameter handling."""

from mcp.server.fastmcp import FastMCP
from typing import Optional, List
from src.graph import FamilyGraph
from src.mcp.servers.nlp_server import infer_gender as _infer_gender, extract_family_name as _extract_family_name

mcp = FastMCP("graph-server")

_graph: Optional[FamilyGraph] = None

def get_graph() -> FamilyGraph:
    global _graph
    if _graph is None:
        _graph = FamilyGraph()
    return _graph


def _resolve_value(val) -> Optional[str]:
    """Resolve a value, executing nested function calls if needed."""
    if val is None:
        return None
    
    if isinstance(val, dict):
        if 'function_name' in val:
            func_name = val['function_name']
            args = val.get('arguments', {})
            
            if func_name == 'infer_gender':
                name = _resolve_value(args.get('name', ''))
                result = _infer_gender(name or '')
                return result.get('gender')
            elif func_name == 'extract_family_name':
                names = args.get('names', [])
                result = _extract_family_name(names)
                return result.get('family_name')
            else:
                return str(val)
        else:
            return val.get('name', str(val))
    
    return str(val) if val else None


@mcp.tool()
def add_person(
    name: str,
    gender: Optional[str] = None,
    family_name: Optional[str] = None,
    location: Optional[str] = None,
    marital_status: Optional[str] = None
) -> dict:
    """Add or update a person in the graph."""
    graph = get_graph()
    
    # Resolve nested function calls
    name = _resolve_value(name) or ""
    gender = _resolve_value(gender)
    family_name = _resolve_value(family_name)
    location = _resolve_value(location)
    marital_status = _resolve_value(marital_status)
    
    if not name:
        return {"success": False, "error": "Name required"}
    
    existing = graph.get_person(name)
    if existing:
        graph.update_person(name, 
            gender=gender or existing.gender,
            family_name=family_name or existing.family_name,
            location=location or existing.location,
            marital_status=marital_status or existing.marital_status)
        return {"success": True, "action": "updated", "name": name, "gender": gender}
    
    result = graph.add_person(name=name, gender=gender, family_name=family_name,
        location=location, marital_status=marital_status)
    return {"success": bool(result), "action": "created", "name": name, "gender": gender}


@mcp.tool()
def add_spouse(person1: str, person2: str) -> dict:
    """Add spouse relationship (bidirectional)."""
    graph = get_graph()
    p1 = _resolve_value(person1) or ""
    p2 = _resolve_value(person2) or ""
    success = graph.add_spouse(p1, p2)
    return {"success": success, "type": "spouse", "person1": p1, "person2": p2}


@mcp.tool()
def add_parent_child(parent: str, child: str) -> dict:
    """Add parent-child relationship."""
    graph = get_graph()
    p = _resolve_value(parent) or ""
    c = _resolve_value(child) or ""
    success = graph.add_parent_child(p, c)
    return {"success": success, "type": "parent_child", "parent": p, "child": c}


@mcp.tool()
def add_sibling(person1: str, person2: str) -> dict:
    """Add sibling relationship (bidirectional)."""
    graph = get_graph()
    p1 = _resolve_value(person1) or ""
    p2 = _resolve_value(person2) or ""
    success = graph.add_sibling(p1, p2)
    return {"success": success, "type": "sibling", "person1": p1, "person2": p2}


@mcp.tool()
def get_person(name: str) -> dict:
    """Get person details from graph."""
    graph = get_graph()
    n = _resolve_value(name) or ""
    person = graph.get_person(n)
    
    if person:
        return {"found": True, "name": person.name, "gender": person.gender,
            "family_name": person.family_name, "location": person.location}
    return {"found": False, "name": n}


@mcp.tool()
def get_all_persons() -> dict:
    """Get all persons from graph."""
    graph = get_graph()
    persons = graph.get_all_persons()
    return {"count": len(persons), "persons": [
        {"name": p.name, "gender": p.gender, "family_name": p.family_name} for p in persons
    ]}


@mcp.tool()
def get_all_relationships() -> dict:
    """Get all relationships from graph."""
    graph = get_graph()
    rels = graph.get_all_relationships()
    return {"count": len(rels), "relationships": rels}


@mcp.tool()
def verify_storage(persons: List[str], relationships: List[dict]) -> dict:
    """Verify persons and relationships were stored correctly."""
    graph = get_graph()
    
    person_results = []
    for p in persons:
        name = _resolve_value(p) or ""
        stored = graph.get_person(name) is not None
        person_results.append({"name": name, "stored": stored})
    
    all_rels = graph.get_all_relationships()
    rel_results = []
    for rel in relationships:
        if isinstance(rel, dict):
            p1 = _resolve_value(rel.get("person1", rel.get("from", ""))) or ""
            p2 = _resolve_value(rel.get("person2", rel.get("to", ""))) or ""
            found = any(r["from"] == p1 and r["to"] == p2 for r in all_rels)
            rel_results.append({"person1": p1, "person2": p2, "stored": found})
    
    all_ok = all(p["stored"] for p in person_results) and all(r["stored"] for r in rel_results)
    return {"success": all_ok, "persons": person_results, "relationships": rel_results}


if __name__ == "__main__":
    mcp.run()
