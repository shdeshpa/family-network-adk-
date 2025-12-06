"""Network analytics and centrality measures for family graph."""

from typing import Optional
from collections import defaultdict

from src.graph.family_graph import FamilyGraph
from src.graph.person_store import PersonStore


class FamilyAnalytics:
    """Calculate network metrics for family graph."""
    
    def __init__(
        self,
        family_graph: Optional[FamilyGraph] = None,
        person_store: Optional[PersonStore] = None
    ):
        self.graph = family_graph or FamilyGraph()
        self.person_store = person_store or PersonStore()
    
    def get_all_connections(self, person_id: int) -> set[int]:
        """Get all directly connected persons (any relationship)."""
        connections = set()
        connections.update(self.graph.get_parents(person_id))
        connections.update(self.graph.get_children(person_id))
        connections.update(self.graph.get_spouse(person_id))
        connections.update(self.graph.get_siblings(person_id))
        return connections
    
    def degree_centrality(self, person_id: int) -> int:
        """
        Calculate degree centrality (number of direct connections).
        Higher = more connected within family.
        """
        return len(self.get_all_connections(person_id))
    
    def calculate_all_degree_centrality(self, person_ids: list[int]) -> dict[int, int]:
        """Calculate degree centrality for all persons."""
        return {pid: self.degree_centrality(pid) for pid in person_ids}
    
    def find_most_connected(self, person_ids: list[int], top_n: int = 5) -> list[dict]:
        """Find the most connected family members."""
        centralities = self.calculate_all_degree_centrality(person_ids)
        sorted_ids = sorted(centralities.keys(), key=lambda x: centralities[x], reverse=True)
        
        results = []
        for pid in sorted_ids[:top_n]:
            person = self.person_store.get_person(pid)
            results.append({
                "person_id": pid,
                "name": person.name if person else "Unknown",
                "degree_centrality": centralities[pid],
                "connections": list(self.get_all_connections(pid))
            })
        return results
    
    def find_bridges(self, person_ids: list[int]) -> list[dict]:
        """
        Find persons who connect different family branches.
        These are typically spouses who link two families.
        """
        bridges = []
        
        for pid in person_ids:
            spouses = self.graph.get_spouse(pid)
            if spouses:
                # Person with spouse from different family branch
                my_parents = set(self.graph.get_parents(pid))
                
                for spouse_id in spouses:
                    spouse_parents = set(self.graph.get_parents(spouse_id))
                    
                    # If spouse has different parents, this is a bridge
                    if my_parents and spouse_parents and not my_parents.intersection(spouse_parents):
                        person = self.person_store.get_person(pid)
                        bridges.append({
                            "person_id": pid,
                            "name": person.name if person else "Unknown",
                            "spouse_id": spouse_id,
                            "type": "marriage_bridge"
                        })
        
        return bridges
    
    def get_generation_depth(self, person_id: int) -> dict:
        """Calculate generations above and below a person."""
        ancestors = self.graph.get_all_ancestors(person_id)
        descendants = self.graph.get_all_descendants(person_id)
        
        return {
            "person_id": person_id,
            "generations_above": self._count_generations_up(person_id),
            "generations_below": self._count_generations_down(person_id),
            "total_ancestors": len(ancestors),
            "total_descendants": len(descendants)
        }
    
    def _count_generations_up(self, person_id: int, max_depth: int = 10) -> int:
        """Count generations above a person."""
        depth = 0
        current = {person_id}
        
        for _ in range(max_depth):
            parents = set()
            for pid in current:
                parents.update(self.graph.get_parents(pid))
            if not parents:
                break
            depth += 1
            current = parents
        
        return depth
    
    def _count_generations_down(self, person_id: int, max_depth: int = 10) -> int:
        """Count generations below a person."""
        depth = 0
        current = {person_id}
        
        for _ in range(max_depth):
            children = set()
            for pid in current:
                children.update(self.graph.get_children(pid))
            if not children:
                break
            depth += 1
            current = children
        
        return depth
    
    def family_statistics(self, person_ids: list[int]) -> dict:
        """Get overall family network statistics."""
        if not person_ids:
            return {"error": "No persons provided"}
        
        total_connections = sum(self.degree_centrality(pid) for pid in person_ids)
        
        return {
            "total_members": len(person_ids),
            "total_connections": total_connections // 2,  # Divide by 2 since bidirectional
            "avg_connections_per_person": round(total_connections / len(person_ids), 2),
            "most_connected": self.find_most_connected(person_ids, top_n=3),
            "bridges": self.find_bridges(person_ids)
        }