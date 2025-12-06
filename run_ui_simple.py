"""Run simplified Family Network UI - CRM and Tree only."""

import subprocess
import sys

# Kill any process on port 8080
subprocess.run("lsof -ti:8080 | xargs kill -9 2>/dev/null || true", shell=True)

# Set path and run
sys.path.insert(0, ".")

from nicegui import ui
from src.ui.crm_editor_v2 import CRMEditorV2
from src.ui.cytoscape_tree import CytoscapeTree
from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.enhanced_crm import EnhancedCRM

# Initialize stores
person_store = PersonStore()
family_graph = FamilyGraph()
enhanced_crm = EnhancedCRM()

# Build UI
ui.label("🏠 Family Network System").classes("text-3xl font-bold mb-6")

with ui.tabs().classes("w-full") as tabs:
    tree_tab = ui.tab("🌳 Family Tree")
    crm_tab = ui.tab("📇 CRM")

with ui.tab_panels(tabs, value=crm_tab).classes("w-full"):
    with ui.tab_panel(tree_tab):
        ui.label("🌳 Family Tree").classes("text-xl font-bold mb-4")

        def refresh_tree():
            tree_container.clear()
            with tree_container:
                try:
                    tree = CytoscapeTree(
                        person_store=person_store,
                        family_graph=family_graph,
                        enhanced_crm=enhanced_crm
                    )
                    tree.render()
                    ui.notify("Tree refreshed", type="info")
                except Exception as e:
                    ui.label(f"Error: {str(e)}").classes("text-red-500")

        ui.button("🔄 Refresh Tree", on_click=refresh_tree).classes("bg-blue-500 mb-4")
        tree_container = ui.column().classes("w-full")
        refresh_tree()

    with ui.tab_panel(crm_tab):
        crm_editor = CRMEditorV2()
        crm_editor.render()

if __name__ == "__main__":
    ui.run(title="Family Network", port=8080, reload=False)
