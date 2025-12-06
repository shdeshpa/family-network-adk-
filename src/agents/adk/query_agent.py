"""
Query Agent - natural language queries for family CRM.

Author: Shrinivas Deshpande
Date: December 6, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from src.agents.adk.llm_client import LLMClient
from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.family_registry import FamilyRegistry
from src.graph.text_history import TextHistory
from src.graph.family_graph import FamilyGraph
from src.graph.person_store import PersonStore


class QueryAgent:
    """Answer natural language questions about the family network."""

    SYSTEM = """You are a helpful family network assistant. Answer questions about family members, relationships, and contacts based ONLY on the provided data.

CRITICAL RULES:
- ONLY use information explicitly provided in the Family Database section
- If a person is not listed, say "I don't have information about that person"
- NEVER make up or infer information not in the database
- If no data exists, say "The family database is empty"
- Be concise and friendly

When listing people, format nicely with bullet points.
When describing relationships, be clear about who is related to whom.

Use the text history for additional context, but prioritize the structured database."""

    def __init__(self, provider: str = "ollama"):
        self.llm = LLMClient(provider=provider)
        # Use CRM V2 stores for person profiles
        self.crm_store = CRMStoreV2()
        self.family_registry = FamilyRegistry()
        self.text_history = TextHistory()
        # Use legacy PersonStore + FamilyGraph for relationships
        # (These are still used by GraphAgent for relationship storage)
        self.person_store = PersonStore()
        self.family_graph = FamilyGraph()
    
    def query(self, question: str) -> dict:
        """Answer a question about the family network."""
        # Gather context from CRM V2 and GraphLite
        context = self._build_context()

        if not context["persons"]:
            return {
                "success": True,
                "answer": "The family database is empty. Add some family members first using the Text Input or Record tabs."
            }

        # Get relevant text history
        text_context = self._get_relevant_text_history(question)

        # Search for persons mentioned in question
        person_mentions = self._search_relevant_persons(question)

        prompt = f"""Family Database:
{self._format_context(context)}

{text_context}

{person_mentions}

Question: {question}

IMPORTANT: Base your answer ONLY on the data provided above. Do not make up or infer information."""

        result = self.llm.generate(prompt, system=self.SYSTEM, temperature=0.1)

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
    
    def _search_relevant_persons(self, question: str) -> str:
        """Search for persons mentioned in the question."""
        question_lower = question.lower()
        persons = self.crm_store.get_all()

        mentioned_persons = []
        for p in persons:
            if p.is_archived:
                continue
            # Check if person's name appears in question
            if p.first_name.lower() in question_lower or p.last_name.lower() in question_lower:
                mentioned_persons.append(p.full_name)
            # Check if family code appears
            elif p.family_code and p.family_code.lower() in question_lower:
                mentioned_persons.append(p.full_name)

        if mentioned_persons:
            return f"\nPersons Mentioned in Question: {', '.join(mentioned_persons[:5])}"
        return ""
    
    def _build_context(self) -> dict:
        """Build context from CRM V2 database."""
        # Get all persons from CRM V2
        persons = self.crm_store.get_all()

        context = {
            "persons": [],
            "families": []
        }

        # Get all families
        families = self.family_registry.get_all()
        for family in families:
            if not family.is_archived:
                context["families"].append({
                    "code": family.code,
                    "surname": family.surname,
                    "city": family.city,
                    "description": family.description
                })

        # Build person info with relationships from FamilyGraph
        for p in persons:
            if p.is_archived:
                continue

            person_info = {
                "id": p.id,
                "name": p.full_name,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "gender": p.gender,
                "birth_year": p.birth_year,
                "age": p.approximate_age,
                "occupation": p.occupation,
                "phone": p.phone,
                "email": p.email,
                "city": p.city,
                "state": p.state,
                "country": p.country,
                "family_code": p.family_code,
                "gothra": p.gothra,
                "nakshatra": p.nakshatra,
                "notes": p.notes
            }

            # Get interests (split by newlines)
            interests = []
            if p.religious_interests:
                interests.extend([i.strip() for i in p.religious_interests.split("\n") if i.strip()])
            if p.spiritual_interests:
                interests.extend([i.strip() for i in p.spiritual_interests.split("\n") if i.strip()])
            if p.social_interests:
                interests.extend([i.strip() for i in p.social_interests.split("\n") if i.strip()])
            if p.hobbies:
                interests.extend([i.strip() for i in p.hobbies.split("\n") if i.strip()])
            person_info["interests"] = interests

            # Get relationships from FamilyGraph by matching name to PersonStore
            # (GraphAgent stores in PersonStore with relationships in FamilyGraph)
            person_store_record = self._find_in_person_store(p.full_name)
            if person_store_record:
                relationships = self._get_relationships_from_graph(p.full_name, person_store_record.id)
                person_info.update(relationships)
            else:
                # No legacy record - no relationships
                person_info.update({
                    "spouse": [],
                    "children": [],
                    "parents": [],
                    "siblings": []
                })

            context["persons"].append(person_info)

        return context
    
    def _get_relationships_from_graph(self, person_name: str, person_id: int) -> dict:
        """Get relationships for a person from FamilyGraph using person ID."""
        relationships = {
            "spouse": [],
            "children": [],
            "parents": [],
            "siblings": []
        }

        if not person_id:
            return relationships

        try:
            # Get relationship IDs from FamilyGraph
            spouse_ids = self.family_graph.get_spouse(person_id)
            children_ids = self.family_graph.get_children(person_id)
            parent_ids = self.family_graph.get_parents(person_id)
            sibling_ids = self.family_graph.get_siblings(person_id)

            # Convert IDs to names
            relationships["spouse"] = self._ids_to_names(spouse_ids)
            relationships["children"] = self._ids_to_names(children_ids)
            relationships["parents"] = self._ids_to_names(parent_ids)
            relationships["siblings"] = self._ids_to_names(sibling_ids)

        except Exception:
            # Graph query failed - return empty relationships
            pass

        return relationships

    def _ids_to_names(self, person_ids: list[int]) -> list[str]:
        """Convert person IDs to names using PersonStore."""
        names = []
        for pid in person_ids:
            person = self.person_store.get_person(pid)
            if person:
                names.append(person.name)
        return names

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
    
    def _format_context(self, context: dict) -> str:
        """Format context for LLM with strict data grounding."""
        lines = []

        # Add families if any
        if context.get("families"):
            lines.append("FAMILIES:")
            for fam in context["families"]:
                lines.append(f"  - {fam['code']}: {fam['surname']} family from {fam['city']}")
            lines.append("")

        # Add persons
        if not context.get("persons"):
            return "No persons in database."

        lines.append("PERSONS:")
        for p in context["persons"]:
            # Basic info line
            parts = [f"- {p['name']}"]

            if p.get("gender"):
                gender_map = {"M": "Male", "F": "Female", "O": "Other"}
                parts.append(gender_map.get(p["gender"], p["gender"]))

            if p.get("age"):
                parts.append(f"age {p['age']}")
            elif p.get("birth_year"):
                parts.append(f"born {p['birth_year']}")

            # Location
            location_parts = []
            if p.get("city"):
                location_parts.append(p["city"])
            if p.get("state"):
                location_parts.append(p["state"])
            if p.get("country"):
                location_parts.append(p["country"])
            if location_parts:
                parts.append(f"from {', '.join(location_parts)}")

            if p.get("occupation"):
                parts.append(f"works as {p['occupation']}")

            lines.append(", ".join(parts))

            # Family code
            if p.get("family_code"):
                lines.append(f"  Family: {p['family_code']}")

            # Contact
            if p.get("phone"):
                lines.append(f"  Phone: {p['phone']}")
            if p.get("email"):
                lines.append(f"  Email: {p['email']}")

            # Relationships
            if p.get("spouse"):
                lines.append(f"  Spouse: {', '.join(p['spouse'])}")
            if p.get("children"):
                lines.append(f"  Children: {', '.join(p['children'])}")
            if p.get("parents"):
                lines.append(f"  Parents: {', '.join(p['parents'])}")
            if p.get("siblings"):
                lines.append(f"  Siblings: {', '.join(p['siblings'])}")

            # Cultural info
            if p.get("gothra"):
                lines.append(f"  Gothra: {p['gothra']}")
            if p.get("nakshatra"):
                lines.append(f"  Nakshatra: {p['nakshatra']}")

            # Interests
            if p.get("interests"):
                lines.append(f"  Interests: {', '.join(p['interests'][:10])}")  # Limit to 10

            # Notes
            if p.get("notes"):
                lines.append(f"  Notes: {p['notes'][:150]}")  # Truncate long notes

            lines.append("")  # Blank line between persons

        return "\n".join(lines)