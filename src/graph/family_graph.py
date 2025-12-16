"""Family relationship graph using GraphLite."""

from pathlib import Path
from typing import Optional
from enum import Enum

from graphlite import connect, V

from src.config import settings


class RelationType(str, Enum):
    """Types of family relationships."""
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"
    SPOUSE_OF = "spouse_of"
    SIBLING_OF = "sibling_of"


class FamilyGraph:
    """Manage family relationships with GraphLite."""
    
    RELATION_TYPES = ["parent_of", "child_of", "spouse_of", "sibling_of"]
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.database.graph_db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.graph = connect(self.db_path, graphs=self.RELATION_TYPES)
    
    def add_parent_child(self, parent_id: int, child_id: int):
        """Add parent-child relationship (bidirectional)."""
        with self.graph.transaction() as tr:
            tr.store(V(parent_id).parent_of(child_id))
            tr.store(V(child_id).child_of(parent_id))
    
    def add_spouse(self, person1_id: int, person2_id: int):
        """Add spouse relationship (bidirectional)."""
        with self.graph.transaction() as tr:
            tr.store(V(person1_id).spouse_of(person2_id))
            tr.store(V(person2_id).spouse_of(person1_id))
    
    def add_sibling(self, person1_id: int, person2_id: int):
        """Add sibling relationship (bidirectional)."""
        with self.graph.transaction() as tr:
            tr.store(V(person1_id).sibling_of(person2_id))
            tr.store(V(person2_id).sibling_of(person1_id))
    
    def get_children(self, person_id: int) -> list[int]:
        """Get all children of a person."""
        return self.graph.find(V(person_id).parent_of).to(list)
    
    def get_parents(self, person_id: int) -> list[int]:
        """Get all parents of a person."""
        return self.graph.find(V(person_id).child_of).to(list)
    
    def get_spouse(self, person_id: int) -> list[int]:
        """Get spouse(s) of a person."""
        return self.graph.find(V(person_id).spouse_of).to(list)
    
    def get_siblings(self, person_id: int) -> list[int]:
        """Get all siblings of a person."""
        return self.graph.find(V(person_id).sibling_of).to(list)
    
    def get_grandchildren(self, person_id: int) -> list[int]:
        """Get all grandchildren of a person."""
        return self.graph.find(V(person_id).parent_of).traverse(V().parent_of).to(list)
    
    def get_grandparents(self, person_id: int) -> list[int]:
        """Get all grandparents of a person."""
        return self.graph.find(V(person_id).child_of).traverse(V().child_of).to(list)
    
    def get_all_descendants(self, person_id: int, max_depth: int = 5) -> set[int]:
        """Get all descendants up to max_depth generations."""
        descendants = set()
        current_gen = {person_id}
        
        for _ in range(max_depth):
            next_gen = set()
            for pid in current_gen:
                children = self.get_children(pid)
                next_gen.update(children)
            if not next_gen:
                break
            descendants.update(next_gen)
            current_gen = next_gen
        
        return descendants
    
    def get_all_ancestors(self, person_id: int, max_depth: int = 5) -> set[int]:
        """Get all ancestors up to max_depth generations."""
        ancestors = set()
        current_gen = {person_id}
        
        for _ in range(max_depth):
            next_gen = set()
            for pid in current_gen:
                parents = self.get_parents(pid)
                next_gen.update(parents)
            if not next_gen:
                break
            ancestors.update(next_gen)
            current_gen = next_gen
        
        return ancestors
    
    def get_family_tree(self, person_id: int) -> dict:
        """Get complete family tree structure for a person."""
        return {
            "person_id": person_id,
            "parents": self.get_parents(person_id),
            "spouse": self.get_spouse(person_id),
            "siblings": self.get_siblings(person_id),
            "children": self.get_children(person_id),
            "grandparents": self.get_grandparents(person_id),
            "grandchildren": self.get_grandchildren(person_id)
        }

    def delete_person_relationships(self, person_id: int) -> bool:
        """Delete all relationships for a person before removing them.

        This prevents dangling edges in the graph that would break tree visualization.
        """
        try:
            with self.graph.transaction() as tr:
                # Get all related persons first
                children = self.get_children(person_id)
                parents = self.get_parents(person_id)
                spouses = self.get_spouse(person_id)
                siblings = self.get_siblings(person_id)

                # Delete parent-child edges (both directions)
                for child_id in children:
                    tr.delete(V(person_id).parent_of(child_id))
                    tr.delete(V(child_id).child_of(person_id))

                for parent_id in parents:
                    tr.delete(V(person_id).child_of(parent_id))
                    tr.delete(V(parent_id).parent_of(person_id))

                # Delete spouse edges (both directions)
                for spouse_id in spouses:
                    tr.delete(V(person_id).spouse_of(spouse_id))
                    tr.delete(V(spouse_id).spouse_of(person_id))

                # Delete sibling edges (both directions)
                for sibling_id in siblings:
                    tr.delete(V(person_id).sibling_of(sibling_id))
                    tr.delete(V(sibling_id).sibling_of(person_id))

            return True
        except Exception as e:
            print(f"Error deleting relationships for person {person_id}: {e}")
            return False