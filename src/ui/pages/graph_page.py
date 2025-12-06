"""Graph Data Page - View all persons and relationships."""

from nicegui import ui
from src.graph import FamilyGraph


class GraphPage:
    """Graph data viewer with refresh capability."""
    
    def __init__(self):
        self.graph = FamilyGraph()
    
    def build(self):
        """Build the graph page UI."""
        with ui.row().classes("w-full justify-between items-center mb-4"):
            ui.label("Graph Data").classes("text-2xl font-bold")
            ui.button("Refresh", on_click=self.refresh_data, icon="refresh").props("flat")
        
        self.persons_container = ui.column().classes("w-full")
        self.rels_container = ui.column().classes("w-full")
        
        self.load_data()
    
    def load_data(self):
        """Load and display data."""
        # Reload graph to get fresh data
        self.graph = FamilyGraph()
        
        # Persons
        self.persons_container.clear()
        with self.persons_container:
            with ui.card().classes("w-full mb-4"):
                persons = self.graph.get_all_persons()
                ui.label(f"All Persons ({len(persons)})").classes("font-semibold mb-2")
                
                if persons:
                    columns = [
                        {"name": "name", "label": "Name", "field": "name", "sortable": True},
                        {"name": "gender", "label": "Gender", "field": "gender"},
                        {"name": "family", "label": "Family Name", "field": "family"},
                        {"name": "location", "label": "Location", "field": "location"},
                    ]
                    rows = [
                        {
                            "name": p.name,
                            "gender": p.gender or "-",
                            "family": p.family_name or "-",
                            "location": p.location or "-",
                        }
                        for p in persons
                    ]
                    ui.table(columns=columns, rows=rows).classes("w-full")
                else:
                    ui.label("No persons in graph").classes("text-gray-500")
        
        # Relationships
        self.rels_container.clear()
        with self.rels_container:
            with ui.card().classes("w-full"):
                rels = self.graph.get_all_relationships()
                ui.label(f"All Relationships ({len(rels)})").classes("font-semibold mb-2")
                
                if rels:
                    columns = [
                        {"name": "from", "label": "From", "field": "from", "sortable": True},
                        {"name": "type", "label": "Relationship", "field": "type"},
                        {"name": "to", "label": "To", "field": "to"},
                    ]
                    rows = [
                        {
                            "from": r["from"],
                            "type": r["specific"] or r["type"],
                            "to": r["to"]
                        }
                        for r in rels
                    ]
                    ui.table(columns=columns, rows=rows).classes("w-full")
                else:
                    ui.label("No relationships in graph").classes("text-gray-500")
    
    def refresh_data(self):
        """Refresh data from graph."""
        self.load_data()
        ui.notify("Data refreshed", type="positive")


def create_graph_page():
    """Create graph page instance."""
    page = GraphPage()
    page.build()
    return page
