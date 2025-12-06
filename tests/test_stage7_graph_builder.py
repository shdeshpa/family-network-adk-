"""Stage 7 Tests: Graph Builder Agent."""

import pytest
import tempfile


class TestGraphBuilderAgent:
    """Test graph builder agent."""
    
    def test_agent_import(self):
        """Agent should be importable."""
        from src.agents.graph_builder import GraphBuilderAgent
        assert GraphBuilderAgent is not None
    
    def test_build_from_extraction(self):
        """Should build graph from extraction data."""
        from src.agents.graph_builder import GraphBuilderAgent
        from src.graph.person_store import PersonStore
        from src.graph.family_graph import FamilyGraph
        from src.graph.crm_store import CRMStore
        
        with tempfile.TemporaryDirectory() as tmpdir:
            person_store = PersonStore(db_path=f"{tmpdir}/persons.db")
            family_graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            crm_store = CRMStore(db_path=f"{tmpdir}/crm.db")
            
            agent = GraphBuilderAgent(
                person_store=person_store,
                family_graph=family_graph,
                crm_store=crm_store
            )
            
            # Simulated extraction result
            extraction = {
                "success": True,
                "persons": [
                    {"name": "Ramesh Kumar", "gender": "M", "location": "Hyderabad", "phone": "9876543210"},
                    {"name": "Priya Kumar", "gender": "F", "location": "Hyderabad"},
                    {"name": "Arjun Kumar", "gender": "M", "location": "Bangalore"},
                    {"name": "Kavya Kumar", "gender": "F", "location": "Chennai"}
                ],
                "relationships": [
                    {"type": "spouse", "person1": "Ramesh Kumar", "person2": "Priya Kumar"},
                    {"type": "parent_child", "parent": "Ramesh Kumar", "child": "Arjun Kumar"},
                    {"type": "parent_child", "parent": "Ramesh Kumar", "child": "Kavya Kumar"},
                    {"type": "parent_child", "parent": "Priya Kumar", "child": "Arjun Kumar"},
                    {"type": "parent_child", "parent": "Priya Kumar", "child": "Kavya Kumar"},
                    {"type": "sibling", "person1": "Arjun Kumar", "person2": "Kavya Kumar"}
                ]
            }
            
            result = agent.build_from_extraction(extraction)
            
            print(f"\nBuild result: {result}")
            
            assert result["success"] == True
            assert result["persons_created"] == 4
            assert result["relationships_created"] == 6
            
            # Verify graph structure
            ramesh_id = agent.get_person_id("ramesh kumar")
            arjun_id = agent.get_person_id("arjun kumar")
            
            children = family_graph.get_children(ramesh_id)
            assert arjun_id in children
    
    def test_duplicate_person_handling(self):
        """Should handle duplicate persons correctly."""
        from src.agents.graph_builder import GraphBuilderAgent
        from src.graph.person_store import PersonStore
        from src.graph.family_graph import FamilyGraph
        from src.graph.crm_store import CRMStore
        
        with tempfile.TemporaryDirectory() as tmpdir:
            person_store = PersonStore(db_path=f"{tmpdir}/persons.db")
            family_graph = FamilyGraph(db_path=f"{tmpdir}/family.db")
            crm_store = CRMStore(db_path=f"{tmpdir}/crm.db")
            
            agent = GraphBuilderAgent(
                person_store=person_store,
                family_graph=family_graph,
                crm_store=crm_store
            )
            
            # First extraction
            extraction1 = {
                "success": True,
                "persons": [{"name": "Ramesh Kumar", "location": "Hyderabad"}],
                "relationships": []
            }
            result1 = agent.build_from_extraction(extraction1)
            
            # Second extraction with same person
            agent2 = GraphBuilderAgent(
                person_store=person_store,
                family_graph=family_graph,
                crm_store=crm_store
            )
            extraction2 = {
                "success": True,
                "persons": [{"name": "Ramesh Kumar", "location": "Hyderabad"}],
                "relationships": []
            }
            result2 = agent2.build_from_extraction(extraction2)
            
            # Should recognize as existing
            assert result2["persons"][0]["existing"] == True
            
            # Should have only 1 person in store
            all_persons = person_store.get_all()
            ramesh_count = sum(1 for p in all_persons if "Ramesh" in p.name)
            assert ramesh_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])