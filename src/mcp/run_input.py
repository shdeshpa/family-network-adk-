"""Run the Input MCP server."""

from src.mcp.input_server import run_server

if __name__ == "__main__":
    print("=" * 80)
    print("FAMILY NETWORK - INPUT MCP SERVER")
    print("=" * 80)
    print("\nStarting server on http://0.0.0.0:8003")
    print("\nAvailable tools:")
    print("  - process_text_input: Process text to create/edit family members")
    print("  - process_audio_input: Process audio to create/edit family members")
    print("  - get_input_help: Get usage examples and guidelines")
    print("\nPress Ctrl+C to stop")
    print("=" * 80)
    print()

    run_server(host="0.0.0.0", port=8003)
