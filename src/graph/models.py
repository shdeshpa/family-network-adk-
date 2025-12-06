"""Shared data models for graph operations."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PersonNode:
    """Person node with properties."""
    name: str
    gender: Optional[str] = None
    family_name: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    marital_status: Optional[str] = None
    gothra: Optional[str] = None


@dataclass
class QueryResult:
    """Result from a GQL query."""
    success: bool
    columns: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    error: Optional[str] = None
    raw_output: str = ""
    rows_affected: int = 0


@dataclass
class Relationship:
    """Relationship between two persons."""
    from_name: str
    to_name: str
    rel_type: str  # PARENT_OF, SPOUSE_OF, SIBLING_OF, CHILD_OF
    specific: Optional[str] = None  # father, mother, husband, wife, etc.
