# Architecture Rules: Hexagonal + DDD

## Directory Layout
```
src/
├── domain/          # Pure business logic (NO infrastructure imports)
│   ├── ports/       # Abstract interfaces (Python ABCs)
│   ├── schemas/     # Pydantic v2 models (data contracts)
│   ├── identity/    # Identity verification bounded context
│   ├── sanctions/   # Sanctions screening bounded context
│   ├── graph_analysis/  # Graph analysis bounded context
│   ├── reporting/   # Compliance reporting bounded context
│   ├── orchestration/   # Decision engine bounded context
│   └── exceptions.py    # Domain exception hierarchy
├── infrastructure/  # External system implementations
│   ├── adapters/    # Port implementations (Neo4j, Bedrock, etc.)
│   ├── resilience/  # Circuit breaker, retry logic
│   └── observability/   # Logging, metrics
├── application/     # Orchestration wiring
│   ├── orchestrator.py  # LangGraph state machine
│   └── container.py     # Dependency injection
├── api/             # HTTP boundary
│   ├── routes/      # FastAPI endpoints
│   └── middleware/  # Security, auth, rate limiting
└── agents/          # Strands agent definitions
```

## Import Rules (ENFORCED BY TESTS)
1. `src/domain/` → may import: stdlib, pydantic ONLY
2. `src/domain/` → must NOT import: src/infrastructure, src/api, src/agents
3. `src/agents/` → may import: src/domain (ports, schemas)
4. `src/agents/` → must NOT import: src/infrastructure, src/api
5. `src/infrastructure/` → may import: src/domain (ports, schemas, exceptions)
6. `src/api/` → may import: src/domain, src/application

## Naming Conventions
- Ports: suffixed with `Port` (e.g., `GraphDatabasePort`)
- Adapters: suffixed with `Adapter` (e.g., `Neo4jAdapter`)
- Agents: suffixed with `Agent` or use `create_*_agent` factory
- Schemas: descriptive names matching domain concepts

## SOLID Principles
- **Single Responsibility**: One bounded context per agent
- **Open/Closed**: New agents added without modifying orchestrator core
- **Liskov Substitution**: All adapters interchangeable via port interfaces
- **Interface Segregation**: Each port has ≤ 5 methods
- **Dependency Inversion**: Domain depends only on abstractions (ports)
