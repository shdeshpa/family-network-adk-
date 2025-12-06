"""Run CRM-only UI - Most stable version."""

import subprocess
import sys

# Kill any process on port 8080
subprocess.run("lsof -ti:8080 | xargs kill -9 2>/dev/null || true", shell=True)

# Set path and run
sys.path.insert(0, ".")

from nicegui import ui
from src.ui.crm_editor_v2 import CRMEditorV2

# Build UI
ui.label("🏠 Family Network - CRM Viewer").classes("text-3xl font-bold mb-6")

crm_editor = CRMEditorV2()
crm_editor.render()

if __name__ == "__main__":
    ui.run(title="Family Network CRM", port=8080, reload=False)
