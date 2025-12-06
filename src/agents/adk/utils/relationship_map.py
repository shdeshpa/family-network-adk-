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
        # ENGLISH
        "father": RelationInfo("father", "parent", "M", True, "child"),
        "mother": RelationInfo("mother", "parent", "F", True, "child"),
        "dad": RelationInfo("father", "parent", "M", True, "child"),
        "mom": RelationInfo("mother", "parent", "F", True, "child"),
        "son": RelationInfo("son", "child", "M", False, "parent"),
        "daughter": RelationInfo("daughter", "child", "F", False, "parent"),
        "husband": RelationInfo("husband", "spouse", "M", True, "wife"),
        "wife": RelationInfo("wife", "spouse", "F", True, "husband"),
        "brother": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "sister": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "grandfather": RelationInfo("grandfather", "grandparent", "M", True, "grandchild"),
        "grandmother": RelationInfo("grandmother", "grandparent", "F", True, "grandchild"),
        "uncle": RelationInfo("uncle", "extended", "M", False, "nephew_niece"),
        "aunt": RelationInfo("aunt", "extended", "F", False, "nephew_niece"),
        
        # HINDI
        "pita": RelationInfo("father", "parent", "M", True, "child"),
        "mata": RelationInfo("mother", "parent", "F", True, "child"),
        "maa": RelationInfo("mother", "parent", "F", True, "child"),
        "beta": RelationInfo("son", "child", "M", False, "parent"),
        "beti": RelationInfo("daughter", "child", "F", False, "parent"),
        "bhai": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "behen": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "pati": RelationInfo("husband", "spouse", "M", True, "wife"),
        "patni": RelationInfo("wife", "spouse", "F", True, "husband"),
        "dadi": RelationInfo("grandmother", "grandparent", "F", True, "grandchild"),
        "dada": RelationInfo("grandfather", "grandparent", "M", True, "grandchild"),
        "chacha": RelationInfo("uncle", "extended", "M", True, "nephew_niece"),
        
        # MARATHI
        "baba": RelationInfo("father", "parent", "M", True, "child"),
        "aai": RelationInfo("mother", "parent", "F", True, "child"),
        "bhau": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "bhaau": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "bahin": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "mulga": RelationInfo("son", "child", "M", False, "parent"),
        "mulgi": RelationInfo("daughter", "child", "F", False, "parent"),
        "navra": RelationInfo("husband", "spouse", "M", True, "wife"),
        "bayko": RelationInfo("wife", "spouse", "F", True, "husband"),
        "aaji": RelationInfo("grandmother", "grandparent", "F", True, "grandchild"),
        "ajoba": RelationInfo("grandfather", "grandparent", "M", True, "grandchild"),
        "kaka": RelationInfo("uncle", "extended", "M", True, "nephew_niece"),
        "kaku": RelationInfo("aunt", "extended", "F", True, "nephew_niece"),
        
        # TAMIL
        "appa": RelationInfo("father", "parent", "M", True, "child"),
        "amma": RelationInfo("mother", "parent", "F", True, "child"),
        "anna": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "thambi": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "akka": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "thangai": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "paati": RelationInfo("grandmother", "grandparent", "F", True, "grandchild"),
        "thatha": RelationInfo("grandfather", "grandparent", "M", True, "grandchild"),
        
        # TELUGU
        "nanna": RelationInfo("father", "parent", "M", True, "child"),
        "tammudu": RelationInfo("brother", "sibling", "M", False, "sibling"),
        "chelli": RelationInfo("sister", "sibling", "F", False, "sibling"),
        "ammamma": RelationInfo("grandmother", "grandparent", "F", True, "grandchild"),
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
        
        if info.relation_type == "parent":
            return "son" if other_gender == "M" else "daughter" if other_gender == "F" else "child"
        elif info.relation_type == "child":
            return "father" if other_gender == "M" else "mother" if other_gender == "F" else "parent"
        elif info.relation_type == "sibling":
            return "brother" if other_gender == "M" else "sister" if other_gender == "F" else "sibling"
        
        return info.reciprocal
