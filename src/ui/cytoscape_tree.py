"""Interactive family tree using Cytoscape.js."""

from nicegui import ui
from typing import Optional
import json

from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.enhanced_crm import EnhancedCRM


class CytoscapeTree:
    """Interactive family tree with Cytoscape.js."""
    
    def __init__(
        self,
        person_store: PersonStore = None,
        family_graph: FamilyGraph = None,
        enhanced_crm: EnhancedCRM = None
    ):
        self.person_store = person_store or PersonStore()
        self.family_graph = family_graph or FamilyGraph()
        self.crm = enhanced_crm or EnhancedCRM()
    
    def render(self):
        """Render the tree view."""
        persons = self.person_store.get_all()
        
        if not persons:
            ui.label("No family data yet. Add persons using Text Input or CRM tabs.").classes("text-gray-500 p-8")
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
        """Build Cytoscape elements."""
        elements = []
        added_edges = set()
        
        for p in persons:
            elements.append({
                "data": {
                    "id": f"p{p.id}",
                    "personId": p.id,
                    "label": p.name,
                    "gender": p.gender or ""
                }
            })
            
            try:
                children = self.family_graph.get_children(p.id)
                for cid in children:
                    key = (p.id, cid, "pc")
                    if key not in added_edges:
                        elements.append({
                            "data": {
                                "id": f"e{p.id}_{cid}_pc",
                                "source": f"p{p.id}",
                                "target": f"p{cid}",
                                "type": "parent_child"
                            }
                        })
                        added_edges.add(key)
            except:
                pass
            
            try:
                spouses = self.family_graph.get_spouse(p.id)
                for sid in spouses:
                    key = tuple(sorted([p.id, sid])) + ("sp",)
                    if key not in added_edges:
                        elements.append({
                            "data": {
                                "id": f"e{min(p.id,sid)}_{max(p.id,sid)}_sp",
                                "source": f"p{p.id}",
                                "target": f"p{sid}",
                                "type": "spouse"
                            }
                        })
                        added_edges.add(key)
            except:
                pass
            
            try:
                siblings = self.family_graph.get_siblings(p.id)
                for sid in siblings:
                    key = tuple(sorted([p.id, sid])) + ("sib",)
                    if key not in added_edges:
                        elements.append({
                            "data": {
                                "id": f"e{min(p.id,sid)}_{max(p.id,sid)}_sib",
                                "source": f"p{p.id}",
                                "target": f"p{sid}",
                                "type": "sibling"
                            }
                        })
                        added_edges.add(key)
            except:
                pass
        
        return json.dumps(elements)
    
    def _render_detail_panel(self, persons):
        """Render detail panel."""
        ui.label("Person Details").classes("font-bold mb-2")
        
        options = {p.id: p.name for p in persons}
        
        self.person_select = ui.select(
            options=options,
            label="Select person",
            on_change=lambda e: self._show_details(e.value)
        ).props("dense outlined").classes("w-full mb-3")
        
        self.detail_box = ui.column().classes("w-full")
        with self.detail_box:
            self._render_legend()
    
    def _show_details(self, person_id: int):
        """Show person details."""
        if not person_id:
            return
        
        person = self.person_store.get_person(person_id)
        if not person:
            return
        
        # Highlight in graph
        ui.run_javascript(f"if(window.cy){{cy.nodes().unselect();cy.$('#p{person_id}').select();}}")
        
        # Get CRM data
        crm_data = None
        try:
            results = self.crm.search(query=person.name.split()[0])
            for cp in results:
                if cp.full_name.lower() == person.name.lower():
                    crm_data = cp
                    break
        except:
            pass
        
        # Get relationships
        tree = {"parents": [], "spouse": [], "siblings": [], "children": []}
        try:
            tree = self.family_graph.get_family_tree(person_id)
        except:
            pass
        
        self.detail_box.clear()
        with self.detail_box:
            ui.label(person.name).classes("text-lg font-bold text-indigo-600")
            
            if person.gender:
                g = "Male" if person.gender == "M" else "Female" if person.gender == "F" else person.gender
                ui.label(g).classes("text-xs text-gray-500")
            
            ui.separator().classes("my-2")
            
            # Contact
            ui.label("Contact").classes("text-xs font-bold text-gray-400 uppercase")
            has_contact = False
            if crm_data:
                if crm_data.phone:
                    ui.label(f"📞 {crm_data.phone}").classes("text-sm")
                    has_contact = True
                if crm_data.email:
                    ui.label(f"✉️ {crm_data.email}").classes("text-sm")
                    has_contact = True
                if crm_data.preferred_currency:
                    ui.label(f"💰 {crm_data.preferred_currency}").classes("text-sm")
                    has_contact = True
            if person.phone and not has_contact:
                ui.label(f"📞 {person.phone}").classes("text-sm")
                has_contact = True
            if not has_contact:
                ui.label("No contact info").classes("text-xs text-gray-400")
            
            # Location
            ui.label("Location").classes("text-xs font-bold text-gray-400 uppercase mt-2")
            if crm_data and crm_data.city:
                loc = ", ".join([x for x in [crm_data.city, crm_data.state, crm_data.country] if x])
                ui.label(f"📍 {loc}").classes("text-sm")
            elif person.location:
                ui.label(f"📍 {person.location}").classes("text-sm")
            else:
                ui.label("No location").classes("text-xs text-gray-400")
            
            # Cultural
            if crm_data and (crm_data.gothra or crm_data.nakshatra):
                ui.label("Cultural").classes("text-xs font-bold text-gray-400 uppercase mt-2")
                if crm_data.gothra:
                    ui.label(f"🏛️ Gothra: {crm_data.gothra}").classes("text-sm")
                if crm_data.nakshatra:
                    ui.label(f"⭐ Nakshatra: {crm_data.nakshatra}").classes("text-sm")
            
            # Interests
            if crm_data and crm_data.general_interests:
                ui.label("Interests").classes("text-xs font-bold text-gray-400 uppercase mt-2")
                ui.label(", ".join(crm_data.general_interests[:4])).classes("text-sm")
            
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
                ui.button("Edit", on_click=lambda: self._edit(person_id)).props("dense flat size=sm")
                ui.button("+ Relation", on_click=lambda: self._add_rel(person_id)).props("dense flat size=sm")
            
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
    
    def _edit(self, person_id):
        person = self.person_store.get_person(person_id)
        if not person:
            return
        with ui.dialog() as dlg, ui.card().classes("w-80 p-3"):
            ui.label(f"Edit {person.name}").classes("font-bold")
            name = ui.input("Name", value=person.name).props("dense outlined").classes("w-full")
            phone = ui.input("Phone", value=person.phone or "").props("dense outlined").classes("w-full")
            location = ui.input("Location", value=person.location or "").props("dense outlined").classes("w-full")
            with ui.row().classes("gap-2 mt-3 justify-end"):
                ui.button("Cancel", on_click=dlg.close).props("flat")
                def save():
                    self.person_store.update_person(person_id, name=name.value, phone=phone.value, location=location.value)
                    ui.notify("Saved")
                    dlg.close()
                    self._show_details(person_id)
                ui.button("Save", on_click=save).props("color=primary")
        dlg.open()
    
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
