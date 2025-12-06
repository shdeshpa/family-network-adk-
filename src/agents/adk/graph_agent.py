"""Graph Agent - manages family graph operations."""

from src.agents.adk.tools import (
    add_person_to_graph,
    add_relationship,
    get_family_tree,
    list_all_persons
)


class GraphAgent:
    """Agent for managing the family graph database."""
    
    def build_from_extraction(self, extraction: dict) -> dict:
        """Build graph from extraction results."""
        if not extraction.get("success"):
            return {"success": False, "error": "Invalid extraction"}
        
        results = {
            "success": True,
            "persons_created": [],
            "relationships_created": [],
            "errors": []
        }
        
        for person_data in extraction.get("persons", []):
            name = person_data.get("name")
            if not name:
                continue
            result = add_person_to_graph(
                name=name,
                gender=person_data.get("gender"),
                phone=person_data.get("phone"),
                email=person_data.get("email"),
                location=person_data.get("location")
            )
            if result.get("success"):
                results["persons_created"].append(result)
            else:
                results["errors"].append(f"Person {name}: {result.get('error')}")
        
        for rel in extraction.get("relationships", []):
            rel_type = rel.get("type")
            person1 = rel.get("person1")
            person2 = rel.get("person2")
            if not all([rel_type, person1, person2]):
                continue
            result = add_relationship(person1, person2, rel_type)
            if result.get("success"):
                results["relationships_created"].append(result)
            else:
                results["errors"].append(f"Relationship: {result.get('error')}")
        
        return results
    
    def query(self, person_name: str) -> dict:
        return get_family_tree(person_name)
    
    def list_all(self) -> dict:
        return list_all_persons()