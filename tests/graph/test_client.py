"""Test GraphLite client."""

import pytest


class TestGraphLiteClient:
    """Tests for GraphLite client."""
    
    def test_query_persons(self, client):
        """Test querying persons."""
        result = client.query("MATCH (p:Person) RETURN p.name")
        assert result.success
        assert isinstance(result.rows, list)
    
    def test_execute_insert(self, client):
        """Test insert execution."""
        result = client.execute("INSERT (:Person {name: 'TestClient', gender: 'M'})")
        assert result.success


class TestOutputParser:
    """Tests for output parser."""
    
    def test_parse_table(self):
        """Test table parsing."""
        from src.graph.graphlite.parser import OutputParser
        
        output = """
┌────────┬────────┐
│ p.name ┆ p.gender │
╞════════╪══════════╡
│ Ramesh ┆ M        │
└────────┴──────────┘
"""
        result = OutputParser.parse_table(output)
        assert result.success
        assert 'p.name' in result.columns
        assert len(result.rows) == 1
        assert result.rows[0]['p.name'] == 'Ramesh'
