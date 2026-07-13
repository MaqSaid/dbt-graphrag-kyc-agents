"""Security middleware for prompt injection detection and input sanitization.

Provides preprocessing security layer that scans API payloads for known
prompt injection patterns, validates Cypher queries, and sanitizes inputs.
"""

from __future__ import annotations

import re

from src.domain.exceptions import SecurityViolationError

# Known prompt injection patterns
INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(previous|all)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"###\s*instruction", re.IGNORECASE),
    re.compile(r"<\|system\|>", re.IGNORECASE),
    re.compile(r"<\|assistant\|>", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all|your)", re.IGNORECASE),
    re.compile(r"override\s+(your|all|previous)", re.IGNORECASE),
]

# Permitted Cypher query patterns (read-only)
CYPHER_WHITELIST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^MATCH\s+\(.+\)\s*-\[.+\]->\s*\(.+\)\s+WHERE.+RETURN", re.IGNORECASE),
    re.compile(r"^MATCH\s+\(.+\)\s+WHERE.+RETURN", re.IGNORECASE),
    re.compile(r"^MATCH\s+path\s*=\s*\(.+\)-\[.+\*\.\.2\].+RETURN", re.IGNORECASE),
]

# Blocked Cypher operations
CYPHER_BLOCKED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(CREATE|MERGE|SET|DELETE|REMOVE|DROP|DETACH)\b", re.IGNORECASE),
]


def detect_prompt_injection(payload: str) -> bool:
    """Check if a payload contains known prompt injection patterns.

    Args:
        payload: The input text to scan.

    Returns:
        True if any injection pattern is detected.
    """
    for pattern in INJECTION_PATTERNS:
        if pattern.search(payload):
            return True
    return False


def validate_cypher_query(query: str) -> bool:
    """Validate a Cypher query against the whitelist of permitted patterns.

    Args:
        query: The Cypher query string to validate.

    Returns:
        True if the query matches a permitted pattern and contains no blocked ops.
    """
    # Check for blocked operations first
    for blocked in CYPHER_BLOCKED_PATTERNS:
        if blocked.search(query):
            return False

    # Check against whitelist
    return any(pattern.match(query.strip()) for pattern in CYPHER_WHITELIST_PATTERNS)


def sanitize_input(text: str) -> str:
    """Remove control characters, null bytes, and dangerous Unicode.

    Args:
        text: The input text to sanitize.

    Returns:
        Sanitized text with dangerous characters removed.
    """
    # Remove null bytes
    text = text.replace("\x00", "")
    # Remove control characters (except newline, tab, carriage return)
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Remove Unicode direction override characters
    text = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text)
    return text


def scan_payload(payload: str) -> None:
    """Scan a payload for security violations, raising on detection.

    Args:
        payload: The input payload text to scan.

    Raises:
        SecurityViolationError: If a prompt injection pattern is detected.
    """
    sanitized = sanitize_input(payload)
    if detect_prompt_injection(sanitized):
        raise SecurityViolationError(
            message="Prompt injection pattern detected in input payload",
            violation_type="prompt_injection",
        )
