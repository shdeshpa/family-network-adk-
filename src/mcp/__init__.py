"""MCP servers for Family Network."""

from src.mcp.transcription_server import mcp as transcription_mcp
from src.mcp.family_server import mcp as family_mcp

__all__ = ["transcription_mcp", "family_mcp"]