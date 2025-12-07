"""Interactive family tree using Cytoscape.js with CRM V2 data."""

from nicegui import ui
from typing import Optional
import json

from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.family_registry import FamilyRegistry


class CytoscapeTree:
    """Interactive family tree with Cytoscape.js using CRM V2 data."""

    def __init__(
        self,
        crm_store: CRMStoreV2 = None,
        family_registry: FamilyRegistry = None,
        person_store: PersonStore = None,
        family_graph: FamilyGraph = None
    ):
        # CRM V2 stores for person data
        self.crm_store = crm_store or CRMStoreV2()
        self.family_registry = family_registry or FamilyRegistry()
        # Legacy stores for relationship graph
        self.person_store = person_store or PersonStore()
        self.family_graph = family_graph or FamilyGraph()
    
    def render(self):
        """Render the tree view using CRM V2 data."""
        # Get persons from CRM V2
        persons = self.crm_store.get_all()

        if not persons:
            ui.label("No family data yet. Add persons using Text Input or Record tabs.").classes("text-gray-500 p-8")
            return

        with ui.row().classes("w-full gap-4"):
            with ui.card().classes("flex-1 p-2"):
                self._render_graph(persons)
            with ui.card().classes("w-72 p-3"):
                self._render_detail_panel(persons)
    
    def _render_graph(self, persons):
        """Render Cytoscape graph."""
        # Toolbar
        with ui.row().classes("gap-1 mb-2"):
            ui.button("Refresh", on_click=lambda: ui.navigate.reload()).props("dense flat size=sm")
            ui.button("Fit", on_click=self._fit_graph).props("dense flat size=sm")
            ui.button("+", on_click=self._zoom_in).props("dense flat size=sm")
            ui.button("-", on_click=self._zoom_out).props("dense flat size=sm")
        
        # Build graph data
        graph_data = self._build_graph_data(persons)
        
        # Container div (no script)
        ui.html('<div id="cy-container" style="width:100%;height:450px;border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;"></div>', sanitize=False)
        
        # Add Cytoscape library
        ui.add_head_html('<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>')
        
        # Add initialization script to body
        init_script = f'''
        <script>
        (function initCy() {{
            if (typeof cytoscape === 'undefined') {{
                setTimeout(initCy, 100);
                return;
            }}
            
            var container = document.getElementById('cy-container');
            if (!container) {{
                setTimeout(initCy, 100);
                return;
            }}
            
            var elements = {graph_data};
            
            window.cy = cytoscape({{
                container: container,
                elements: elements,
                style: [
                    {{
                        selector: 'node',
                        style: {{
                            'background-color': '#818cf8',
                            'label': 'data(label)',
                            'color': '#1f2937',
                            'text-valign': 'bottom',
                            'text-margin-y': 6,
                            'font-size': '10px',
                            'width': 35,
                            'height': 35,
                            'border-width': 2,
                            'border-color': '#6366f1'
                        }}
                    }},
                    {{
                        selector: 'node[gender="M"]',
                        style: {{
                            'background-color': '#60a5fa',
                            'border-color': '#2563eb',
                            'shape': 'round-rectangle'
                        }}
                    }},
                    {{
                        selector: 'node[gender="F"]',
                        style: {{
                            'background-color': '#f472b6',
                            'border-color': '#db2777',
                            'shape': 'ellipse'
                        }}
                    }},
                    {{
                        selector: 'node:selected',
                        style: {{
                            'border-width': 4,
                            'border-color': '#fbbf24'
                        }}
                    }},
                    {{
                        selector: 'edge',
                        style: {{
                            'width': 2,
                            'line-color': '#d1d5db',
                            'target-arrow-color': '#d1d5db',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier'
                        }}
                    }},
                    {{
                        selector: 'edge[type="spouse"]',
                        style: {{
                            'line-style': 'dashed',
                            'line-color': '#f9a8d4',
                            'target-arrow-shape': 'none'
                        }}
                    }},
                    {{
                        selector: 'edge[type="parent_child"]',
                        style: {{
                            'line-color': '#93c5fd',
                            'target-arrow-color': '#93c5fd'
                        }}
                    }},
                    {{
                        selector: 'edge[type="sibling"]',
                        style: {{
                            'line-style': 'dotted',
                            'line-color': '#c4b5fd',
                            'target-arrow-shape': 'none'
                        }}
                    }}
                ],
                layout: {{
                    name: 'breadthfirst',
                    directed: true,
                    padding: 20,
                    spacingFactor: 1.2
                }},
                userZoomingEnabled: true,
                userPanningEnabled: true,
                minZoom: 0.3,
                maxZoom: 3
            }});
            
            setTimeout(function() {{ cy.fit(); }}, 100);
        }})();
        </script>
        '''
        ui.add_body_html(init_script)
    
    def _fit_graph(self):
        ui.run_javascript("if(window.cy)cy.fit()")
    
    def _zoom_in(self):
        ui.run_javascript("if(window.cy)cy.zoom(cy.zoom()*1.3)")
    
    def _zoom_out(self):
        ui.run_javascript("if(window.cy)cy.zoom(cy.zoom()*0.7)")
    
    def _build_graph_data(self, persons) -> str:
        """Build Cytoscape elements from CRM V2 persons."""
        elements = []
        added_edges = set()

        # Build mapping from CRM V2 person ID to legacy PersonStore ID for relationships
        person_id_map = {}  # crm_v2_id -> legacy_person_store_id
        for p in persons:
            if p.is_archived:
                continue
            # Find matching person in legacy PersonStore by name
            legacy_person = self._find_in_person_store(p.full_name)
            if legacy_person:
                person_id_map[p.id] = legacy_person.id

        # Build nodes from CRM V2 persons
        for p in persons:
            if p.is_archived:
                continue

            elements.append({
                "data": {
                    "id": f"p{p.id}",
                    "personId": p.id,
                    "label": p.full_name,
                    "gender": p.gender or ""
                }
            })

            # Get legacy ID for relationship lookups
            legacy_id = person_id_map.get(p.id)
            if not legacy_id:
                continue

            # Add relationship edges using legacy IDs
            try:
                children = self.family_graph.get_children(legacy_id)
                for child_legacy_id in children:
                    # Find CRM V2 person with this legacy ID
                    child_crm_id = self._find_crm_id_by_legacy(child_legacy_id, person_id_map)
                    if child_crm_id:
                        key = (p.id, child_crm_id, "pc")
                        if key not in added_edges:
                            elements.append({
                                "data": {
                                    "id": f"e{p.id}_{child_crm_id}_pc",
                                    "source": f"p{p.id}",
                                    "target": f"p{child_crm_id}",
                                    "type": "parent_child"
                                }
                            })
                            added_edges.add(key)
            except:
                pass

            try:
                spouses = self.family_graph.get_spouse(legacy_id)
                for spouse_legacy_id in spouses:
                    spouse_crm_id = self._find_crm_id_by_legacy(spouse_legacy_id, person_id_map)
                    if spouse_crm_id:
                        key = tuple(sorted([p.id, spouse_crm_id])) + ("sp",)
                        if key not in added_edges:
                            elements.append({
                                "data": {
                                    "id": f"e{min(p.id,spouse_crm_id)}_{max(p.id,spouse_crm_id)}_sp",
                                    "source": f"p{p.id}",
                                    "target": f"p{spouse_crm_id}",
                                    "type": "spouse"
                                }
                            })
                            added_edges.add(key)
            except:
                pass

            try:
                siblings = self.family_graph.get_siblings(legacy_id)
                for sibling_legacy_id in siblings:
                    sibling_crm_id = self._find_crm_id_by_legacy(sibling_legacy_id, person_id_map)
                    if sibling_crm_id:
                        key = tuple(sorted([p.id, sibling_crm_id])) + ("sib",)
                        if key not in added_edges:
                            elements.append({
                                "data": {
                                    "id": f"e{min(p.id,sibling_crm_id)}_{max(p.id,sibling_crm_id)}_sib",
                                    "source": f"p{p.id}",
                                    "target": f"p{sibling_crm_id}",
                                    "type": "sibling"
                                }
                            })
                            added_edges.add(key)
            except:
                pass

        return json.dumps(elements)

    def _find_in_person_store(self, full_name: str):
        """Find person in legacy PersonStore by name."""
        try:
            matches = self.person_store.find_by_name(full_name)
            for match in matches:
                if match.name.lower() == full_name.lower():
                    return match
        except Exception:
            pass
        return None

    def _find_crm_id_by_legacy(self, legacy_id: int, person_id_map: dict) -> Optional[int]:
        """Find CRM V2 ID given legacy PersonStore ID."""
        for crm_id, leg_id in person_id_map.items():
            if leg_id == legacy_id:
                return crm_id
        return None
    
    def _render_detail_panel(self, persons):
        """Render detail panel using CRM V2 persons."""
        ui.label("Person Details").classes("font-bold mb-2")

        # Filter archived persons
        active_persons = [p for p in persons if not p.is_archived]
        options = {p.id: p.full_name for p in active_persons}

        self.person_select = ui.select(
            options=options,
            label="Select person",
            on_change=lambda e: self._show_details(e.value)
        ).props("dense outlined").classes("w-full mb-3")

        self.detail_box = ui.column().classes("w-full")
        with self.detail_box:
            self._render_legend()
    
    def _show_details(self, person_id: int):
        """Show person details from CRM V2."""
        if not person_id:
            return

        # Get person from CRM V2
        person = self.crm_store.get_person(person_id)
        if not person:
            return

        # Highlight in graph
        ui.run_javascript(f"if(window.cy){{cy.nodes().unselect();cy.$('#p{person_id}').select();}}")

        # Get relationships using legacy ID
        tree = {"parents": [], "spouse": [], "siblings": [], "children": []}
        legacy_person = self._find_in_person_store(person.full_name)
        if legacy_person:
            try:
                tree = self.family_graph.get_family_tree(legacy_person.id)
            except:
                pass

        self.detail_box.clear()
        with self.detail_box:
            ui.label(person.full_name).classes("text-lg font-bold text-indigo-600")

            if person.gender:
                g = "Male" if person.gender == "M" else "Female" if person.gender == "F" else "Other"
                ui.label(g).classes("text-xs text-gray-500")

            if person.family_code:
                ui.label(f"Family: {person.family_code}").classes("text-xs text-gray-500 font-mono")

            ui.separator().classes("my-2")

            # Contact
            ui.label("Contact").classes("text-xs font-bold text-gray-400 uppercase")
            has_contact = False
            if person.phone:
                ui.label(f"📞 {person.phone}").classes("text-sm")
                has_contact = True
            if person.email:
                ui.label(f"✉️ {person.email}").classes("text-sm")
                has_contact = True
            if person.preferred_currency:
                ui.label(f"💰 {person.preferred_currency}").classes("text-sm")
                has_contact = True
            if not has_contact:
                ui.label("No contact info").classes("text-xs text-gray-400")

            # Location
            ui.label("Location").classes("text-xs font-bold text-gray-400 uppercase mt-2")
            loc_parts = [x for x in [person.city, person.state, person.country] if x]
            if loc_parts:
                ui.label(f"📍 {', '.join(loc_parts)}").classes("text-sm")
            else:
                ui.label("No location").classes("text-xs text-gray-400")

            # Occupation
            if person.occupation:
                ui.label("Occupation").classes("text-xs font-bold text-gray-400 uppercase mt-2")
                ui.label(person.occupation).classes("text-sm")

            # Cultural
            if person.gothra or person.nakshatra:
                ui.label("Cultural").classes("text-xs font-bold text-gray-400 uppercase mt-2")
                if person.gothra:
                    ui.label(f"🏛️ Gothra: {person.gothra}").classes("text-sm")
                if person.nakshatra:
                    ui.label(f"⭐ Nakshatra: {person.nakshatra}").classes("text-sm")

            # Interests
            interests = []
            if person.religious_interests:
                interests.extend([i.strip() for i in person.religious_interests.split("\n") if i.strip()])
            if person.spiritual_interests:
                interests.extend([i.strip() for i in person.spiritual_interests.split("\n") if i.strip()])
            if person.social_interests:
                interests.extend([i.strip() for i in person.social_interests.split("\n") if i.strip()])
            if person.hobbies:
                interests.extend([i.strip() for i in person.hobbies.split("\n") if i.strip()])
            if interests:
                ui.label("Interests").classes("text-xs font-bold text-gray-400 uppercase mt-2")
                ui.label(", ".join(interests[:5])).classes("text-sm")

            # Notes
            if person.notes:
                ui.label("Notes").classes("text-xs font-bold text-gray-400 uppercase mt-2")
                ui.label(person.notes[:150]).classes("text-sm text-gray-600 italic")

            # Family
            ui.label("Family").classes("text-xs font-bold text-gray-400 uppercase mt-2")
            has_family = False
            if tree["parents"]:
                ui.label(f"Parents: {', '.join(self._names(tree['parents']))}").classes("text-sm")
                has_family = True
            if tree["spouse"]:
                ui.label(f"Spouse: {', '.join(self._names(tree['spouse']))}").classes("text-sm")
                has_family = True
            if tree["children"]:
                ui.label(f"Children: {', '.join(self._names(tree['children']))}").classes("text-sm")
                has_family = True
            if tree["siblings"]:
                ui.label(f"Siblings: {', '.join(self._names(tree['siblings']))}").classes("text-sm")
                has_family = True
            if not has_family:
                ui.label("No relationships").classes("text-xs text-gray-400")

            # Actions
            ui.separator().classes("my-2")
            with ui.row().classes("gap-1"):
                ui.button("View in CRM", on_click=lambda: ui.notify("Navigate to CRM V2 tab")).props("dense flat size=sm")
                if legacy_person:
                    ui.button("+ Relation", on_click=lambda: self._add_rel(legacy_person.id)).props("dense flat size=sm")

            self._render_legend()
    
    def _names(self, ids):
        return [self.person_store.get_person(i).name for i in ids if self.person_store.get_person(i)]
    
    def _render_legend(self):
        ui.separator().classes("my-3")
        ui.label("Legend").classes("text-xs font-bold text-gray-400 uppercase")
        with ui.row().classes("gap-2 text-xs mt-1"):
            with ui.row().classes("items-center gap-1"):
                ui.element('div').classes("w-3 h-3 bg-blue-400 rounded-sm")
                ui.label("Male")
            with ui.row().classes("items-center gap-1"):
                ui.element('div').classes("w-3 h-3 bg-pink-400 rounded-full")
                ui.label("Female")
        ui.label("── Parent→Child").classes("text-xs text-blue-300")
        ui.label("- - Spouse").classes("text-xs text-pink-300")
        ui.label("··· Sibling").classes("text-xs text-purple-300")
    
    def _add_rel(self, person_id):
        person = self.person_store.get_person(person_id)
        others = {p.id: p.name for p in self.person_store.get_all() if p.id != person_id}
        if not others:
            ui.notify("No other persons")
            return
        with ui.dialog() as dlg, ui.card().classes("w-80 p-3"):
            ui.label(f"Add Relationship").classes("font-bold")
            ui.label(f"For: {person.name}").classes("text-sm text-gray-500")
            other = ui.select(others, label="Person").props("dense outlined").classes("w-full")
            rel = ui.select({
                "spouse": "Spouse",
                "parent": f"{person.name} is PARENT",
                "child": f"{person.name} is CHILD",
                "sibling": "Sibling"
            }, label="Relationship").props("dense outlined").classes("w-full")
            with ui.row().classes("gap-2 mt-3 justify-end"):
                ui.button("Cancel", on_click=dlg.close).props("flat")
                def add():
                    if not other.value or not rel.value:
                        ui.notify("Select both", type="warning")
                        return
                    try:
                        if rel.value == "spouse":
                            self.family_graph.add_spouse(person_id, other.value)
                        elif rel.value == "parent":
                            self.family_graph.add_parent_child(person_id, other.value)
                        elif rel.value == "child":
                            self.family_graph.add_parent_child(other.value, person_id)
                        elif rel.value == "sibling":
                            self.family_graph.add_sibling(person_id, other.value)
                        ui.notify("Added! Refresh to see.")
                        dlg.close()
                    except Exception as e:
                        ui.notify(str(e), type="negative")
                ui.button("Add", on_click=add).props("color=primary")
        dlg.open()
