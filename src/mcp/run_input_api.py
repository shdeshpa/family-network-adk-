"""Run the Input HTTP API server."""

from src.mcp.input_api_server import run_server

if __name__ == "__main__":
    print("=" * 80)
    print("FAMILY NETWORK - INPUT HTTP API SERVER")
    print("=" * 80)
    print("\nStarting server on http://0.0.0.0:8003")
    print("\nAvailable endpoints:")
    print("  - POST /tools/process_text_input: Process text to create/edit family members")
    print("  - POST /tools/process_audio_input: Process audio to create/edit family members")
    print("  - POST /tools/fuzzy_match_person: Find person with fuzzy name matching (NEW)")
    print("  - POST /tools/resolve_pronoun: Resolve pronouns (he/she) to person IDs (NEW)")
    print("  - POST /tools/get_input_help: Get usage examples and guidelines")
    print("  - GET /health: Health check")
    print("\nPress Ctrl+C to stop")
    print("=" * 80)
    print()

    run_server(host="0.0.0.0", port=8003)
