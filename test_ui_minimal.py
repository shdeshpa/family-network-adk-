"""Minimal main UI test to identify crash cause."""

from nicegui import ui
from src.ui.crm_editor_v2 import CRMEditorV2

ui.label("🏠 Testing CRM V2 Only").classes("text-2xl font-bold mb-4")

try:
    crm_editor = CRMEditorV2()
    crm_editor.render()
    ui.label("✅ CRM V2 loaded successfully!").classes("text-green-600 mt-4")
except Exception as e:
    ui.label(f"❌ CRM V2 failed: {str(e)}").classes("text-red-600 mt-4")

ui.run(title="Minimal Test", port=8080, reload=False)
