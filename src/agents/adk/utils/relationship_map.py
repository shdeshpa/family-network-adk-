"""Multilingual relationship mappings."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RelationInfo:
    """Normalized relationship information."""
    term: str
    relation_type: str
    gender: Optional[str]
    implies_married: bool
    reciprocal: str


class RelationshipMap:
    """Multilingual relationship normalizer."""
    
    MAPPINGS = {
        # ENGLISH - FAMILY
        "father": RelationInfo("father", "parent_child", "M", True, "child"),
        "mother": RelationInfo("mother", "parent_child", "F", True, "child"),
        "dad": RelationInfo("father", "parent_child", "M", True, "child"),
        "mom": RelationInfo("mother", "parent_child", "F", True, "child"),
        "son": RelationInfo("son", "parent_child", "M", False, "parent"),
        "daughter": RelationInfo("daughter", "parent_child", "F", False, "parent"),
        "husband": RelationInfo("husband", "spouse", "M", True, "wife"),
        "wife": RelationInfo("wife", "spouse", "F", True, "husband"),
        "brother": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "sister": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "grandfather": RelationInfo("grandfather", "parent_child", "M", True, "grandchild"),
        "grandmother": RelationInfo("grandmother", "parent_child", "F", True, "grandchild"),
        "uncle": RelationInfo("uncle", "extended", "M", False, "nephew_niece"),
        "aunt": RelationInfo("aunt", "extended", "F", False, "nephew_niece"),

        # ENGLISH - NON-FAMILY (SOCIAL/PROFESSIONAL)
        "friend": RelationInfo("friend", "friend_of", None, False, "friend"),
        "colleague": RelationInfo("colleague", "colleague", None, False, "colleague"),
        "coworker": RelationInfo("colleague", "colleague", None, False, "colleague"),
        "boss": RelationInfo("boss", "colleague", None, False, "employee"),
        "manager": RelationInfo("boss", "colleague", None, False, "employee"),
        "employee": RelationInfo("employee", "colleague", None, False, "boss"),
        "mentor": RelationInfo("mentor", "mentor", None, False, "mentee"),
        "mentee": RelationInfo("mentee", "mentor", None, False, "mentor"),
        "teacher": RelationInfo("teacher", "mentor", None, False, "student"),
        "student": RelationInfo("student", "mentor", None, False, "teacher"),
        "fan": RelationInfo("fan", "fan_of", None, False, "celebrity"),
        "fan of": RelationInfo("fan", "fan_of", None, False, "celebrity"),
        "follower": RelationInfo("fan", "fan_of", None, False, "celebrity"),
        "admirer": RelationInfo("fan", "fan_of", None, False, "celebrity"),
        "neighbor": RelationInfo("neighbor", "neighbor", None, False, "neighbor"),
        "roommate": RelationInfo("roommate", "roommate", None, False, "roommate"),
        "classmate": RelationInfo("classmate", "classmate", None, False, "classmate"),
        
        # HINDI
        "pita": RelationInfo("father", "parent_child", "M", True, "child"),
        "mata": RelationInfo("mother", "parent_child", "F", True, "child"),
        "maa": RelationInfo("mother", "parent_child", "F", True, "child"),
        "beta": RelationInfo("son", "parent_child", "M", False, "parent"),
        "beti": RelationInfo("daughter", "parent_child", "F", False, "parent"),
        "bhai": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "behen": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "pati": RelationInfo("husband", "spouse", "M", True, "wife"),
        "patni": RelationInfo("wife", "spouse", "F", True, "husband"),
        "dadi": RelationInfo("grandmother", "parent_child", "F", True, "grandchild"),
        "dada": RelationInfo("grandfather", "parent_child", "M", True, "grandchild"),
        "chacha": RelationInfo("uncle", "extended", "M", True, "nephew_niece"),

        # MARATHI
        "baba": RelationInfo("father", "parent_child", "M", True, "child"),
        "aai": RelationInfo("mother", "parent_child", "F", True, "child"),
        "bhau": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "bhaau": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "bahin": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "mulga": RelationInfo("son", "parent_child", "M", False, "parent"),
        "mulgi": RelationInfo("daughter", "parent_child", "F", False, "parent"),
        "navra": RelationInfo("husband", "spouse", "M", True, "wife"),
        "bayko": RelationInfo("wife", "spouse", "F", True, "husband"),
        "aaji": RelationInfo("grandmother", "parent_child", "F", True, "grandchild"),
        "ajoba": RelationInfo("grandfather", "parent_child", "M", True, "grandchild"),
        "kaka": RelationInfo("uncle", "extended", "M", True, "nephew_niece"),
        "kaku": RelationInfo("aunt", "extended", "F", True, "nephew_niece"),

        # TAMIL
        "appa": RelationInfo("father", "parent_child", "M", True, "child"),
        "amma": RelationInfo("mother", "parent_child", "F", True, "child"),
        "anna": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "thambi": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "akka": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "thangai": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "paati": RelationInfo("grandmother", "parent_child", "F", True, "grandchild"),
        "thatha": RelationInfo("grandfather", "parent_child", "M", True, "grandchild"),

        # TELUGU
        "nanna": RelationInfo("father", "parent_child", "M", True, "child"),
        "tammudu": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "chelli": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "ammamma": RelationInfo("grandmother", "parent_child", "F", True, "grandchild"),
        "babai": RelationInfo("uncle", "extended", "M", True, "nephew_niece"),
    }
    
    def normalize(self, term: str) -> Optional[RelationInfo]:
        """Normalize a relationship term to standard form."""
        if not term:
            return None
        return self.MAPPINGS.get(term.lower().strip())
    
    def is_known_term(self, term: str) -> bool:
        """Check if term exists in mappings."""
        if not term:
            return False
        return term.lower().strip() in self.MAPPINGS
    
    def get_gender_for_relation(self, term: str) -> Optional[str]:
        """Get implied gender for a relationship term."""
        info = self.normalize(term)
        return info.gender if info else None
    
    def get_reciprocal(self, term: str, other_gender: Optional[str] = None) -> str:
        """Get reciprocal relationship term."""
        info = self.normalize(term)
        if not info:
            return "relative"

        if info.relation_type == "parent_child":
            # If the term is a parent term, reciprocal is a child term
            if info.term in ["father", "mother", "grandfather", "grandmother"]:
                return "son" if other_gender == "M" else "daughter" if other_gender == "F" else "child"
            # If the term is a child term, reciprocal is a parent term
            else:
                return "father" if other_gender == "M" else "mother" if other_gender == "F" else "parent"
        elif info.relation_type == "sibling":
            return "brother" if other_gender == "M" else "sister" if other_gender == "F" else "sibling"

        return info.reciprocal
