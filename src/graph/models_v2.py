"""
Enhanced data models for CRM V2.

Models:
- Family: Family group with auto-generated code (SHARMA-HYD-001)
- PersonProfileV2: Extended person profile with family linkage
- Donation: Donation records linked to persons

These are pure data structures - NO database logic here.
MCP tools use these for request/response typing.

Author: Shrinivas Deshpande
Date: December 6, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


@dataclass
class Family:
    """Family group with unique identifier."""
    id: Optional[int] = None
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    code: str = ""              # SHARMA-HYD-001
    surname: str = ""           # Original surname
    city: str = ""              # Original city
    description: str = ""
    is_archived: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        if not self.uuid:
            self.uuid = str(uuid.uuid4())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for MCP responses."""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "code": self.code,
            "surname": self.surname,
            "city": self.city,
            "description": self.description,
            "is_archived": self.is_archived,
            "created_at": self.created_at
        }


@dataclass
class PersonProfileV2:
    """Enhanced person profile with family linkage and extended fields."""
    
    # Identity
    id: Optional[int] = None
    family_id: Optional[int] = None
    family_uuid: str = ""
    family_code: str = ""       # Denormalized for easy display/sorting
    
    # Basic Info
    first_name: str = ""
    last_name: str = ""
    gender: str = ""            # M, F, O
    birth_year: Optional[int] = None
    occupation: str = ""
    
    # Contact
    phone: str = ""
    email: str = ""
    preferred_currency: str = "USD"
    
    # Location
    city: str = ""
    state: str = ""
    country: str = ""
    
    # Cultural
    gothra: str = ""
    nakshatra: str = ""
    
    # Interests (free-text, newline-separated for textarea)
    religious_interests: str = ""
    spiritual_interests: str = ""
    social_interests: str = ""
    hobbies: str = ""
    
    # Meta
    notes: str = ""
    is_archived: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def full_name(self) -> str:
        """Return full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def approximate_age(self) -> Optional[int]:
        """Calculate approximate age from birth year."""
        if self.birth_year:
            return datetime.now().year - self.birth_year
        return None
    
    def get_interests_list(self, category: str) -> list[str]:
        """Get interests as list for a category."""
        text = getattr(self, category, "")
        if not text:
            return []
        return [line.strip() for line in text.split("\n") if line.strip()]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for MCP responses."""
        return {
            "id": self.id,
            "family_id": self.family_id,
            "family_uuid": self.family_uuid,
            "family_code": self.family_code,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "gender": self.gender,
            "birth_year": self.birth_year,
            "approximate_age": self.approximate_age,
            "occupation": self.occupation,
            "phone": self.phone,
            "email": self.email,
            "preferred_currency": self.preferred_currency,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "gothra": self.gothra,
            "nakshatra": self.nakshatra,
            "religious_interests": self.religious_interests,
            "spiritual_interests": self.spiritual_interests,
            "social_interests": self.social_interests,
            "hobbies": self.hobbies,
            "notes": self.notes,
            "is_archived": self.is_archived,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class Donation:
    """Donation record linked to a person."""
    
    id: Optional[int] = None
    person_id: int = 0
    
    # Donation details
    amount: float = 0.0
    currency: str = "USD"
    cause: str = ""             # e.g., "Temple Construction"
    deity: str = ""             # e.g., "Lord Ganesha"
    
    # Transaction info
    donation_date: str = ""     # ISO date string
    payment_method: str = ""    # cash, check, online, upi
    receipt_number: str = ""
    
    # Meta
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for MCP responses."""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "amount": self.amount,
            "currency": self.currency,
            "cause": self.cause,
            "deity": self.deity,
            "donation_date": self.donation_date,
            "payment_method": self.payment_method,
            "receipt_number": self.receipt_number,
            "notes": self.notes,
            "created_at": self.created_at
        }


# =============================================================================
# CONSTANTS (for UI dropdowns and validation)
# =============================================================================

GENDER_OPTIONS = {
    "": "Not specified",
    "M": "Male",
    "F": "Female",
    "O": "Other"
}

CURRENCY_OPTIONS = {
    "USD": "US Dollar ($)",
    "INR": "Indian Rupee (₹)",
    "EUR": "Euro (€)",
    "GBP": "British Pound (£)",
    "CAD": "Canadian Dollar (C$)",
    "AUD": "Australian Dollar (A$)"
}

PAYMENT_METHODS = {
    "": "Not specified",
    "cash": "Cash",
    "check": "Check",
    "online": "Online Transfer",
    "bank": "Bank Transfer",
    "card": "Credit/Debit Card",
    "upi": "UPI",
    "other": "Other"
}

COMMON_CAUSES = [
    "Temple Construction",
    "Temple Maintenance",
    "Education Fund",
    "Food Distribution",
    "Festival Celebration",
    "Charitable Trust",
    "Medical Aid",
    "Community Service"
]

COMMON_DEITIES = [
    "Lord Ganesha",
    "Lord Shiva",
    "Goddess Lakshmi",
    "Lord Vishnu",
    "Goddess Durga",
    "Lord Hanuman",
    "Lord Krishna",
    "Goddess Saraswati",
    "Lord Venkateshwara",
    "General Temple Fund"
]
