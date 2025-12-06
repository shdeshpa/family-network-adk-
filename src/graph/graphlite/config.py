"""GraphLite connection configuration."""

from dataclasses import dataclass


@dataclass
class GraphLiteConfig:
    """Configuration for GraphLite connection."""
    db_path: str = "data/graphlite_db"
    user: str = "admin"
    password: str = "familynet123"
    schema: str = "family"
    graph: str = "network"
    timeout: int = 30
    
    @property
    def graph_path(self) -> str:
        """Full graph path."""
        return f"/{self.schema}/{self.graph}"
