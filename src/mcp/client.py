"""MCP Client - calls FastMCP servers via subprocess."""

import json
from typing import Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Client to call FastMCP server tools."""
    
    def __init__(self, server_script: str):
        self.server_script = server_script
        self.session = None
        self._context = None
    
    async def connect(self):
        """Connect to MCP server."""
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", self.server_script]
        )
        
        self._context = stdio_client(server_params)
        self.stdio, self.write = await self._context.__aenter__()
        self.session = ClientSession(self.stdio, self.write)
        await self.session.__aenter__()
        await self.session.initialize()
        return self
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        result = await self.session.call_tool(tool_name, arguments)
        
        if result.content:
            for content in result.content:
                if hasattr(content, 'text'):
                    try:
                        return json.loads(content.text)
                    except:
                        return content.text
        return None
    
    async def list_tools(self) -> list:
        """List available tools."""
        result = await self.session.list_tools()
        return [t.name for t in result.tools]
    
    async def close(self):
        """Close connection."""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self._context:
            await self._context.__aexit__(None, None, None)


async def call_nlp_tool(tool_name: str, args: dict) -> dict:
    """Call NLP server tool."""
    client = MCPClient("src/mcp/servers/nlp_server.py")
    try:
        await client.connect()
        return await client.call_tool(tool_name, args)
    finally:
        await client.close()


async def call_graph_tool(tool_name: str, args: dict) -> dict:
    """Call Graph server tool."""
    client = MCPClient("src/mcp/servers/graph_server.py")
    try:
        await client.connect()
        return await client.call_tool(tool_name, args)
    finally:
        await client.close()


async def call_crm_tool(tool_name: str, args: dict) -> dict:
    """Call CRM server tool."""
    client = MCPClient("src/mcp/servers/crm_server.py")
    try:
        await client.connect()
        return await client.call_tool(tool_name, args)
    finally:
        await client.close()


async def call_input_tool(tool_name: str, args: dict) -> dict:
    """Call Input server tool."""
    client = MCPClient("src/mcp/input_server.py")
    try:
        await client.connect()
        return await client.call_tool(tool_name, args)
    finally:
        await client.close()
