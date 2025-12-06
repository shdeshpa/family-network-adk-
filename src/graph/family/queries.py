"""Family tree queries."""

from src.graph.models import PersonNode
from src.graph.graphlite.client import GraphLiteClient


class FamilyQueries:
    """Query operations for family relationships."""
    
    def __init__(self, client: GraphLiteClient):
        self.client = client
    
    def _escape(self, value: str) -> str:
        return value.replace("'", "\\'").replace('"', '\\"') if value else ""
    
    def _rows_to_persons(self, rows: list[dict], prefix: str = "p") -> list[PersonNode]:
        """Convert rows to PersonNode list."""
        return [
            PersonNode(
                name=r.get(f'{prefix}.name', ''),
                gender=r.get(f'{prefix}.gender'),
                family_name=r.get(f'{prefix}.family_name')
            )
            for r in rows
        ]
    
    def get_children(self, person_name: str) -> list[PersonNode]:
        """Get children of a person."""
        query = f"MATCH (p:Person {{name: '{self._escape(person_name)}'}})-[:PARENT_OF]->(c:Person) RETURN c.name, c.gender, c.family_name"
        result = self.client.query(query)
        return self._rows_to_persons(result.rows, 'c') if result.success else []
    
    def get_parents(self, person_name: str) -> list[PersonNode]:
        """Get parents of a person."""
        query = f"MATCH (p:Person)-[:PARENT_OF]->(c:Person {{name: '{self._escape(person_name)}'}}) RETURN p.name, p.gender, p.family_name"
        result = self.client.query(query)
        return self._rows_to_persons(result.rows, 'p') if result.success else []
    
    def get_spouse(self, person_name: str) -> list[PersonNode]:
        """Get spouse(s) of a person."""
        query = f"MATCH (p:Person {{name: '{self._escape(person_name)}'}})-[:SPOUSE_OF]->(s:Person) RETURN s.name, s.gender, s.family_name"
        result = self.client.query(query)
        return self._rows_to_persons(result.rows, 's') if result.success else []
    
    def get_siblings(self, person_name: str) -> list[PersonNode]:
        """Get siblings of a person."""
        query = f"MATCH (p:Person {{name: '{self._escape(person_name)}'}})-[:SIBLING_OF]->(s:Person) RETURN s.name, s.gender, s.family_name"
        result = self.client.query(query)
        return self._rows_to_persons(result.rows, 's') if result.success else []
    
    def get_family_tree(self, person_name: str) -> dict:
        """Get complete family tree."""
        from src.graph.family.person import PersonOperations
        persons = PersonOperations(self.client)
        
        return {
            "person": persons.get_by_name(person_name),
            "parents": self.get_parents(person_name),
            "spouse": self.get_spouse(person_name),
            "children": self.get_children(person_name),
            "siblings": self.get_siblings(person_name)
        }
    
    def get_by_family_name(self, family_name: str) -> list[PersonNode]:
        """Get all persons with a family name."""
        query = f"MATCH (p:Person {{family_name: '{self._escape(family_name)}'}}) RETURN p.name, p.gender, p.family_name"
        result = self.client.query(query)
        return self._rows_to_persons(result.rows, 'p') if result.success else []
