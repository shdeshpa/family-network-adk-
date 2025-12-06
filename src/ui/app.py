"""Main NiceGUI application."""

from nicegui import ui


def create_app():
    """Create the main application with tabs."""
    
    @ui.page("/")
    def main_page():
        ui.label("Family Network").classes("text-3xl font-bold mb-4")
        
        with ui.tabs().classes("w-full") as tabs:
            tab_audio = ui.tab("Audio Input", icon="mic")
            tab_graph = ui.tab("Graph Data", icon="hub")
        
        with ui.tab_panels(tabs, value=tab_audio).classes("w-full") as panels:
            with ui.tab_panel(tab_audio):
                from src.ui.pages.audio_page import create_audio_page
                create_audio_page()
            
            with ui.tab_panel(tab_graph) as graph_panel:
                graph_container = ui.column().classes("w-full")
                
                def load_graph():
                    graph_container.clear()
                    with graph_container:
                        from src.ui.pages.graph_page import create_graph_page
                        create_graph_page()
                
                load_graph()
                
                # Reload when tab is selected
                tabs.on_value_change(lambda e: load_graph() if e.value == tab_graph else None)
    
    return main_page


if __name__ == "__main__":
    create_app()
    ui.run(title="Family Network", port=8080)
