"""Person operations for FamilyGraph."""

from typing import Optional, List
from src.graph.models import PersonNode
from src.graph.graphlite.client import GraphLiteClient


class PersonOperations:
    """CRUD operations for Person nodes."""
    
    def __init__(self, client: GraphLiteClient):
        self.client = client
    
    def _escape(self, value) -> str:
        """Escape string for GQL query."""
        if value is None:
            return ""
        if isinstance(value, dict):
            value = value.get('name', str(value))
        return str(value).replace("'", "\\'").replace('"', '\\"')
    
    def _row_to_person(self, row: dict) -> PersonNode:
        """Convert query row to PersonNode."""
        return PersonNode(
            name=row.get('p.name') or '',
            gender=row.get('p.gender'),
            family_name=row.get('p.family_name'),
            age=row.get('p.age'),
            location=row.get('p.location'),
            phone=row.get('p.phone'),
            email=row.get('p.email'),
            marital_status=row.get('p.marital_status'),
            gothra=row.get('p.gothra')
        )
    
    def add(self, name: str, gender: Optional[str] = None, family_name: Optional[str] = None,
            age: Optional[int] = None, location: Optional[str] = None, 
            phone: Optional[str] = None, email: Optional[str] = None,
            marital_status: Optional[str] = None, gothra: Optional[str] = None) -> Optional[str]:
        """Add a person to the graph."""
        # Check if exists
        existing = self.get_by_name(name)
        if existing:
            return existing.name
        
        props = [f"name: '{self._escape(name)}'"]
        if gender: props.append(f"gender: '{self._escape(gender)}'")
        if family_name: props.append(f"family_name: '{self._escape(family_name)}'")
        if age: props.append(f"age: {age}")
        if location: props.append(f"location: '{self._escape(location)}'")
        if phone: props.append(f"phone: '{self._escape(phone)}'")
        if email: props.append(f"email: '{self._escape(email)}'")
        if marital_status: props.append(f"marital_status: '{self._escape(marital_status)}'")
        if gothra: props.append(f"gothra: '{self._escape(gothra)}'")
        
        query = f"INSERT (:Person {{{', '.join(props)}}})"
        result = self.client.execute(query)
        return name if result.success else None
    
    def get_by_name(self, name: str) -> Optional[PersonNode]:
        """Get person by exact name."""
        query = f"MATCH (p:Person {{name: '{self._escape(name)}'}}) RETURN p.name, p.gender, p.family_name, p.age, p.location, p.phone, p.email, p.marital_status, p.gothra"
        result = self.client.query(query)
        
        if result.success and result.rows:
            return self._row_to_person(result.rows[0])
        return None
    
    def get_all(self) -> List[PersonNode]:
        """Get all persons."""
        query = "MATCH (p:Person) RETURN p.name, p.gender, p.family_name, p.age, p.location, p.phone, p.email, p.marital_status, p.gothra"
        result = self.client.query(query)
        
        if result.success:
            return [self._row_to_person(row) for row in result.rows]
        return []
    
    def search(self, name_pattern: str) -> List[PersonNode]:
        """Search persons by partial name."""
        query = f"MATCH (p:Person) WHERE p.name CONTAINS '{self._escape(name_pattern)}' RETURN p.name, p.gender, p.family_name, p.age, p.location"
        result = self.client.query(query)
        
        if result.success:
            return [self._row_to_person(row) for row in result.rows]
        return []
    
    def update(self, name: str, **kwargs) -> bool:
        """Update person properties."""
        sets = []
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, int):
                    sets.append(f"p.{key} = {value}")
                else:
                    sets.append(f"p.{key} = '{self._escape(value)}'")
        
        if not sets:
            return False
        
        query = f"MATCH (p:Person {{name: '{self._escape(name)}'}}) SET {', '.join(sets)}"
        result = self.client.execute(query)
        return result.success
    
    def delete(self, name: str) -> bool:
        """Delete person and their relationships."""
        query = f"MATCH (p:Person {{name: '{self._escape(name)}'}}) DETACH DELETE p"
        result = self.client.execute(query)
        return result.success
