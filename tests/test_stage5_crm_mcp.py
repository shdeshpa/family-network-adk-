"""Stage 5 Tests: CRM and Family MCP Server."""

import pytest
import tempfile


class TestCRMStore:
    """Test CRM database operations."""
    
    def test_add_contact(self):
        """Should add contact info."""
        from src.graph.crm_store import CRMStore
        
        with tempfile.TemporaryDirectory() as tmpdir:
            crm = CRMStore(db_path=f"{tmpdir}/crm.db")
            contact_id = crm.add_contact(1, phone="9876543210", email="test@example.com")
            assert contact_id > 0
    
    def test_get_contact(self):
        """Should retrieve contact info."""
        from src.graph.crm_store import CRMStore
        
        with tempfile.TemporaryDirectory() as tmpdir:
            crm = CRMStore(db_path=f"{tmpdir}/crm.db")
            crm.add_contact(1, phone="9876543210")
            
            contact = crm.get_contact(1)
            assert contact is not None
            assert contact["phone"] == "9876543210"
    
    def test_add_interest(self):
        """Should add and find by interest."""
        from src.graph.crm_store import CRMStore
        
        with tempfile.TemporaryDirectory() as tmpdir:
            crm = CRMStore(db_path=f"{tmpdir}/crm.db")
            crm.add_interest(1, "yoga")
            crm.add_interest(2, "yoga")
            crm.add_interest(1, "music")
            
            yoga_lovers = crm.find_by_interest("yoga")
            assert 1 in yoga_lovers
            assert 2 in yoga_lovers
    
    def test_log_interaction(self):
        """Should log and retrieve interactions."""
        from src.graph.crm_store import CRMStore
        
        with tempfile.TemporaryDirectory() as tmpdir:
            crm = CRMStore(db_path=f"{tmpdir}/crm.db")
            crm.add_interaction(1, "phone_call", "Discussed family event")
            crm.add_interaction(1, "email", "Sent invitation")
            
            interactions = crm.get_interactions(1)
            assert len(interactions) == 2


class TestFamilyMCPServer:
    """Test Family MCP server."""
    
    def test_mcp_import(self):
        """MCP server should be importable."""
        from src.mcp.family_server import mcp
        assert mcp.name == "family-network-server"
    
    def test_mcp_has_tools(self):
        """MCP should have tool manager."""
        from src.mcp.family_server import mcp
        assert mcp._tool_manager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])