"""Relationship operations between persons."""

from src.graph.graphlite.client import GraphLiteClient
from src.graph.family.person import PersonOperations


class RelationshipOperations:
    """Operations for family relationships."""
    
    def __init__(self, client: GraphLiteClient, persons: PersonOperations):
        self.client = client
        self.persons = persons
    
    def _escape(self, value: str) -> str:
        return value.replace("'", "\\'").replace('"', '\\"') if value else ""
    
    def add_parent_child(self, parent_name: str, child_name: str) -> bool:
        """Add parent-child relationship with auto-derived specifics."""
        parent = self.persons.get_by_name(parent_name)
        child = self.persons.get_by_name(child_name)
        
        # Derive specific labels from gender
        parent_specific = "father" if parent and parent.gender == "M" else "mother" if parent and parent.gender == "F" else "parent"
        child_specific = "son" if child and child.gender == "M" else "daughter" if child and child.gender == "F" else "child"
        
        # Parent -> Child
        q1 = f"MATCH (a:Person {{name: '{self._escape(parent_name)}'}}), (b:Person {{name: '{self._escape(child_name)}'}}) INSERT (a)-[:PARENT_OF {{specific: '{parent_specific}'}}]->(b)"
        result = self.client.execute(q1)
        
        # Child -> Parent (reciprocal)
        if result.success:
            q2 = f"MATCH (a:Person {{name: '{self._escape(child_name)}'}}), (b:Person {{name: '{self._escape(parent_name)}'}}) INSERT (a)-[:CHILD_OF {{specific: '{child_specific}'}}]->(b)"
            self.client.execute(q2)
        
        return result.success
    
    def add_spouse(self, person1_name: str, person2_name: str) -> bool:
        """Add bidirectional spouse relationship."""
        p1 = self.persons.get_by_name(person1_name)
        p2 = self.persons.get_by_name(person2_name)
        
        s1 = "husband" if p1 and p1.gender == "M" else "wife" if p1 and p1.gender == "F" else "spouse"
        s2 = "husband" if p2 and p2.gender == "M" else "wife" if p2 and p2.gender == "F" else "spouse"
        
        q1 = f"MATCH (a:Person {{name: '{self._escape(person1_name)}'}}), (b:Person {{name: '{self._escape(person2_name)}'}}) INSERT (a)-[:SPOUSE_OF {{specific: '{s1}'}}]->(b)"
        result = self.client.execute(q1)
        
        if result.success:
            q2 = f"MATCH (a:Person {{name: '{self._escape(person2_name)}'}}), (b:Person {{name: '{self._escape(person1_name)}'}}) INSERT (a)-[:SPOUSE_OF {{specific: '{s2}'}}]->(b)"
            self.client.execute(q2)
            
            # Update marital status
            self.persons.update(person1_name, marital_status="Married")
            self.persons.update(person2_name, marital_status="Married")
        
        return result.success
    
    def add_sibling(self, person1_name: str, person2_name: str) -> bool:
        """Add bidirectional sibling relationship."""
        p1 = self.persons.get_by_name(person1_name)
        p2 = self.persons.get_by_name(person2_name)
        
        s1 = "brother" if p1 and p1.gender == "M" else "sister" if p1 and p1.gender == "F" else "sibling"
        s2 = "brother" if p2 and p2.gender == "M" else "sister" if p2 and p2.gender == "F" else "sibling"
        
        q1 = f"MATCH (a:Person {{name: '{self._escape(person1_name)}'}}), (b:Person {{name: '{self._escape(person2_name)}'}}) INSERT (a)-[:SIBLING_OF {{specific: '{s1}'}}]->(b)"
        result = self.client.execute(q1)
        
        if result.success:
            q2 = f"MATCH (a:Person {{name: '{self._escape(person2_name)}'}}), (b:Person {{name: '{self._escape(person1_name)}'}}) INSERT (a)-[:SIBLING_OF {{specific: '{s2}'}}]->(b)"
            self.client.execute(q2)
        
        return result.success
    
    def get_all(self) -> list[dict]:
        """Get all relationships."""
        query = "MATCH (a:Person)-[r]->(b:Person) RETURN a.name, type(r), r.specific, b.name"
        result = self.client.query(query)
        
        if not result.success:
            return []
        
        return [
            {"from": r.get('a.name'), "type": r.get('type(r)'), "specific": r.get('r.specific'), "to": r.get('b.name')}
            for r in result.rows
        ]
