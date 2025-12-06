"""Family tree visualization component for NiceGUI."""

from typing import Optional, Callable

from nicegui import ui

from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.analytics import FamilyAnalytics


class FamilyTreeView:
    """Interactive family tree visualization."""
    
    def __init__(
        self,
        person_store: Optional[PersonStore] = None,
        family_graph: Optional[FamilyGraph] = None,
        on_person_select: Optional[Callable] = None
    ):
        self.person_store = person_store or PersonStore()
        self.family_graph = family_graph or FamilyGraph()
        self.analytics = FamilyAnalytics(self.family_graph, self.person_store)
        self.on_person_select = on_person_select
        self.selected_person_id: Optional[int] = None
    
    def render(self):
        """Render the tree visualization."""
        with ui.card().classes("w-full p-4"):
            ui.label("🌳 Family Tree").classes("text-xl font-bold mb-4")
            
            with ui.row().classes("w-full gap-4"):
                with ui.card().classes("flex-1 p-4"):
                    self._render_tree_diagram()
                
                with ui.card().classes("w-80 p-4"):
                    self._render_person_details()
    
    def _render_tree_diagram(self):
        """Render the Mermaid tree diagram."""
        with ui.row().classes("justify-between items-center mb-2"):
            ui.label("Family Structure").classes("font-bold")
            ui.button("🔄 Refresh", on_click=self._refresh_tree).classes("text-sm")
        
        mermaid_code = self._generate_mermaid()
        
        if mermaid_code:
            ui.mermaid(mermaid_code).classes("w-full")
        else:
            ui.label("No family data yet. Add persons to see the tree.").classes("text-gray-500")
    
    def _generate_mermaid(self) -> str:
        """Generate Mermaid diagram code from family graph."""
        persons = self.person_store.get_all()
        if not persons:
            return ""
        
        lines = ["graph TD"]
        added_edges = set()
        
        for person in persons:
            node_id = f"P{person.id}"
            label = person.name.replace(" ", "_")
            lines.append(f"    {node_id}[{label}]")
            
            # Parent → Child (parent at top, child below)
            children = self.family_graph.get_children(person.id)
            for child_id in children:
                edge_key = (person.id, child_id, "parent")
                if edge_key not in added_edges:
                    lines.append(f"    P{person.id} --> P{child_id}")
                    added_edges.add(edge_key)
            
            # Spouse (dotted line, horizontal)
            spouses = self.family_graph.get_spouse(person.id)
            for spouse_id in spouses:
                edge_key = tuple(sorted([person.id, spouse_id])) + ("spouse",)
                if edge_key not in added_edges:
                    lines.append(f"    P{person.id} -.- P{spouse_id}")
                    added_edges.add(edge_key)
            
            # Siblings (dotted, different style)
            siblings = self.family_graph.get_siblings(person.id)
            for sib_id in siblings:
                edge_key = tuple(sorted([person.id, sib_id])) + ("sibling",)
                if edge_key not in added_edges:
                    lines.append(f"    P{person.id} -.-> P{sib_id}")
                    added_edges.add(edge_key)
        
        return "\n".join(lines)
    
    def _render_person_details(self):
        """Render selected person details panel."""
        ui.label("Person Details").classes("font-bold mb-2")
        
        self.details_container = ui.column().classes("w-full")
        
        with self.details_container:
            ui.label("Select a person below").classes("text-gray-500")
        
        persons = self.person_store.get_all()
        if persons:
            options = {p.id: p.name for p in persons}
            ui.select(
                options=options,
                label="Select Person",
                on_change=lambda e: self._show_person_details(e.value)
            ).classes("w-full mt-4")
            
            ui.separator().classes("my-4")
            
            # Delete button
            ui.label("Actions").classes("font-bold")
            with ui.row().classes("gap-2 mt-2"):
                ui.button("🗑️ Delete Selected", on_click=self._delete_selected).classes("bg-red-400 text-sm")
                ui.button("🔗 Edit Relationships", on_click=self._edit_relationships).classes("bg-blue-400 text-sm")
    
    def _show_person_details(self, person_id: int):
        """Show details for selected person."""
        if not person_id:
            return
        
        self.selected_person_id = person_id
        person = self.person_store.get_person(person_id)
        
        if not person:
            return
        
        self.details_container.clear()
        
        with self.details_container:
            ui.label(f"📌 {person.name}").classes("text-lg font-bold")
            
            if person.gender:
                ui.label(f"Gender: {'Male' if person.gender == 'M' else 'Female' if person.gender == 'F' else person.gender}")
            if person.age:
                ui.label(f"Age: {person.age}")
            if person.location:
                ui.label(f"📍 {person.location}")
            if person.phone:
                ui.label(f"📞 {person.phone}")
            if person.email:
                ui.label(f"✉️ {person.email}")
            
            ui.separator().classes("my-2")
            
            tree = self.family_graph.get_family_tree(person_id)
            
            if tree["parents"]:
                parent_names = self._get_names(tree["parents"])
                ui.label(f"👆 Parents: {', '.join(parent_names)}")
            
            if tree["spouse"]:
                spouse_names = self._get_names(tree["spouse"])
                ui.label(f"💑 Spouse: {', '.join(spouse_names)}")
            
            if tree["siblings"]:
                sibling_names = self._get_names(tree["siblings"])
                ui.label(f"👫 Siblings: {', '.join(sibling_names)}")
            
            if tree["children"]:
                children_names = self._get_names(tree["children"])
                ui.label(f"👶 Children: {', '.join(children_names)}")
            
            ui.separator().classes("my-2")
            centrality = self.analytics.degree_centrality(person_id)
            ui.label(f"Connections: {centrality}").classes("text-sm text-gray-600")
    
    def _get_names(self, person_ids: list[int]) -> list[str]:
        """Get names for a list of person IDs."""
        names = []
        for pid in person_ids:
            person = self.person_store.get_person(pid)
            names.append(person.name if person else f"ID:{pid}")
        return names
    
    async def _refresh_tree(self):
        """Refresh the tree view."""
        ui.notify("Refreshing...")
        ui.navigate.reload()
    
    async def _delete_selected(self):
        """Delete selected person."""
        if not self.selected_person_id:
            ui.notify("Select a person first", type="warning")
            return
        
        person = self.person_store.get_person(self.selected_person_id)
        name = person.name if person else "Unknown"
        
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete {name}?").classes("text-lg font-bold")
            ui.label("This will remove the person and all their relationships.")
            
            with ui.row().classes("gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Delete", on_click=lambda: self._confirm_delete(dialog)).classes("bg-red-500")
        
        dialog.open()
    
    async def _confirm_delete(self, dialog):
        """Confirm and execute deletion."""
        # Note: GraphLite doesn't have easy delete, so we'd need to implement this
        # For now, show a message
        dialog.close()
        ui.notify("Delete feature coming soon. Clear database to reset.", type="info")
    
    async def _edit_relationships(self):
        """Open relationship editor dialog."""
        if not self.selected_person_id:
            ui.notify("Select a person first", type="warning")
            return
        
        person = self.person_store.get_person(self.selected_person_id)
        persons = self.person_store.get_all()
        options = {p.id: p.name for p in persons if p.id != self.selected_person_id}
        
        with ui.dialog() as dialog, ui.card().classes("w-96"):
            ui.label(f"Add Relationship for {person.name}").classes("text-lg font-bold mb-4")
            
            other_person = ui.select(options=options, label="Other Person").classes("w-full")
            rel_type = ui.select(
                options={
                    "spouse": "Spouse",
                    "parent_child": f"{person.name} is PARENT of...",
                    "child_parent": f"{person.name} is CHILD of..."
                },
                label="Relationship"
            ).classes("w-full")
            
            async def add_rel():
                if not other_person.value or not rel_type.value:
                    ui.notify("Select both fields", type="warning")
                    return
                
                from src.agents.adk.tools import add_relationship
                
                if rel_type.value == "spouse":
                    result = add_relationship(person.name, options[other_person.value], "spouse")
                elif rel_type.value == "parent_child":
                    result = add_relationship(person.name, options[other_person.value], "parent_child")
                elif rel_type.value == "child_parent":
                    result = add_relationship(options[other_person.value], person.name, "parent_child")
                
                if result.get("success"):
                    ui.notify("Relationship added!")
                    dialog.close()
                    ui.navigate.reload()
                else:
                    ui.notify(f"Error: {result.get('error')}", type="negative")
            
            with ui.row().classes("gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Add", on_click=add_rel).classes("bg-green-500")
        
        dialog.open()