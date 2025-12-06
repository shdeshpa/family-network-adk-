"""
Supervisor Agent - Validates and enhances extraction results.

Responsibilities:
1. Validate extracted data for consistency
2. Normalize multilingual relationship terms
3. Add reciprocal relationships
4. Infer gender and marital status
5. Assign family name to all members
"""

from dataclasses import dataclass, field
from typing import Optional

from src.agents.adk.extraction_agent import ExtractionResult, ExtractedPerson, ExtractedRelationship
from src.agents.adk.utils.text_utils import TextUtils
from src.agents.adk.utils.relationship_map import RelationshipMap


@dataclass
class ValidatedPerson:
    """Person validated by supervisor."""
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    marital_status: Optional[str] = None  # Married, Single, Unknown
    family_name: Optional[str] = None
    is_speaker: bool = False
    confidence: float = 1.0
    notes: list[str] = field(default_factory=list)


@dataclass
class ValidatedRelationship:
    """Relationship validated with reciprocal."""
    person1: str
    person2: str
    relation_type: str       # PARENT_OF, CHILD_OF, SPOUSE_OF, SIBLING_OF
    specific_relation: str   # father, mother, husband, wife, brother, sister
    is_reciprocal: bool = False


@dataclass
class SupervisorResult:
    """Result from supervisor agent."""
    persons: list[ValidatedPerson]
    relationships: list[ValidatedRelationship]
    family_name: Optional[str]
    validation_notes: list[str]
    success: bool = True
    error: Optional[str] = None


class SupervisorAgent:
    """Agent that validates and enhances extraction results."""
    
    def __init__(self):
        self.relationship_map = RelationshipMap()
        self.text_utils = TextUtils()
    
    def validate(self, extraction: ExtractionResult) -> SupervisorResult:
        """
        Validate and enhance extraction results.
        
        Args:
            extraction: Result from ExtractionAgent
            
        Returns:
            SupervisorResult with validated data
        """
        notes = []
        
        if not extraction.success:
            return SupervisorResult(
                persons=[],
                relationships=[],
                family_name=None,
                validation_notes=[f"Extraction failed: {extraction.error}"],
                success=False,
                error=extraction.error
            )
        
        # Step 1: Extract family name from all person names
        all_names = [p.name for p in extraction.persons]
        family_name = self.text_utils.extract_family_name(all_names)
        if family_name:
            notes.append(f"Identified family name: {family_name}")
        
        # Step 2: Validate and enhance persons
        validated_persons = self._validate_persons(
            extraction.persons, 
            extraction.relationships,
            family_name
        )
        
        # Step 3: Build relationships with reciprocals
        validated_relationships = self._build_relationships(
            extraction.relationships,
            validated_persons
        )
        
        # Step 4: Update marital status from relationships
        self._update_marital_status(validated_persons, validated_relationships, notes)
        
        return SupervisorResult(
            persons=validated_persons,
            relationships=validated_relationships,
            family_name=family_name,
            validation_notes=notes,
            success=True
        )
    
    def _validate_persons(
        self, 
        persons: list[ExtractedPerson],
        relationships: list[ExtractedRelationship],
        family_name: Optional[str]
    ) -> list[ValidatedPerson]:
        """Validate and enhance person data."""
        validated = []
        
        for p in persons:
            # Infer gender from relationships if not set
            gender = p.gender
            if not gender:
                gender = self._infer_gender_from_relationships(p.name, relationships)
            if not gender:
                gender = self.text_utils.infer_gender_from_name(p.name)
            
            validated.append(ValidatedPerson(
                name=self.text_utils.clean_name(p.name),
                gender=gender,
                age=p.age,
                location=p.location,
                occupation=p.occupation,
                family_name=family_name,
                is_speaker=p.is_speaker,
                marital_status="Unknown"
            ))
        
        return validated
    
    def _infer_gender_from_relationships(
        self, 
        name: str, 
        relationships: list[ExtractedRelationship]
    ) -> Optional[str]:
        """Infer gender from relationship terms."""
        for rel in relationships:
            # Check if this person is mentioned with a gendered term
            if rel.person2.lower() == name.lower():
                info = self.relationship_map.normalize(rel.relation_term)
                if info and info.gender:
                    return info.gender
        return None
    
    def _build_relationships(
        self,
        extracted: list[ExtractedRelationship],
        persons: list[ValidatedPerson]
    ) -> list[ValidatedRelationship]:
        """Build validated relationships with reciprocals."""
        validated = []
        person_map = {p.name.lower(): p for p in persons}
        
        for rel in extracted:
            info = self.relationship_map.normalize(rel.relation_term)
            
            if not info:
                # Unknown relationship, skip
                continue
            
            # Map relation_type to graph edge type
            edge_type = self._get_edge_type(info.relation_type)
            
            # Get person genders for specific labels
            p1 = person_map.get(rel.person1.lower())
            p2 = person_map.get(rel.person2.lower())
            
            p1_gender = p1.gender if p1 else None
            p2_gender = p2.gender if p2 else None
            
            # Forward relationship
            specific = self._get_specific_label(info.relation_type, p1_gender, "forward")
            validated.append(ValidatedRelationship(
                person1=rel.person1,
                person2=rel.person2,
                relation_type=edge_type,
                specific_relation=specific,
                is_reciprocal=False
            ))
            
            # Reciprocal relationship
            reciprocal_edge = self._get_reciprocal_edge_type(edge_type)
            reciprocal_specific = self._get_specific_label(
                self._get_reciprocal_relation_type(info.relation_type),
                p2_gender,
                "forward"
            )
            
            validated.append(ValidatedRelationship(
                person1=rel.person2,
                person2=rel.person1,
                relation_type=reciprocal_edge,
                specific_relation=reciprocal_specific,
                is_reciprocal=True
            ))
        
        return validated
    
    def _get_edge_type(self, relation_type: str) -> str:
        """Convert relation type to graph edge type."""
        mapping = {
            "parent": "PARENT_OF",
            "child": "CHILD_OF",
            "spouse": "SPOUSE_OF",
            "sibling": "SIBLING_OF",
            "grandparent": "GRANDPARENT_OF",
            "grandchild": "GRANDCHILD_OF",
            "extended": "RELATIVE_OF"
        }
        return mapping.get(relation_type, "RELATIVE_OF")
    
    def _get_reciprocal_edge_type(self, edge_type: str) -> str:
        """Get reciprocal edge type."""
        mapping = {
            "PARENT_OF": "CHILD_OF",
            "CHILD_OF": "PARENT_OF",
            "SPOUSE_OF": "SPOUSE_OF",
            "SIBLING_OF": "SIBLING_OF",
            "GRANDPARENT_OF": "GRANDCHILD_OF",
            "GRANDCHILD_OF": "GRANDPARENT_OF"
        }
        return mapping.get(edge_type, edge_type)
    
    def _get_reciprocal_relation_type(self, relation_type: str) -> str:
        """Get reciprocal relation type."""
        mapping = {
            "parent": "child",
            "child": "parent",
            "spouse": "spouse",
            "sibling": "sibling"
        }
        return mapping.get(relation_type, relation_type)
    
    def _get_specific_label(self, relation_type: str, gender: Optional[str], direction: str) -> str:
        """Get specific relationship label based on gender."""
        labels = {
            ("parent", "M"): "father",
            ("parent", "F"): "mother",
            ("parent", None): "parent",
            ("child", "M"): "son",
            ("child", "F"): "daughter",
            ("child", None): "child",
            ("spouse", "M"): "husband",
            ("spouse", "F"): "wife",
            ("spouse", None): "spouse",
            ("sibling", "M"): "brother",
            ("sibling", "F"): "sister",
            ("sibling", None): "sibling",
        }
        return labels.get((relation_type, gender), relation_type)
    
    def _update_marital_status(
        self,
        persons: list[ValidatedPerson],
        relationships: list[ValidatedRelationship],
        notes: list[str]
    ):
        """Update marital status based on relationships."""
        married_persons = set()
        
        for rel in relationships:
            if rel.relation_type == "SPOUSE_OF":
                married_persons.add(rel.person1.lower())
                married_persons.add(rel.person2.lower())
        
        for person in persons:
            if person.name.lower() in married_persons:
                person.marital_status = "Married"
                notes.append(f"Inferred {person.name} is Married from spouse relationship")


# Convenience function
def validate_extraction(extraction: ExtractionResult) -> SupervisorResult:
    """Validate extraction results."""
    agent = SupervisorAgent()
    return agent.validate(extraction)
