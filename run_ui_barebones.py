"""Absolute bare minimum to test if NiceGUI itself works."""

import subprocess

# Kill any process on port 8080
subprocess.run("lsof -ti:8080 | xargs kill -9 2>/dev/null || true", shell=True)

from nicegui import ui

ui.label("🏠 Test - If you see this, NiceGUI works").classes("text-2xl font-bold")
ui.label("The issue is with project imports, not NiceGUI itself").classes("text-gray-600 mt-4")

if __name__ == "__main__":
    print("Starting bare bones UI...")
    ui.run(title="Test", port=8080, reload=False)
