"""Entry point for running transcription MCP server."""

import argparse
from src.mcp.transcription_server import run_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcription MCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on")
    args = parser.parse_args()
    
    print(f"Starting Transcription MCP Server on http://{args.host}:{args.port}")
    run_server(host=args.host, port=args.port)