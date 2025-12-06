"""Main FamilyGraph facade combining all operations."""

from src.graph.graphlite.client import GraphLiteClient
from src.graph.graphlite.config import GraphLiteConfig
from src.graph.family.person import PersonOperations
from src.graph.family.relationships import RelationshipOperations
from src.graph.family.queries import FamilyQueries
from src.graph.models import PersonNode


class FamilyGraph:
    """
    Main interface for family graph operations.
    
    Combines person, relationship, and query operations.
    
    Usage:
        graph = FamilyGraph()
        graph.add_person("Ramesh", gender="M", family_name="Mattegunta")
        graph.add_spouse("Ramesh", "Padma")
        tree = graph.get_family_tree("Ramesh")
    """
    
    def __init__(self, config: GraphLiteConfig = None):
        self.config = config or GraphLiteConfig()
        self.client = GraphLiteClient(self.config)
        self.client.init_schema()
        
        # Compose operations
        self.persons = PersonOperations(self.client)
        self.relationships = RelationshipOperations(self.client, self.persons)
        self.queries = FamilyQueries(self.client)
    
    # ─────────────────────────────────────────
    # Person operations (delegated)
    # ─────────────────────────────────────────
    
    def add_person(self, name: str, **kwargs) -> str:
        return self.persons.add(name, **kwargs)
    
    def get_person(self, name: str) -> PersonNode:
        return self.persons.get_by_name(name)
    
    def get_all_persons(self) -> list[PersonNode]:
        return self.persons.get_all()
    
    def update_person(self, name: str, **kwargs) -> bool:
        return self.persons.update(name, **kwargs)
    
    def delete_person(self, name: str) -> bool:
        return self.persons.delete(name)
    
    # ─────────────────────────────────────────
    # Relationship operations (delegated)
    # ─────────────────────────────────────────
    
    def add_parent_child(self, parent: str, child: str) -> bool:
        return self.relationships.add_parent_child(parent, child)
    
    def add_spouse(self, person1: str, person2: str) -> bool:
        return self.relationships.add_spouse(person1, person2)
    
    def add_sibling(self, person1: str, person2: str) -> bool:
        return self.relationships.add_sibling(person1, person2)
    
    def get_all_relationships(self) -> list[dict]:
        return self.relationships.get_all()
    
    # ─────────────────────────────────────────
    # Query operations (delegated)
    # ─────────────────────────────────────────
    
    def get_children(self, name: str) -> list[PersonNode]:
        return self.queries.get_children(name)
    
    def get_parents(self, name: str) -> list[PersonNode]:
        return self.queries.get_parents(name)
    
    def get_spouse(self, name: str) -> list[PersonNode]:
        return self.queries.get_spouse(name)
    
    def get_siblings(self, name: str) -> list[PersonNode]:
        return self.queries.get_siblings(name)
    
    def get_family_tree(self, name: str) -> dict:
        return self.queries.get_family_tree(name)
    
    def get_family_by_surname(self, family_name: str) -> list[PersonNode]:
        return self.queries.get_by_family_name(family_name)
