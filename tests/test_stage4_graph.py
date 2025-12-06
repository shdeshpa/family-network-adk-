"""Stage 4 Tests: Family Graph with GraphLite."""

import pytest
import tempfile
from pathlib import Path
from datetime import date


class TestPersonStore:
    """Test person attribute storage."""
    
    def test_add_and_get_person(self):
        """Should add and retrieve a person."""
        from src.graph.person_store import PersonStore
        from src.models import Person
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = PersonStore(db_path=f"{tmpdir}/persons.db")
            
            person = Person(
                name="Ramesh Kumar",
                gender="M",
                phone="9876543210",
                location="Hyderabad"
            )
            
            person_id = store.add_person(person)
            assert person_id > 0
            
            retrieved = store.get_person(person_id)
            assert retrieved is not None
            assert retrieved.name == "Ramesh Kumar"
            assert retrieved.phone == "9876543210"
    
    def test_find_by_name(self):
        """Should find persons by partial name match."""
        from src.graph.person_store import PersonStore
        from src.models import Person
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = PersonStore(db_path=f"{tmpdir}/persons.db")
            
            store.add_person(Person(name="Ramesh Kumar"))
            store.add_person(Person(name="Suresh Kumar"))
            store.add_person(Person(name="Priya Sharma"))
            
            results = store.find_by_name("Kumar")
            assert len(results) == 2
    
    def test_update_person(self):
        """Should update person attributes."""
        from src.graph.person_store import PersonStore
        from src.models import Person
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = PersonStore(db_path=f"{tmpdir}/persons.db")
            
            person_id = store.add_person(Person(name="Test User"))
            store.update_person(person_id, phone="1234567890", location="Mumbai")
            
            updated = store.get_person(person_id)
            assert updated.phone == "1234567890"
            assert updated.location == "Mumbai"


class TestFamilyGraph:
    """Test family relationship graph."""
    
    def test_parent_child_relationship(self):
        """Should store and retrieve parent-child relationships."""
        from src.graph.family_graph import FamilyGraph
        
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            
            # Parent ID=1, Child ID=2
            graph.add_parent_child(parent_id=1, child_id=2)
            
            children = graph.get_children(1)
            assert 2 in children
            
            parents = graph.get_parents(2)
            assert 1 in parents
    
    def test_spouse_relationship(self):
        """Should store bidirectional spouse relationship."""
        from src.graph.family_graph import FamilyGraph
        
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            
            graph.add_spouse(1, 2)
            
            assert 2 in graph.get_spouse(1)
            assert 1 in graph.get_spouse(2)
    
    def test_grandchildren(self):
        """Should find grandchildren through traversal."""
        from src.graph.family_graph import FamilyGraph
        
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            
            # Grandparent(1) -> Parent(2) -> Child(3)
            graph.add_parent_child(1, 2)
            graph.add_parent_child(2, 3)
            
            grandchildren = graph.get_grandchildren(1)
            assert 3 in grandchildren
    
    def test_family_tree_structure(self):
        """Should return complete family tree."""
        from src.graph.family_graph import FamilyGraph
        
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            
            # Build small family: Parent1(1) + Parent2(2) -> Child(3)
            graph.add_spouse(1, 2)
            graph.add_parent_child(1, 3)
            graph.add_parent_child(2, 3)
            
            tree = graph.get_family_tree(3)
            
            assert 1 in tree["parents"]
            assert 2 in tree["parents"]
            assert tree["person_id"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])