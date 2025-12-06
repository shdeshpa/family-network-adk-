"""Query Agent - natural language queries for family CRM."""

from src.agents.adk.llm_client import LLMClient
from src.agents.adk.tools import list_all_persons, get_family_tree
from src.graph.person_store import PersonStore
from src.graph.family_graph import FamilyGraph
from src.graph.crm_store import CRMStore
from src.graph.text_history import TextHistory
from src.graph.vector_store import VectorStore
from src.graph.enhanced_crm import EnhancedCRM


class QueryAgent:
    """Answer natural language questions about the family network."""
    
    SYSTEM = """You are a helpful family network assistant. Answer questions about family members, relationships, and contacts based on the provided data.

Be concise and friendly. If you don't have enough information, say so.

When listing people, format nicely with bullet points.
When describing relationships, be clear about who is related to whom.

Use the text history and relevant context to provide comprehensive answers."""
    
    def __init__(self, provider: str = "ollama"):
        self.llm = LLMClient(provider=provider)
        self.person_store = PersonStore()
        self.family_graph = FamilyGraph()
        self.crm_store = CRMStore()
        self.text_history = TextHistory()
        self.enhanced_crm = EnhancedCRM()
        # Vector store might not be available, so wrap in try/except
        try:
            self.vector_store = VectorStore()
        except Exception:
            self.vector_store = None
    
    def query(self, question: str) -> dict:
        """Answer a question about the family network."""
        # Gather context
        context = self._build_context()
        
        if not context["persons"]:
            return {
                "success": True,
                "answer": "The family database is empty. Add some family members first using the Text Input or Record tabs."
            }
        
        # Get relevant text history
        text_context = self._get_relevant_text_history(question)
        
        # Get vector search results
        vector_results = self._vector_search(question)
        
        prompt = f"""Family Database:
{self._format_context(context)}

{text_context}

{vector_results}

Question: {question}

Provide a helpful answer based on the data above. Use the text history and search results to provide detailed context."""
        
        result = self.llm.generate(prompt, system=self.SYSTEM, temperature=0.3)
        
        if result["success"]:
            return {"success": True, "answer": result["text"]}
        else:
            return {"success": False, "answer": f"Error: {result.get('error')}"}
    
    def _get_relevant_text_history(self, question: str, limit: int = 5) -> str:
        """Get relevant text history entries that match the question."""
        entries = self.text_history.get_all(limit=20)
        if not entries:
            return ""
        
        # Simple keyword matching (could be enhanced with semantic search)
        question_lower = question.lower()
        relevant_entries = []
        
        for entry in entries:
            if entry.status == "processed" and entry.text:
                # Check if question keywords appear in text
                text_lower = entry.text.lower()
                if any(word in text_lower for word in question_lower.split() if len(word) > 3):
                    relevant_entries.append(entry.text[:200])  # Truncate long entries
                    if len(relevant_entries) >= limit:
                        break
        
        if relevant_entries:
            return f"\nRelevant Text Input History:\n" + "\n".join([f"- {text}" for text in relevant_entries])
        return ""
    
    def _vector_search(self, question: str, limit: int = 5) -> str:
        """Search vector store for relevant persons."""
        if not self.vector_store:
            return ""
        try:
            results = self.vector_store.search(question, limit=limit)
            if results:
                person_names = [r["name"] for r in results if r.get("score", 0) > 0.3]
                if person_names:
                    return f"\nSemantically Related Persons: {', '.join(person_names)}"
        except Exception:
            pass  # Vector store might not be initialized
        return ""
    
    def _build_context(self) -> dict:
        """Build context from database."""
        persons = self.person_store.get_all()
        
        context = {
            "persons": [],
            "relationships": []
        }
        
        for p in persons:
            person_info = {
                "id": p.id,
                "name": p.name,
                "gender": p.gender,
                "age": p.age,
                "location": p.location,
                "phone": p.phone,
                "email": p.email
            }
            
            # Get relationships
            try:
                tree = self.family_graph.get_family_tree(p.id)
                person_info["spouse"] = self._get_names(tree["spouse"])
                person_info["children"] = self._get_names(tree["children"])
                person_info["parents"] = self._get_names(tree["parents"])
                person_info["siblings"] = self._get_names(tree["siblings"])
            except Exception:
                person_info["spouse"] = []
                person_info["children"] = []
                person_info["parents"] = []
                person_info["siblings"] = []
            
            # Get interests
            try:
                interests = self.crm_store.get_interests(p.id)
                person_info["interests"] = interests if isinstance(interests, list) else []
            except Exception:
                person_info["interests"] = []
            
            # Get Enhanced CRM data
            try:
                crm_profiles = self.enhanced_crm.search(query=p.name.split()[0] if p.name else "")
                for profile in crm_profiles:
                    if profile.full_name.lower() == p.name.lower():
                        if profile.city:
                            person_info["city"] = profile.city
                        if profile.state:
                            person_info["state"] = profile.state
                        if profile.country:
                            person_info["country"] = profile.country
                        if profile.gothra:
                            person_info["gothra"] = profile.gothra
                        if profile.nakshatra:
                            person_info["nakshatra"] = profile.nakshatra
                        if profile.general_interests and isinstance(profile.general_interests, list):
                            person_info["enhanced_interests"] = profile.general_interests
                        if profile.notes:
                            person_info["notes"] = profile.notes
                        break
            except Exception:
                pass
            
            context["persons"].append(person_info)
        
        return context
    
    def _get_names(self, ids: list[int]) -> list[str]:
        """Convert IDs to names."""
        names = []
        for pid in ids:
            p = self.person_store.get_person(pid)
            if p:
                names.append(p.name)
        return names
    
    def _format_context(self, context: dict) -> str:
        """Format context for LLM."""
        lines = []
        for p in context["persons"]:
            parts = [f"- {p['name']}"]
            if p.get("age"):
                parts.append(f"age {p['age']}")
            location_parts = []
            if p.get("location"):
                location_parts.append(p["location"])
            if p.get("city"):
                location_parts.append(p["city"])
            if p.get("state"):
                location_parts.append(p["state"])
            if p.get("country"):
                location_parts.append(p["country"])
            if location_parts:
                parts.append(f"in {', '.join(location_parts)}")
            if p.get("phone"):
                parts.append(f"phone: {p['phone']}")
            
            lines.append(", ".join(parts))
            
            if p.get("spouse"):
                lines.append(f"  Spouse: {', '.join(p['spouse'])}")
            if p.get("children"):
                lines.append(f"  Children: {', '.join(p['children'])}")
            if p.get("parents"):
                lines.append(f"  Parents: {', '.join(p['parents'])}")
            if p.get("siblings"):
                lines.append(f"  Siblings: {', '.join(p['siblings'])}")
            interests_list = []
            base_interests = p.get("interests", [])
            if base_interests and isinstance(base_interests, list):
                interests_list.extend(base_interests)
            enhanced_int = p.get("enhanced_interests", [])
            if enhanced_int and isinstance(enhanced_int, list):
                interests_list.extend(enhanced_int)
            if interests_list:
                lines.append(f"  Interests: {', '.join(str(i) for i in interests_list)}")
            if p.get("gothra"):
                lines.append(f"  Gothra: {p['gothra']}")
            if p.get("nakshatra"):
                lines.append(f"  Nakshatra: {p['nakshatra']}")
            if p.get("notes"):
                lines.append(f"  Notes: {p['notes'][:100]}")
        
        return "\n".join(lines)