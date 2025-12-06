"""Test family graph operations."""

import pytest


class TestPersonOperations:
    """Tests for person operations."""
    
    def test_get_all_persons(self, graph):
        """Test getting all persons."""
        persons = graph.get_all_persons()
        assert isinstance(persons, list)
    
    def test_get_person_by_name(self, graph):
        """Test getting person by name."""
        person = graph.get_person("Ramesh")
        if person:
            assert person.name == "Ramesh"


class TestFamilyQueries:
    """Tests for family queries."""
    
    def test_get_family_tree(self, graph):
        """Test family tree query."""
        tree = graph.get_family_tree("Ramesh")
        assert "person" in tree
        assert "spouse" in tree
        assert "children" in tree
        assert "parents" in tree
    
    def test_get_spouse(self, graph):
        """Test spouse query."""
        spouses = graph.get_spouse("Ramesh")
        assert isinstance(spouses, list)


class TestRelationships:
    """Tests for relationship operations."""
    
    def test_get_all_relationships(self, graph):
        """Test getting all relationships."""
        rels = graph.get_all_relationships()
        assert isinstance(rels, list)
