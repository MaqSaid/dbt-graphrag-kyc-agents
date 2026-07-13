"""Sanctions Analyst Strands agent for PEP and watchlist screening.

Screens verified customer identities against international watchlists,
sanctions registers, and PEP databases with fuzzy matching.
"""

from __future__ import annotations

from typing import Any

from strands import Agent, tool

from src.domain.ports.llm_client_port import LLMClientPort
from src.domain.ports.watchlist_port import WatchlistPort
from src.domain.schemas.sanctions import SanctionsScreeningResult


# Module-level port references set by factory
_watchlist_port: WatchlistPort | None = None


@tool
def search_ofac_sdn(name: str, threshold: float = 0.85) -> dict[str, Any]:
    """Search OFAC Specially Designated Nationals list.

    Args:
        name: Entity name to search.
        threshold: Minimum similarity score for matches.

    Returns:
        Dictionary with matched entries from OFAC SDN.
    """
    import asyncio

    if _watchlist_port is None:
        return {"error": "Watchlist port not configured"}
    result = asyncio.run(_watchlist_port.search_by_name(name, threshold))
    ofac_entries = [
        e.model_dump() for e in result.entries
        if e.matched_entity.source_list == "ofac_sdn"
    ]
    return {"source": "ofac_sdn", "matches": ofac_entries, "count": len(ofac_entries)}


@tool
def search_eu_sanctions(name: str, threshold: float = 0.85) -> dict[str, Any]:
    """Search EU Consolidated Sanctions list.

    Args:
        name: Entity name to search.
        threshold: Minimum similarity score for matches.

    Returns:
        Dictionary with matched entries from EU sanctions.
    """
    import asyncio

    if _watchlist_port is None:
        return {"error": "Watchlist port not configured"}
    result = asyncio.run(_watchlist_port.search_by_name(name, threshold))
    eu_entries = [
        e.model_dump() for e in result.entries
        if e.matched_entity.source_list == "eu_sanctions"
    ]
    return {"source": "eu_sanctions", "matches": eu_entries, "count": len(eu_entries)}


@tool
def search_un_sanctions(name: str, threshold: float = 0.85) -> dict[str, Any]:
    """Search UN Security Council sanctions list.

    Args:
        name: Entity name to search.
        threshold: Minimum similarity score for matches.

    Returns:
        Dictionary with matched entries from UN sanctions.
    """
    import asyncio

    if _watchlist_port is None:
        return {"error": "Watchlist port not configured"}
    result = asyncio.run(_watchlist_port.search_by_name(name, threshold))
    un_entries = [
        e.model_dump() for e in result.entries
        if e.matched_entity.source_list == "un_sanctions"
    ]
    return {"source": "un_sanctions", "matches": un_entries, "count": len(un_entries)}


@tool
def search_pep_database(name: str, date_of_birth: str) -> dict[str, Any]:
    """Search Politically Exposed Persons database.

    Args:
        name: Entity name to search.
        date_of_birth: Date of birth in ISO format for combined matching.

    Returns:
        Dictionary with PEP matches.
    """
    import asyncio

    if _watchlist_port is None:
        return {"error": "Watchlist port not configured"}
    result = asyncio.run(_watchlist_port.search_by_date_of_birth(date_of_birth, name))
    pep_entries = [
        e.model_dump() for e in result.entries
        if e.matched_entity.source_list == "pep"
    ]
    return {"source": "pep", "matches": pep_entries, "count": len(pep_entries)}


@tool
def compute_match_similarity(
    customer_name: str,
    matched_name: str,
    customer_dob: str = "",
    matched_dob: str = "",
) -> dict[str, Any]:
    """Compute fuzzy similarity score between customer and matched entity.

    Uses character-level matching to determine if a watchlist hit is a
    true match or a false positive.

    Args:
        customer_name: The customer's full name.
        matched_name: The matched entity's name from watchlist.
        customer_dob: Customer date of birth (optional, for disambiguation).
        matched_dob: Matched entity date of birth (optional).

    Returns:
        Dictionary with similarity score and match assessment.
    """
    # Simple Jaccard-based similarity for name matching
    name_a = set(customer_name.lower().split())
    name_b = set(matched_name.lower().split())
    if not name_a or not name_b:
        return {"similarity_score": 0.0, "is_likely_match": False}

    intersection = name_a & name_b
    union = name_a | name_b
    name_similarity = len(intersection) / len(union) if union else 0.0

    # Boost score if DOB matches
    dob_match = customer_dob == matched_dob if customer_dob and matched_dob else False
    final_score = min(1.0, name_similarity + (0.2 if dob_match else 0.0))

    return {
        "similarity_score": final_score,
        "name_similarity": name_similarity,
        "dob_match": dob_match,
        "is_likely_match": final_score >= 0.85,
    }


SYSTEM_PROMPT = """You are a specialized PEP & Sanctions Analyst agent.

Your sole responsibility is to screen verified customer identity fields against
international watchlists, sanctions registers, and Politically Exposed Person databases.

Your tools allow you to:
1. Search OFAC SDN (US sanctions)
2. Search EU Consolidated Sanctions
3. Search UN Security Council sanctions
4. Search PEP databases
5. Compute similarity scores for false-positive differentiation

Workflow:
- Search the customer name against all available watchlist sources
- For any potential matches, compute similarity scores
- Differentiate true matches (similarity >= 0.85) from false positives
- If similarity is between 0.70 and 0.85, flag as ambiguous
- Return a clear assessment: screening_clear, screening_hit, or screening_ambiguous

Always provide the match score and source details for your findings.
"""


def create_sanctions_analyst_agent(
    watchlist_port: WatchlistPort,
    llm_port: LLMClientPort,
) -> Agent:
    """Factory function creating the Sanctions_Analyst Strands agent.

    Args:
        watchlist_port: Port for watchlist/sanctions queries.
        llm_port: Port for LLM interactions.

    Returns:
        Configured Strands Agent for sanctions screening.
    """
    global _watchlist_port  # noqa: PLW0603
    _watchlist_port = watchlist_port

    return Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[
            search_ofac_sdn,
            search_eu_sanctions,
            search_un_sanctions,
            search_pep_database,
            compute_match_similarity,
        ],
        max_iterations=10,
    )
