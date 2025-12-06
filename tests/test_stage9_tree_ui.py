"""Stage 9 Tests: Tree Visualization UI."""

import pytest


class TestTreeVisualization:
    """Test tree visualization components."""
    
    def test_tree_view_import(self):
        """TreeView should be importable."""
        from src.ui.tree_view import FamilyTreeView
        assert FamilyTreeView is not None
    
    def test_person_editor_import(self):
        """PersonEditor should be importable."""
        from src.ui.person_editor import PersonEditor
        assert PersonEditor is not None
    
    def test_mermaid_generation(self):
        """Should generate Mermaid diagram code."""
        import tempfile
        from src.ui.tree_view import FamilyTreeView
        from src.graph.person_store import PersonStore
        from src.graph.family_graph import FamilyGraph
        from src.models import Person
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = PersonStore(db_path=f"{tmpdir}/persons.db")
            graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            
            # Add test data
            id1 = store.add_person(Person(name="Parent One"))
            id2 = store.add_person(Person(name="Child One"))
            graph.add_parent_child(id1, id2)
            
            tree_view = FamilyTreeView(person_store=store, family_graph=graph)
            mermaid = tree_view._generate_mermaid()
            
            assert "graph TD" in mermaid
            assert "Parent_One" in mermaid
            assert "Child_One" in mermaid
            assert "-->" in mermaid  # Parent-child arrow
            
            print(f"\nGenerated Mermaid:\n{mermaid}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])