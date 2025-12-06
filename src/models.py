"""Data models for family network."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class Person(BaseModel):
    """Person node with attributes."""
    
    id: Optional[int] = None
    name: str
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    interests: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def age(self) -> Optional[int]:
        """Calculate current age."""
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )


class Relationship(BaseModel):
    """Relationship between two persons."""
    
    from_id: int
    to_id: int
    relation_type: str  # parent_of, spouse_of, sibling_of