"""Test NiceGUI with all background features disabled."""

import subprocess
import os

# Kill any process on port 8080
subprocess.run("lsof -ti:8080 | xargs kill -9 2>/dev/null || true", shell=True)

# Disable multiprocessing for NiceGUI
os.environ['NICEGUI_STORAGE_PATH'] = '/tmp/nicegui'

from nicegui import ui

ui.label("🏠 Test - No Reload/Background Processes").classes("text-2xl font-bold")
ui.label("Testing if disabling reload helps...").classes("text-gray-600 mt-4")

if __name__ == "__main__":
    print("Starting UI with reload disabled...")
    # Disable reload, show=False to prevent auto-opening browser
    ui.run(
        title="Test",
        port=8080,
        reload=False,
        show=False,
        storage_secret=None  # Disable storage
    )
