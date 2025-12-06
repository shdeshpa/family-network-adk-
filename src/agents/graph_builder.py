"""Graph builder agent - creates family graph from extracted entities."""

from typing import Optional

from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.crm_store import CRMStore
from src.models import Person


class GraphBuilderAgent:
    """Build family graph from extracted entities."""
    
    def __init__(
        self,
        person_store: Optional[PersonStore] = None,
        family_graph: Optional[FamilyGraph] = None,
        crm_store: Optional[CRMStore] = None
    ):
        self.person_store = person_store or PersonStore()
        self.family_graph = family_graph or FamilyGraph()
        self.crm_store = crm_store or CRMStore()
        self._name_to_id: dict[str, int] = {}
    
    def build_from_extraction(self, extraction: dict) -> dict:
        """
        Build graph from entity extraction results.
        
        Args:
            extraction: Output from EntityExtractorAgent.extract_entities()
            
        Returns:
            dict with created person IDs and relationship counts
        """
        if not extraction.get("success"):
            return {"success": False, "error": "Invalid extraction data"}
        
        persons_created = []
        relationships_created = []
        
        # Step 1: Create all persons first
        for person_data in extraction.get("persons", []):
            result = self._create_person(person_data)
            if result["success"]:
                persons_created.append(result)
        
        # Step 2: Create relationships
        for rel_data in extraction.get("relationships", []):
            result = self._create_relationship(rel_data)
            if result["success"]:
                relationships_created.append(result)
        
        return {
            "success": True,
            "persons_created": len(persons_created),
            "relationships_created": len(relationships_created),
            "persons": persons_created,
            "relationships": relationships_created,
            "name_to_id_map": self._name_to_id.copy()
        }
    
    def _create_person(self, person_data: dict) -> dict:
        """Create a person from extracted data."""
        name = person_data.get("name", "").strip()
        if not name:
            return {"success": False, "error": "No name provided"}
        
        # Check if person already exists (by name match)
        existing = self.person_store.find_by_name(name)
        if existing:
            # Use first exact match or close match
            for p in existing:
                if p.name.lower() == name.lower():
                    self._name_to_id[name.lower()] = p.id
                    return {"success": True, "person_id": p.id, "name": name, "existing": True}
        
        # Create new person
        person = Person(
            name=name,
            gender=person_data.get("gender"),
            phone=person_data.get("phone"),
            email=person_data.get("email"),
            location=person_data.get("location"),
            interests=person_data.get("interests", [])
        )
        
        person_id = self.person_store.add_person(person)
        self._name_to_id[name.lower()] = person_id
        
        # Add to CRM if contact info exists
        if person.phone or person.email:
            self.crm_store.add_contact(person_id, phone=person.phone, email=person.email)
        
        # Add interests to CRM
        for interest in person.interests:
            self.crm_store.add_interest(person_id, interest)
        
        return {"success": True, "person_id": person_id, "name": name, "existing": False}
    
    def _create_relationship(self, rel_data: dict) -> dict:
        """Create a relationship from extracted data."""
        rel_type = rel_data.get("type", "").lower()
        
        if rel_type == "parent_child":
            parent_name = rel_data.get("parent", "").lower()
            child_name = rel_data.get("child", "").lower()
            
            parent_id = self._name_to_id.get(parent_name)
            child_id = self._name_to_id.get(child_name)
            
            if parent_id and child_id:
                self.family_graph.add_parent_child(parent_id, child_id)
                return {"success": True, "type": "parent_child", "parent_id": parent_id, "child_id": child_id}
            return {"success": False, "error": f"Could not find IDs for {parent_name} or {child_name}"}
        
        elif rel_type == "spouse":
            person1_name = rel_data.get("person1", "").lower()
            person2_name = rel_data.get("person2", "").lower()
            
            person1_id = self._name_to_id.get(person1_name)
            person2_id = self._name_to_id.get(person2_name)
            
            if person1_id and person2_id:
                self.family_graph.add_spouse(person1_id, person2_id)
                return {"success": True, "type": "spouse", "person1_id": person1_id, "person2_id": person2_id}
            return {"success": False, "error": f"Could not find IDs for {person1_name} or {person2_name}"}
        
        elif rel_type == "sibling":
            person1_name = rel_data.get("person1", "").lower()
            person2_name = rel_data.get("person2", "").lower()
            
            person1_id = self._name_to_id.get(person1_name)
            person2_id = self._name_to_id.get(person2_name)
            
            if person1_id and person2_id:
                self.family_graph.add_sibling(person1_id, person2_id)
                return {"success": True, "type": "sibling", "person1_id": person1_id, "person2_id": person2_id}
            return {"success": False, "error": f"Could not find IDs for {person1_name} or {person2_name}"}
        
        return {"success": False, "error": f"Unknown relationship type: {rel_type}"}
    
    def get_person_id(self, name: str) -> Optional[int]:
        """Get person ID by name."""
        return self._name_to_id.get(name.lower())