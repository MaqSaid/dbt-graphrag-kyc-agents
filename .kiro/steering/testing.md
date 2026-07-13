# Testing Strategy

## Multi-Tiered Test Architecture
```
tests/
├── unit/          # Mocked adapters, isolated domain logic
├── integration/   # Real DuckDB + Neo4j Docker
├── architecture/  # pytest-archon boundary enforcement
├── quality/       # ruff + mypy subprocess assertions
├── security/      # Adversarial input injection tests
├── retrieval/     # Graph_Analyst correctness
├── property/      # Hypothesis-based invariant testing
└── e2e/           # Full pipeline CSV→dbt→Neo4j→agents→report
```

## Property-Based Testing (Hypothesis)
- CI: minimum 100 examples per property test
- Nightly: 1000 examples per property test
- Always enable shrinking for minimal counterexamples

### Key Properties to Validate
1. Pydantic round-trip: model_validate_json(m.model_dump_json()) == m
2. Composite score bounded: always in [0.0, 1.0]
3. Decision determinism: same inputs → same decision
4. Graph path invariant: all paths ≤ 2 hops
5. ELT idempotence: same input → same output
6. Injection rejection: all known patterns rejected
7. Audit hash chain: ordered, verifiable, tamper-evident

## Coverage Requirements
- Unit + Integration combined: ≥ 80%
- Architecture tests: run on every PR
- Security tests: run on every PR

## Test Data
- Use synthetic data generator in src/domain/testing/
- Three scenarios: clean_customer, watchlisted_entity, fraud_ring_member
- Minimum 100 records per scenario for property testing
