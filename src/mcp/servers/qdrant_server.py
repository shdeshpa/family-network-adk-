"""QDRANT MCP server stub using FastMCP."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("qdrant-server")


@mcp.tool()
def embed_person(name: str, description: str) -> dict:
    """Embed person description in QDRANT (stub)."""
    return {"success": True, "action": "embedded", "name": name, "stub": True}


@mcp.tool()
def semantic_search(query: str, limit: int = 5) -> dict:
    """Search for persons by semantic similarity (stub)."""
    return {"success": True, "query": query, "results": [], "stub": True}


if __name__ == "__main__":
    mcp.run()
