"""Stage 8 Tests: Centrality & Analytics."""

import pytest
import tempfile


class TestFamilyAnalytics:
    """Test family network analytics."""
    
    def test_analytics_import(self):
        """Analytics should be importable."""
        from src.graph.analytics import FamilyAnalytics
        assert FamilyAnalytics is not None
    
    def test_degree_centrality(self):
        """Should calculate degree centrality correctly."""
        from src.graph.analytics import FamilyAnalytics
        from src.graph.family_graph import FamilyGraph
        from src.graph.person_store import PersonStore
        
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            store = PersonStore(db_path=f"{tmpdir}/persons.db")
            analytics = FamilyAnalytics(family_graph=graph, person_store=store)
            
            # Create family: Parent(1) + Parent(2) -> Children(3, 4)
            graph.add_spouse(1, 2)
            graph.add_parent_child(1, 3)
            graph.add_parent_child(1, 4)
            graph.add_parent_child(2, 3)
            graph.add_parent_child(2, 4)
            graph.add_sibling(3, 4)
            
            # Parent 1 has: spouse(2), children(3,4) = 3 connections
            centrality = analytics.degree_centrality(1)
            assert centrality == 3
            
            # Child 3 has: parents(1,2), sibling(4) = 3 connections
            centrality = analytics.degree_centrality(3)
            assert centrality == 3
    
    def test_find_most_connected(self):
        """Should find most connected members."""
        from src.graph.analytics import FamilyAnalytics
        from src.graph.family_graph import FamilyGraph
        from src.graph.person_store import PersonStore
        from src.models import Person
        
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            store = PersonStore(db_path=f"{tmpdir}/persons.db")
            
            # Add persons
            id1 = store.add_person(Person(name="Parent1"))
            id2 = store.add_person(Person(name="Parent2"))
            id3 = store.add_person(Person(name="Child1"))
            id4 = store.add_person(Person(name="Child2"))
            id5 = store.add_person(Person(name="Child3"))
            
            # Parent1 has most connections
            graph.add_spouse(id1, id2)
            graph.add_parent_child(id1, id3)
            graph.add_parent_child(id1, id4)
            graph.add_parent_child(id1, id5)
            
            analytics = FamilyAnalytics(family_graph=graph, person_store=store)
            most_connected = analytics.find_most_connected([id1, id2, id3, id4, id5], top_n=2)
            
            assert len(most_connected) == 2
            assert most_connected[0]["person_id"] == id1
            assert most_connected[0]["degree_centrality"] == 4  # spouse + 3 children
    
    def test_generation_depth(self):
        """Should calculate generation depth."""
        from src.graph.analytics import FamilyAnalytics
        from src.graph.family_graph import FamilyGraph
        
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            analytics = FamilyAnalytics(family_graph=graph)
            
            # 3 generations: Grandparent(1) -> Parent(2) -> Child(3)
            graph.add_parent_child(1, 2)
            graph.add_parent_child(2, 3)
            
            depth = analytics.get_generation_depth(2)
            
            assert depth["generations_above"] == 1
            assert depth["generations_below"] == 1
    
    def test_family_statistics(self):
        """Should return family statistics."""
        from src.graph.analytics import FamilyAnalytics
        from src.graph.family_graph import FamilyGraph
        from src.graph.person_store import PersonStore
        from src.models import Person
        
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            store = PersonStore(db_path=f"{tmpdir}/persons.db")
            
            id1 = store.add_person(Person(name="Person1"))
            id2 = store.add_person(Person(name="Person2"))
            id3 = store.add_person(Person(name="Person3"))
            
            graph.add_spouse(id1, id2)
            graph.add_parent_child(id1, id3)
            graph.add_parent_child(id2, id3)
            
            analytics = FamilyAnalytics(family_graph=graph, person_store=store)
            stats = analytics.family_statistics([id1, id2, id3])
            
            assert stats["total_members"] == 3
            assert stats["total_connections"] >= 2
            print(f"\nFamily stats: {stats}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])