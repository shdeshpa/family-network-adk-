"""Person editor component for NiceGUI."""

from typing import Optional, Callable

from nicegui import ui

from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.models import Person


class PersonEditor:
    """Edit person details and relationships."""
    
    def __init__(
        self,
        person_store: Optional[PersonStore] = None,
        family_graph: Optional[FamilyGraph] = None,
        on_save: Optional[Callable] = None
    ):
        self.person_store = person_store or PersonStore()
        self.family_graph = family_graph or FamilyGraph()
        self.on_save = on_save
    
    def render_add_person_form(self):
        """Render form to add new person."""
        with ui.card().classes("w-96 p-4"):
            ui.label("➕ Add New Person").classes("text-lg font-bold mb-4")
            
            name_input = ui.input("Name *").classes("w-full")
            gender_select = ui.select(
                options={"M": "Male", "F": "Female", "O": "Other"},
                label="Gender"
            ).classes("w-full")
            phone_input = ui.input("Phone").classes("w-full")
            email_input = ui.input("Email").classes("w-full")
            location_input = ui.input("Location").classes("w-full")
            
            async def save_person():
                if not name_input.value:
                    ui.notify("Name is required", type="warning")
                    return
                
                person = Person(
                    name=name_input.value,
                    gender=gender_select.value,
                    phone=phone_input.value or None,
                    email=email_input.value or None,
                    location=location_input.value or None
                )
                
                person_id = self.person_store.add_person(person)
                ui.notify(f"Added {person.name} (ID: {person_id})", type="positive")
                
                # Clear form
                name_input.value = ""
                gender_select.value = None
                phone_input.value = ""
                email_input.value = ""
                location_input.value = ""
                
                if self.on_save:
                    await self.on_save(person_id)
            
            ui.button("💾 Save Person", on_click=save_person).classes("mt-4 bg-green-500")
    
    def render_add_relationship_form(self):
        """Render form to add relationships."""
        with ui.card().classes("w-96 p-4"):
            ui.label("🔗 Add Relationship").classes("text-lg font-bold mb-4")
            
            persons = self.person_store.get_all()
            options = {p.id: p.name for p in persons}
            
            if len(options) < 2:
                ui.label("Add at least 2 persons first").classes("text-gray-500")
                return
            
            person1_select = ui.select(
                options=options,
                label="Person 1"
            ).classes("w-full")
            
            rel_type_select = ui.select(
                options={
                    "parent_child": "Parent → Child",
                    "spouse": "Spouse ↔ Spouse",
                    "sibling": "Sibling ↔ Sibling"
                },
                label="Relationship Type"
            ).classes("w-full")
            
            person2_select = ui.select(
                options=options,
                label="Person 2"
            ).classes("w-full")
            
            async def save_relationship():
                if not all([person1_select.value, rel_type_select.value, person2_select.value]):
                    ui.notify("All fields required", type="warning")
                    return
                
                if person1_select.value == person2_select.value:
                    ui.notify("Select different persons", type="warning")
                    return
                
                p1, p2 = person1_select.value, person2_select.value
                rel = rel_type_select.value
                
                if rel == "parent_child":
                    self.family_graph.add_parent_child(p1, p2)
                elif rel == "spouse":
                    self.family_graph.add_spouse(p1, p2)
                elif rel == "sibling":
                    self.family_graph.add_sibling(p1, p2)
                
                ui.notify(f"Relationship added!", type="positive")
                
                if self.on_save:
                    await self.on_save(None)
            
            ui.button("🔗 Add Relationship", on_click=save_relationship).classes("mt-4 bg-blue-500")