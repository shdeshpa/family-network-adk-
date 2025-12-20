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
            "errors": [],
            "detailed_reasoning": []  # NEW: Capture all reasoning steps
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
                # Add reasoning for person creation
                results["detailed_reasoning"].append(f"✅ Added person: {name}")
            else:
                results["errors"].append(f"Person {name}: {result.get('error')}")
                results["detailed_reasoning"].append(f"❌ Failed to add person {name}: {result.get('error')}")

        for rel in extraction.get("relationships", []):
            rel_type = rel.get("type")
            person1 = rel.get("person1")
            person2 = rel.get("person2")
            if not all([rel_type, person1, person2]):
                continue
            result = add_relationship(person1, person2, rel_type)
            if result.get("success"):
                results["relationships_created"].append(result)
                # Capture detailed fuzzy matching reasoning
                if "detailed_reasoning" in result:
                    results["detailed_reasoning"].extend(result["detailed_reasoning"])
            else:
                error_msg = result.get("error", "Unknown error")
                results["errors"].append(f"Relationship: {error_msg}")
                results["detailed_reasoning"].append(f"\n❌ RELATIONSHIP FAILED: {person1} → {person2}")
                results["detailed_reasoning"].append(f"   Error: {error_msg}")
                # Include reasoning from failed fuzzy match if available
                if result.get("reasoning"):
                    results["detailed_reasoning"].extend([f"   {r}" for r in result.get("reasoning", [])])

        return results
    
    def query(self, person_name: str) -> dict:
        return get_family_tree(person_name)
    
    def list_all(self) -> dict:
        return list_all_persons()