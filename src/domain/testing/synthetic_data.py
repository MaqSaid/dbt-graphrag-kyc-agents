"""Synthetic data generation for testing KYC pipeline scenarios.

Generates realistic customer onboarding records for three scenarios:
- clean_customer: No flags, passes all checks
- watchlisted_entity: Matches sanctions/PEP databases
- fraud_ring_member: Shares infrastructure with flagged entities
"""

from __future__ import annotations

import random
import string
from datetime import date, timedelta

from src.domain.schemas.identity import CustomerOnboardingPayload


def _random_name() -> str:
    """Generate a random full name."""
    first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"


def _random_date(start_year: int = 1950, end_year: int = 2000) -> date:
    """Generate a random date of birth."""
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _random_national_id() -> str:
    """Generate a random national ID."""
    return "SSN" + "".join(random.choices(string.digits, k=9))


def _random_address() -> str:
    """Generate a random US address."""
    number = random.randint(100, 9999)
    streets = ["Main St", "Oak Ave", "Pine Rd", "Maple Dr", "Cedar Ln", "Elm Blvd", "Park Way", "Lake Dr"]
    cities = ["New York NY", "Chicago IL", "Los Angeles CA", "Houston TX", "Phoenix AZ", "Boston MA"]
    return f"{number} {random.choice(streets)} {random.choice(cities)} {random.randint(10001, 99999)}"


def _random_email(name: str) -> str:
    """Generate a random email based on name."""
    domains = ["email.com", "mail.org", "inbox.net", "post.com"]
    clean_name = name.lower().replace(" ", ".")
    return f"{clean_name}{random.randint(1, 99)}@{random.choice(domains)}"


def _random_phone() -> str:
    """Generate a random E.164 phone number."""
    return f"+1{random.randint(2000000000, 9999999999)}"


def _random_ip() -> str:
    """Generate a random IPv4 address."""
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


# Shared infrastructure for fraud ring scenarios
FRAUD_RING_ADDRESS = "666 Shadow Lane Suite 13 Darkville NJ 07001"
FRAUD_RING_IP = "203.0.113.42"
FRAUD_RING_PHONE = "+19175551666"


def generate_clean_customer(seed: int | None = None) -> CustomerOnboardingPayload:
    """Generate a clean customer with no risk indicators.

    Args:
        seed: Optional random seed for reproducibility.

    Returns:
        Valid CustomerOnboardingPayload for a clean customer.
    """
    if seed is not None:
        random.seed(seed)
    name = _random_name()
    return CustomerOnboardingPayload(
        full_name=name,
        date_of_birth=_random_date(),
        national_id=_random_national_id(),
        address=_random_address(),
        email=_random_email(name),
        phone=_random_phone(),
        ip_address=_random_ip(),
    )


def generate_watchlisted_entity(seed: int | None = None) -> CustomerOnboardingPayload:
    """Generate a customer that matches sanctions/PEP databases.

    Uses names that would trigger fuzzy matching against known watchlists.

    Args:
        seed: Optional random seed for reproducibility.

    Returns:
        Valid CustomerOnboardingPayload for a watchlisted entity.
    """
    if seed is not None:
        random.seed(seed)
    # Names that resemble known sanctioned entities
    sanctioned_names = [
        "Viktor Petrov",
        "Hassan Al-Rashid",
        "Kim Jong-Sik",
        "Sergei Ivanov",
        "Mohammed Al-Qaeda",
    ]
    name = random.choice(sanctioned_names)
    return CustomerOnboardingPayload(
        full_name=name,
        date_of_birth=_random_date(1960, 1990),
        national_id=_random_national_id(),
        address=_random_address(),
        email=_random_email(name),
        phone=_random_phone(),
        ip_address=_random_ip(),
    )


def generate_fraud_ring_member(seed: int | None = None) -> CustomerOnboardingPayload:
    """Generate a customer sharing infrastructure with flagged entities.

    Uses shared address, IP, or phone that links to existing flagged entities
    in the graph database.

    Args:
        seed: Optional random seed for reproducibility.

    Returns:
        Valid CustomerOnboardingPayload with fraud ring connections.
    """
    if seed is not None:
        random.seed(seed)
    name = _random_name()
    # Randomly share 1-3 infrastructure elements
    shared = random.sample(["address", "ip", "phone"], k=random.randint(1, 3))

    address = FRAUD_RING_ADDRESS if "address" in shared else _random_address()
    ip = FRAUD_RING_IP if "ip" in shared else _random_ip()
    phone = FRAUD_RING_PHONE if "phone" in shared else _random_phone()

    return CustomerOnboardingPayload(
        full_name=name,
        date_of_birth=_random_date(),
        national_id=_random_national_id(),
        address=address,
        email=_random_email(name),
        phone=phone,
        ip_address=ip,
    )


def generate_batch(
    scenario: str,
    count: int = 100,
    start_seed: int = 0,
) -> list[CustomerOnboardingPayload]:
    """Generate a batch of synthetic records for a given scenario.

    Args:
        scenario: One of 'clean_customer', 'watchlisted_entity', 'fraud_ring_member'.
        count: Number of records to generate (default 100).
        start_seed: Starting seed for reproducibility.

    Returns:
        List of valid CustomerOnboardingPayload instances.

    Raises:
        ValueError: If scenario is not recognized.
    """
    generators = {
        "clean_customer": generate_clean_customer,
        "watchlisted_entity": generate_watchlisted_entity,
        "fraud_ring_member": generate_fraud_ring_member,
    }
    if scenario not in generators:
        msg = f"Unknown scenario: {scenario}. Must be one of {list(generators.keys())}"
        raise ValueError(msg)

    generator = generators[scenario]
    return [generator(seed=start_seed + i) for i in range(count)]
