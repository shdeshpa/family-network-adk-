"""
Fuzzy Name Matching Module - Reusable across projects.

Provides intelligent name matching with:
- Spelling variation handling (Alka vs Alaka)
- Pronoun resolution (he/she -> actual person)
- Detailed reasoning logs for debugging
- Phone number matching boost

Author: Shrinivas Deshpande
Date: December 19, 2025
Copyright (c) 2025 Shrinivas Deshpande. All rights reserved.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from difflib import SequenceMatcher
import re
import uuid

from src.graph.crm_store_v2 import CRMStoreV2
from src.agents.adk.utils.agent_trajectory import TrajectoryLogger, StepType


@dataclass
class MatchCandidate:
    """A potential match for a person query."""
    person_id: int
    full_name: str
    phone: Optional[str]
    email: Optional[str]
    city: Optional[str]
    similarity_score: float
    match_reason: str
    confidence: str  # "very_high", "high", "medium", "low"


@dataclass
class MatchResult:
    """Result from fuzzy matching."""
    success: bool
    query: str
    best_match: Optional[MatchCandidate]
    all_matches: List[MatchCandidate]
    reasoning: List[str]  # Step-by-step reasoning
    needs_disambiguation: bool
    error: Optional[str] = None


class FuzzyPersonMatcher:
    """
    Fuzzy person matcher with ReAct pattern logging.

    Handles:
    - Spelling variations (Alka vs Alaka)
    - Honorific removal (Srikanth Garu -> Srikanth)
    - Phone number matching boost
    - Detailed reasoning for debugging
    """

    def __init__(self, similarity_threshold: float = 0.70, session_id: Optional[str] = None):
        """
        Initialize fuzzy matcher.

        Args:
            similarity_threshold: Minimum similarity score (0.0-1.0) for considering a match
                                 Default 0.70 (lowered from 0.75 for better Indian name matching)
            session_id: Optional session ID for trajectory logging
        """
        self.crm_store = CRMStoreV2()
        self.similarity_threshold = similarity_threshold
        self.session_id = session_id or str(uuid.uuid4())

    def find_person(self, query: str, phone_hint: Optional[str] = None,
                    context_person_id: Optional[int] = None) -> MatchResult:
        """
        Find person(s) matching the query with detailed reasoning.

        Args:
            query: Name to search for (can have spelling variations)
            phone_hint: Optional phone number to boost matching confidence
            context_person_id: Optional person ID for context (helps with pronoun resolution)

        Returns:
            MatchResult with best match, all matches, and reasoning
        """
        # Create trajectory for this matching operation
        trajectory = TrajectoryLogger.create_trajectory("FuzzyPersonMatcher", self.session_id)

        # OBSERVATION: Record what we received
        trajectory.observe(
            f"Searching for person: '{query}'",
            {
                "query": query,
                "phone_hint": phone_hint,
                "context_person_id": context_person_id,
                "threshold": self.similarity_threshold
            }
        )

        reasoning = []

        # Normalize the query
        normalized_query = self._normalize_name(query)
        normalized_phone = self._normalize_phone(phone_hint) if phone_hint else None

        trajectory.reflect(
            f"Normalized query: '{normalized_query}'",
            {"original": query, "normalized": normalized_query}
        )
        reasoning.append(f"Normalized query '{query}' to '{normalized_query}'")

        # ACTION: Get all persons from CRM
        trajectory.act("Fetching all persons from CRM database")
        all_persons = self.crm_store.get_all()

        trajectory.result(
            f"Found {len(all_persons)} persons in database",
            {"total_count": len(all_persons)}
        )
        reasoning.append(f"Searching through {len(all_persons)} persons in database")

        # REASONING: Plan the matching strategy
        if normalized_phone:
            trajectory.reason(
                "Using phone-boosted matching strategy (phone + name)",
                {"phone": normalized_phone}
            )
            reasoning.append(f"Using phone number {phone_hint} to boost matching confidence")
        else:
            trajectory.reason("Using name-only matching strategy")
            reasoning.append("Using name-only matching (no phone number provided)")

        # ACTION: Calculate similarity for each person
        trajectory.act("Calculating similarity scores for all candidates")

        candidates = []
        for person in all_persons:
            if person.is_archived:
                continue

            # Calculate name similarity
            name_similarity = self._calculate_name_similarity(normalized_query, person.full_name)

            # Check phone match
            phone_match = False
            if normalized_phone and person.phone:
                existing_phone = self._normalize_phone(person.phone)
                if self._phones_match(normalized_phone, existing_phone):
                    phone_match = True

            # Calculate combined score
            if phone_match and name_similarity >= 0.3:
                # Phone match + reasonable name = very high confidence
                combined_score = 1.5 + name_similarity  # Boost above 1.0
                match_reason = f"Phone match + name similarity ({name_similarity:.2f})"
                confidence = "very_high"
            elif name_similarity >= self.similarity_threshold:
                combined_score = name_similarity
                match_reason = f"Name similarity ({name_similarity:.2f})"
                if name_similarity >= 0.9:
                    confidence = "high"
                elif name_similarity >= 0.8:
                    confidence = "medium"
                else:
                    confidence = "low"
            else:
                # Not a candidate
                continue

            candidates.append(MatchCandidate(
                person_id=person.id,
                full_name=person.full_name,
                phone=person.phone,
                email=person.email,
                city=person.city,
                similarity_score=combined_score,
                match_reason=match_reason,
                confidence=confidence
            ))

        # Sort by similarity score descending
        candidates.sort(key=lambda x: x.similarity_score, reverse=True)

        trajectory.result(
            f"Found {len(candidates)} potential matches",
            {
                "candidate_count": len(candidates),
                "top_3": [
                    {"name": c.full_name, "score": c.similarity_score, "confidence": c.confidence}
                    for c in candidates[:3]
                ]
            }
        )
        reasoning.append(f"Found {len(candidates)} potential matches above threshold {self.similarity_threshold}")

        # REFLECTION: Analyze the results
        if not candidates:
            trajectory.reflect("No matches found - query may be completely new person")
            reasoning.append("No similar names found in database")
            trajectory.complete({"success": True, "match_count": 0, "needs_disambiguation": False})

            return MatchResult(
                success=True,
                query=query,
                best_match=None,
                all_matches=[],
                reasoning=reasoning,
                needs_disambiguation=False
            )

        best_match = candidates[0]

        if len(candidates) == 1:
            trajectory.reflect(
                f"Single clear match found: {best_match.full_name} (confidence: {best_match.confidence})",
                {"match": best_match.full_name, "score": best_match.similarity_score}
            )
            reasoning.append(f"Best match: '{best_match.full_name}' with {best_match.confidence} confidence")
            needs_disambiguation = False
        elif best_match.similarity_score > 2.0 or (best_match.confidence == "very_high"):
            trajectory.reflect(
                f"Very high confidence match: {best_match.full_name} (phone + name)",
                {"match": best_match.full_name, "score": best_match.similarity_score}
            )
            reasoning.append(f"Best match: '{best_match.full_name}' with very high confidence (phone + name match)")
            needs_disambiguation = False
        elif len(candidates) > 1 and (candidates[1].similarity_score >= 0.8):
            trajectory.reflect(
                f"Multiple strong matches found - disambiguation needed",
                {
                    "top_candidates": [
                        {"name": c.full_name, "score": c.similarity_score}
                        for c in candidates[:3]
                    ]
                }
            )
            reasoning.append(f"Multiple strong matches found:")
            for i, c in enumerate(candidates[:3], 1):
                reasoning.append(f"  {i}. {c.full_name} - {c.confidence} confidence ({c.similarity_score:.2f})")
            needs_disambiguation = True
        else:
            trajectory.reflect(
                f"Clear best match: {best_match.full_name}",
                {"match": best_match.full_name, "score": best_match.similarity_score}
            )
            reasoning.append(f"Best match: '{best_match.full_name}' with {best_match.confidence} confidence")
            needs_disambiguation = False

        trajectory.complete({
            "success": True,
            "best_match": best_match.full_name,
            "match_count": len(candidates),
            "needs_disambiguation": needs_disambiguation
        })

        return MatchResult(
            success=True,
            query=query,
            best_match=best_match,
            all_matches=candidates[:5],  # Return top 5
            reasoning=reasoning,
            needs_disambiguation=needs_disambiguation
        )

    def _normalize_name(self, name: str) -> str:
        """
        Normalize name by removing honorifics and extra whitespace.

        Handles:
        - "Srikanth Garu" → "srikanth"
        - "Mr. John Smith" → "john smith"
        - "Alka Lahoti" → "alka lahoti"
        """
        if not name:
            return ""

        # Common honorifics (Indian + Western)
        honorifics = [
            'garu', 'bhau', 'bhai', 'amma', 'anna', 'akka',
            'dada', 'tai', 'mavshi', 'kaka', 'mama',
            'mr', 'mrs', 'ms', 'dr', 'prof', 'sir', 'madam'
        ]

        # Lowercase and remove extra whitespace
        normalized = ' '.join(name.lower().strip().split())

        # Remove honorifics
        words = normalized.split()
        filtered_words = [w for w in words if w.rstrip('.') not in honorifics]

        return ' '.join(filtered_words)

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two names (0.0 - 1.0).

        Uses multi-layer matching for better Indian name handling:
        1. Exact match
        2. Full string similarity (SequenceMatcher)
        3. Token-based matching (first name + last name separately)
        4. Consonant-based phonetic matching (handles "Shikarkhane" vs "Shikarkane")
        """
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)

        if n1 == n2:
            return 1.0

        # Strategy 1: Full string similarity
        full_sim = SequenceMatcher(None, n1, n2).ratio()

        # Strategy 2: Token-based matching (first + last name)
        tokens1 = n1.split()
        tokens2 = n2.split()

        if len(tokens1) >= 2 and len(tokens2) >= 2:
            # Match first name
            first_sim = SequenceMatcher(None, tokens1[0], tokens2[0]).ratio()
            # Match last name
            last_sim = SequenceMatcher(None, tokens1[-1], tokens2[-1]).ratio()
            # Weighted average (first name 40%, last name 60%)
            token_sim = (first_sim * 0.4) + (last_sim * 0.6)
        else:
            token_sim = full_sim

        # Strategy 3: Consonant-based phonetic matching (handles "Shikarkhane" vs "Shikarkane")
        consonants1 = self._extract_consonants(n1)
        consonants2 = self._extract_consonants(n2)
        consonant_sim = SequenceMatcher(None, consonants1, consonants2).ratio()

        # Return the best score from all strategies
        return max(full_sim, token_sim, consonant_sim)

    def _extract_consonants(self, text: str) -> str:
        """
        Extract consonants for phonetic matching.

        Handles Indian names where vowels might vary but consonants stay similar.
        Example: "Shikarkhane" -> "shkrkhane", "Shikarkane" -> "shkrkane"
        """
        if not text:
            return ""
        # Remove vowels (a, e, i, o, u) but keep consonants
        vowels = set('aeiou')
        return ''.join([c for c in text.lower() if c not in vowels and c != ' '])

    def _normalize_phone(self, phone: Optional[str]) -> str:
        """Normalize phone number to digits only."""
        if not phone:
            return ""
        return re.sub(r'\D', '', phone)

    def _phones_match(self, phone1: str, phone2: str) -> bool:
        """
        Check if two phone numbers match.

        Handles:
        - Country code variations (14084445555 vs 4084445555)
        - Formatting differences
        """
        if not phone1 or not phone2:
            return False

        if phone1 == phone2:
            return True

        # Check if one is suffix of another (handles country code differences)
        if len(phone1) > 7 and len(phone2) > 7:
            # Match last 10 digits (US phone number length)
            return phone1.endswith(phone2[-10:]) or phone2.endswith(phone1[-10:])

        return False


class PronounResolver:
    """
    Resolve pronouns (he/she/they) to actual person IDs based on context.

    Uses recent context and gender matching.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.crm_store = CRMStoreV2()
        self.session_id = session_id or str(uuid.uuid4())

    def resolve(self, pronoun: str, context_person_id: Optional[int] = None,
                recent_names: Optional[List[str]] = None) -> MatchResult:
        """
        Resolve a pronoun to a person.

        Args:
            pronoun: "he", "she", "they", "him", "her"
            context_person_id: Person ID being edited/discussed (likely referent)
            recent_names: Recently mentioned names (ordered by recency)

        Returns:
            MatchResult with resolved person
        """
        trajectory = TrajectoryLogger.create_trajectory("PronounResolver", self.session_id)

        trajectory.observe(
            f"Resolving pronoun: '{pronoun}'",
            {
                "pronoun": pronoun,
                "context_person_id": context_person_id,
                "recent_names": recent_names
            }
        )

        reasoning = []
        pronoun_lower = pronoun.lower()

        # Determine expected gender from pronoun
        if pronoun_lower in ['he', 'him', 'his']:
            expected_gender = 'M'
            reasoning.append(f"Pronoun '{pronoun}' indicates male gender")
        elif pronoun_lower in ['she', 'her', 'hers']:
            expected_gender = 'F'
            reasoning.append(f"Pronoun '{pronoun}' indicates female gender")
        else:
            expected_gender = None
            reasoning.append(f"Pronoun '{pronoun}' is gender-neutral")

        trajectory.reflect(
            f"Expected gender: {expected_gender or 'neutral'}",
            {"pronoun": pronoun, "expected_gender": expected_gender}
        )

        # Strategy 1: Check context person
        if context_person_id:
            trajectory.act(f"Checking context person ID: {context_person_id}")
            person = self.crm_store.get_by_id(context_person_id)

            if person and not person.is_archived:
                if expected_gender and person.gender == expected_gender:
                    trajectory.result(
                        f"Resolved to context person: {person.full_name}",
                        {"person_id": person.id, "name": person.full_name}
                    )
                    reasoning.append(f"Resolved to context person '{person.full_name}' (gender matches)")

                    trajectory.complete({
                        "success": True,
                        "resolved_to": person.full_name,
                        "person_id": person.id
                    })

                    return MatchResult(
                        success=True,
                        query=pronoun,
                        best_match=MatchCandidate(
                            person_id=person.id,
                            full_name=person.full_name,
                            phone=person.phone,
                            email=person.email,
                            city=person.city,
                            similarity_score=2.0,  # Very high confidence
                            match_reason=f"Context person with matching gender ({expected_gender})",
                            confidence="very_high"
                        ),
                        all_matches=[],
                        reasoning=reasoning,
                        needs_disambiguation=False
                    )

        # Strategy 2: Check recently mentioned names
        if recent_names:
            trajectory.act(f"Checking {len(recent_names)} recently mentioned names")

            for name in recent_names:
                # Find this person (use 0.70 threshold for better Indian name matching)
                matcher = FuzzyPersonMatcher(similarity_threshold=0.70, session_id=self.session_id)
                match_result = matcher.find_person(name)

                if match_result.best_match:
                    person = self.crm_store.get_by_id(match_result.best_match.person_id)
                    if person and (not expected_gender or person.gender == expected_gender):
                        trajectory.result(
                            f"Resolved to recently mentioned: {person.full_name}",
                            {"person_id": person.id, "name": person.full_name}
                        )
                        reasoning.append(f"Resolved to recently mentioned '{person.full_name}' (gender matches)")

                        trajectory.complete({
                            "success": True,
                            "resolved_to": person.full_name,
                            "person_id": person.id
                        })

                        return MatchResult(
                            success=True,
                            query=pronoun,
                            best_match=match_result.best_match,
                            all_matches=[],
                            reasoning=reasoning,
                            needs_disambiguation=False
                        )

        # Failed to resolve
        trajectory.error(
            f"Could not resolve pronoun '{pronoun}' - insufficient context",
            {"pronoun": pronoun, "context_available": bool(context_person_id or recent_names)}
        )
        reasoning.append(f"Could not resolve pronoun '{pronoun}' - need more context")

        trajectory.complete({
            "success": False,
            "error": "Insufficient context to resolve pronoun"
        })

        return MatchResult(
            success=False,
            query=pronoun,
            best_match=None,
            all_matches=[],
            reasoning=reasoning,
            needs_disambiguation=False,
            error=f"Cannot resolve pronoun '{pronoun}' without more context. Please use the person's name instead."
        )
