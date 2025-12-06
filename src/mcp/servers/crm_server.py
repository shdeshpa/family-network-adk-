"""
CRM MCP Server - FastMCP tools for agent access to CRM data.

This server exposes CRM operations as MCP tools that agents can call.
Agents use these tools to:
- Create and manage families
- Add/update/search person profiles
- Record and query donations

Architecture:
    Agent → MCP Protocol → crm_server.py → Data Layer → SQLite

Tools are organized by domain:
- Family tools: create_family, get_family, list_families
- Profile tools: add_person, get_person, update_person, search_persons
- Donation tools: add_donation, get_donations, donation_summary

Author: Shrikant Deshpande
Date: December 6, 2025
Copyright (c) 2025 Shrikant Deshpande. All rights reserved.
"""

from mcp.server.fastmcp import FastMCP
from typing import Optional, List

from src.graph.family_registry import FamilyRegistry
from src.graph.crm_store_v2 import CRMStoreV2
from src.graph.models_v2 import PersonProfileV2, Donation


# Initialize MCP server
mcp = FastMCP("crm-server")

# Lazy-loaded singletons
_registry: Optional[FamilyRegistry] = None
_store: Optional[CRMStoreV2] = None


def get_registry() -> FamilyRegistry:
    """Get or create FamilyRegistry instance."""
    global _registry
    if _registry is None:
        _registry = FamilyRegistry()
    return _registry


def get_store() -> CRMStoreV2:
    """Get or create CRMStoreV2 instance."""
    global _store
    if _store is None:
        _store = CRMStoreV2()
    return _store


# =============================================================================
# FAMILY TOOLS
# =============================================================================

@mcp.tool()
def create_family(surname: str, city: str, description: str = "") -> dict:
    """
    Create a new family with auto-generated code.
    
    Args:
        surname: Family surname (e.g., "Sharma")
        city: City name (e.g., "Hyderabad")
        description: Optional description
        
    Returns:
        Family details including generated code (e.g., SHARMA-HYD-001)
    """
    registry = get_registry()
    family = registry.create_family(surname, city, description)
    return {
        "success": True,
        "family": family.to_dict()
    }


@mcp.tool()
def preview_family_code(surname: str, city: str) -> dict:
    """
    Preview what family code would be generated without creating.
    
    Useful for confirmation before creating.
    
    Args:
        surname: Family surname
        city: City name
        
    Returns:
        Preview of the code that would be generated
    """
    registry = get_registry()
    code = registry.preview_code(surname, city)
    return {
        "success": True,
        "preview_code": code,
        "note": "This code has not been created yet"
    }


@mcp.tool()
def get_family(code: str = None, family_id: int = None, uuid: str = None) -> dict:
    """
    Get family by code, ID, or UUID.
    
    Provide one of: code, family_id, or uuid.
    
    Args:
        code: Family code (e.g., "SHARMA-HYD-001")
        family_id: Family database ID
        uuid: Family UUID
        
    Returns:
        Family details if found
    """
    registry = get_registry()
    family = None
    
    if code:
        family = registry.get_by_code(code)
    elif family_id:
        family = registry.get_by_id(family_id)
    elif uuid:
        family = registry.get_by_uuid(uuid)
    else:
        return {"success": False, "error": "Provide code, family_id, or uuid"}
    
    if family:
        return {"success": True, "found": True, "family": family.to_dict()}
    return {"success": True, "found": False, "family": None}


@mcp.tool()
def list_families(surname: str = None, city: str = None) -> dict:
    """
    List families with optional filters.
    
    Args:
        surname: Filter by surname (partial match)
        city: Filter by city (partial match)
        
    Returns:
        List of matching families
    """
    registry = get_registry()
    families = registry.find(surname=surname, city=city)
    return {
        "success": True,
        "count": len(families),
        "families": [f.to_dict() for f in families]
    }


@mcp.tool()
def archive_family(family_id: int) -> dict:
    """
    Archive a family (soft delete).
    
    Args:
        family_id: ID of family to archive
        
    Returns:
        Success status
    """
    registry = get_registry()
    success = registry.archive(family_id)
    return {"success": success}


# =============================================================================
# PROFILE TOOLS
# =============================================================================

@mcp.tool()
def add_person(
    first_name: str,
    last_name: str = "",
    gender: str = "",
    birth_year: int = None,
    occupation: str = "",
    phone: str = "",
    email: str = "",
    city: str = "",
    state: str = "",
    country: str = "",
    gothra: str = "",
    nakshatra: str = "",
    religious_interests: str = "",
    spiritual_interests: str = "",
    social_interests: str = "",
    hobbies: str = "",
    notes: str = "",
    family_id: int = None,
    family_uuid: str = "",
    family_code: str = "",
    preferred_currency: str = "USD"
) -> dict:
    """
    Add a new person profile.
    
    Args:
        first_name: First name (required)
        last_name: Last name / surname
        gender: M, F, or O
        birth_year: Year of birth (e.g., 1980)
        occupation: Job/profession
        phone: Phone number
        email: Email address
        city: City of residence
        state: State/province
        country: Country
        gothra: Gothra (cultural)
        nakshatra: Nakshatra (cultural)
        religious_interests: Religious interests (newline-separated)
        spiritual_interests: Spiritual interests (newline-separated)
        social_interests: Social interests (newline-separated)
        hobbies: Hobbies (newline-separated)
        notes: Additional notes
        family_id: Link to family (ID)
        family_uuid: Link to family (UUID)
        family_code: Link to family (code like SHARMA-HYD-001)
        preferred_currency: USD, INR, etc.
        
    Returns:
        Created person with ID
    """
    if not first_name:
        return {"success": False, "error": "first_name is required"}
    
    store = get_store()
    
    profile = PersonProfileV2(
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        birth_year=birth_year,
        occupation=occupation,
        phone=phone,
        email=email,
        city=city,
        state=state,
        country=country,
        gothra=gothra,
        nakshatra=nakshatra,
        religious_interests=religious_interests,
        spiritual_interests=spiritual_interests,
        social_interests=social_interests,
        hobbies=hobbies,
        notes=notes,
        family_id=family_id,
        family_uuid=family_uuid,
        family_code=family_code,
        preferred_currency=preferred_currency
    )
    
    person_id = store.add_person(profile)
    profile.id = person_id
    
    return {
        "success": True,
        "person_id": person_id,
        "person": profile.to_dict()
    }


@mcp.tool()
def get_person(person_id: int) -> dict:
    """
    Get person by ID.
    
    Args:
        person_id: Person database ID
        
    Returns:
        Person profile if found
    """
    store = get_store()
    person = store.get_person(person_id)
    
    if person:
        return {"success": True, "found": True, "person": person.to_dict()}
    return {"success": True, "found": False, "person": None}


@mcp.tool()
def update_person(
    person_id: int,
    first_name: str = None,
    last_name: str = None,
    gender: str = None,
    birth_year: int = None,
    occupation: str = None,
    phone: str = None,
    email: str = None,
    city: str = None,
    state: str = None,
    country: str = None,
    gothra: str = None,
    nakshatra: str = None,
    religious_interests: str = None,
    spiritual_interests: str = None,
    social_interests: str = None,
    hobbies: str = None,
    notes: str = None,
    family_id: int = None,
    family_uuid: str = None,
    family_code: str = None,
    preferred_currency: str = None
) -> dict:
    """
    Update person fields. Only provided fields are updated.
    
    Args:
        person_id: ID of person to update (required)
        ... other fields same as add_person
        
    Returns:
        Success status and updated person
    """
    store = get_store()
    
    # Build kwargs from non-None values
    kwargs = {}
    for field, value in [
        ("first_name", first_name),
        ("last_name", last_name),
        ("gender", gender),
        ("birth_year", birth_year),
        ("occupation", occupation),
        ("phone", phone),
        ("email", email),
        ("city", city),
        ("state", state),
        ("country", country),
        ("gothra", gothra),
        ("nakshatra", nakshatra),
        ("religious_interests", religious_interests),
        ("spiritual_interests", spiritual_interests),
        ("social_interests", social_interests),
        ("hobbies", hobbies),
        ("notes", notes),
        ("family_id", family_id),
        ("family_uuid", family_uuid),
        ("family_code", family_code),
        ("preferred_currency", preferred_currency),
    ]:
        if value is not None:
            kwargs[field] = value
    
    if not kwargs:
        return {"success": False, "error": "No fields to update"}
    
    success = store.update_person(person_id, **kwargs)
    
    if success:
        person = store.get_person(person_id)
        return {"success": True, "person": person.to_dict()}
    return {"success": False, "error": "Person not found or update failed"}


@mcp.tool()
def search_persons(
    query: str = None,
    family_code: str = None,
    city: str = None,
    occupation: str = None,
    gothra: str = None
) -> dict:
    """
    Search persons with filters.
    
    Args:
        query: Search in name, notes, occupation
        family_code: Filter by family code (exact)
        city: Filter by city (partial)
        occupation: Filter by occupation (partial)
        gothra: Filter by gothra (partial)
        
    Returns:
        List of matching persons
    """
    store = get_store()
    persons = store.search(
        query=query,
        family_code=family_code,
        city=city,
        occupation=occupation,
        gothra=gothra
    )
    return {
        "success": True,
        "count": len(persons),
        "persons": [p.to_dict() for p in persons]
    }


@mcp.tool()
def list_persons(family_code: str = None) -> dict:
    """
    List all persons, optionally filtered by family.
    
    Args:
        family_code: Filter by family code
        
    Returns:
        List of persons
    """
    store = get_store()
    if family_code:
        persons = store.get_by_family(family_code)
    else:
        persons = store.get_all()
    return {
        "success": True,
        "count": len(persons),
        "persons": [p.to_dict() for p in persons]
    }


@mcp.tool()
def delete_person(person_id: int) -> dict:
    """
    Delete a person and their donations.
    
    Args:
        person_id: ID of person to delete
        
    Returns:
        Success status
    """
    store = get_store()
    success = store.delete_person(person_id)
    return {"success": success}


@mcp.tool()
def archive_person(person_id: int) -> dict:
    """
    Archive a person (soft delete).
    
    Args:
        person_id: ID of person to archive
        
    Returns:
        Success status
    """
    store = get_store()
    success = store.archive_person(person_id)
    return {"success": success}


@mcp.tool()
def get_family_codes() -> dict:
    """
    Get list of distinct family codes.
    
    Useful for dropdowns/filters.
    
    Returns:
        List of family codes
    """
    store = get_store()
    codes = store.get_family_codes()
    return {
        "success": True,
        "count": len(codes),
        "codes": codes
    }


# =============================================================================
# DONATION TOOLS
# =============================================================================

@mcp.tool()
def add_donation(
    person_id: int,
    amount: float,
    currency: str = "USD",
    cause: str = "",
    deity: str = "",
    donation_date: str = "",
    payment_method: str = "",
    receipt_number: str = "",
    notes: str = ""
) -> dict:
    """
    Add a donation record for a person.
    
    Args:
        person_id: ID of person making donation (required)
        amount: Donation amount (required)
        currency: Currency code (USD, INR, etc.)
        cause: Cause/purpose (e.g., "Temple Construction")
        deity: Deity name (e.g., "Lord Ganesha")
        donation_date: Date of donation (ISO format)
        payment_method: cash, check, online, upi, card
        receipt_number: Receipt/reference number
        notes: Additional notes
        
    Returns:
        Created donation with ID
    """
    if not person_id:
        return {"success": False, "error": "person_id is required"}
    if amount is None or amount <= 0:
        return {"success": False, "error": "amount must be positive"}
    
    store = get_store()
    
    # Verify person exists
    person = store.get_person(person_id)
    if not person:
        return {"success": False, "error": f"Person {person_id} not found"}
    
    donation = Donation(
        person_id=person_id,
        amount=amount,
        currency=currency,
        cause=cause,
        deity=deity,
        donation_date=donation_date,
        payment_method=payment_method,
        receipt_number=receipt_number,
        notes=notes
    )
    
    donation_id = store.add_donation(donation)
    donation.id = donation_id
    
    return {
        "success": True,
        "donation_id": donation_id,
        "donation": donation.to_dict()
    }


@mcp.tool()
def get_donations(person_id: int) -> dict:
    """
    Get all donations for a person.
    
    Args:
        person_id: ID of person
        
    Returns:
        List of donations
    """
    store = get_store()
    donations = store.get_donations_for_person(person_id)
    return {
        "success": True,
        "count": len(donations),
        "donations": [d.to_dict() for d in donations]
    }


@mcp.tool()
def get_donation_summary(person_id: int) -> dict:
    """
    Get donation summary for a person.
    
    Args:
        person_id: ID of person
        
    Returns:
        Summary with totals by currency
    """
    store = get_store()
    summary = store.get_donation_summary(person_id)
    return {
        "success": True,
        "summary": summary
    }


@mcp.tool()
def search_donations(cause: str = None, deity: str = None) -> dict:
    """
    Search donations by cause or deity.
    
    Args:
        cause: Filter by cause (partial match)
        deity: Filter by deity (partial match)
        
    Returns:
        List of donations with person info
    """
    store = get_store()
    
    if cause:
        results = store.get_donations_by_cause(cause)
    elif deity:
        results = store.get_donations_by_deity(deity)
    else:
        return {"success": False, "error": "Provide cause or deity filter"}
    
    return {
        "success": True,
        "count": len(results),
        "results": results
    }


@mcp.tool()
def update_donation(
    donation_id: int,
    amount: float = None,
    currency: str = None,
    cause: str = None,
    deity: str = None,
    donation_date: str = None,
    payment_method: str = None,
    receipt_number: str = None,
    notes: str = None
) -> dict:
    """
    Update donation fields.
    
    Args:
        donation_id: ID of donation to update (required)
        ... other fields to update
        
    Returns:
        Success status
    """
    store = get_store()
    
    kwargs = {}
    for field, value in [
        ("amount", amount),
        ("currency", currency),
        ("cause", cause),
        ("deity", deity),
        ("donation_date", donation_date),
        ("payment_method", payment_method),
        ("receipt_number", receipt_number),
        ("notes", notes),
    ]:
        if value is not None:
            kwargs[field] = value
    
    if not kwargs:
        return {"success": False, "error": "No fields to update"}
    
    success = store.update_donation(donation_id, **kwargs)
    return {"success": success}


@mcp.tool()
def delete_donation(donation_id: int) -> dict:
    """
    Delete a donation.
    
    Args:
        donation_id: ID of donation to delete
        
    Returns:
        Success status
    """
    store = get_store()
    success = store.delete_donation(donation_id)
    return {"success": success}


# =============================================================================
# SERVER ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    mcp.run()
