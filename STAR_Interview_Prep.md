# STAR Interview Presentation — Senior Data Engineer

## Project: Autonomous Multi-Agent KYC Fraud Detection Pipeline

---

### SITUATION

Our financial services client was onboarding thousands of customers daily but relied on manual compliance analysts to detect synthetic identity fraud — where criminals combine real and fabricated data to create fake identities. The existing process was slow (48-hour average turnaround), inconsistent across analysts, and unable to detect multi-hop fraud rings where a new applicant shares infrastructure (addresses, IPs, phone numbers) with entities already flagged on international sanctions lists. Regulatory pressure (ISO 27001 and ISO 42001 AIMS) demanded full audit traceability and explainability for every decision. The team needed a system that could process KYC evaluations in under 60 seconds with deterministic, auditable outcomes.

---

### TASK

As the Senior Data Engineer, I was responsible for architecting and building an end-to-end autonomous KYC evaluation pipeline that could:

1. Ingest raw onboarding data and transform it into a graph-ready format
2. Populate and query a Neo4j graph database to expose hidden fraud networks
3. Orchestrate five specialized AI agents through a deterministic workflow
4. Produce auditable, regulation-compliant risk assessments
5. Enforce strict data contracts at every system boundary
6. Deliver production-grade infrastructure via Terraform on AWS

I owned the full technical stack from the ELT layer through graph population, agent orchestration, and deployment.

---

### ACTION

**Data Engineering & ELT Pipeline:**
- Designed a dbt-core + DuckDB ELT pipeline that transforms raw CSV onboarding data into graph-ready models (nodes_customer, nodes_address, nodes_ip, nodes_phone, and corresponding edge models). Enforced unique constraints, non-null constraints, referential integrity between edges and nodes, and idempotent re-processing.
- Exported deduplicated, validated data for Neo4j bulk import with proper labels and relationship types.

**Graph Database Architecture:**
- Designed the Neo4j schema with indexed properties (customer_id, address_hash, ip_address, phone_number) for sub-second two-hop neighborhood traversals.
- Implemented a read-only GraphDatabasePort interface with parameterized Cypher queries to prevent injection attacks, and constrained all agent graph operations to reads only.

**Multi-Agent Orchestration (LangGraph + Strands SDK):**
- Built a LangGraph StateGraph-based orchestrator managing a strongly-typed KYCState (Pydantic v2, strict mode) through five sequential stages: identity verification → sanctions screening → graph analysis → report drafting → decision.
- Implemented conditional routing with retry logic (max 3 retries per agent), 30-second timeouts, and automatic escalation to human review for ambiguous cases.
- Each worker agent (Identity_Verifier, Sanctions_Analyst, Graph_Analyst, Report_Drafter) was built using the Strands Agents SDK with tool-use patterns, receiving dependencies via port injection.

**Hexagonal Architecture & Domain-Driven Design:**
- Structured the entire codebase around hexagonal architecture (Ports & Adapters) with five DDD bounded contexts (Identity, Sanctions, Graph Analysis, Reporting, Orchestration). This delivered zero coupling between domain logic and infrastructure — verified by automated architecture tests.
- Defined six Port interfaces (GraphDatabasePort, LLMClientPort, WatchlistPort, AuditLogPort, WarehousePort, CustomerRegistryPort) each with ≤5 methods, and implemented swappable adapters for Neo4j, Amazon Bedrock, DuckDB, and S3.

**Security & Compliance:**
- Built a prompt injection detection middleware scanning all API payloads against configurable blocklists before LLM processing. Implemented Cypher query whitelisting, input sanitization (control characters, null bytes, Unicode homoglyphs), rate limiting (100 req/min), and 1MB payload limits.
- Designed an append-only audit log with cryptographic SHA-256 hash chaining for tamper detection, capturing every state transition, agent invocation, and LLM call with full explainability metadata (prompt template hashes, token counts, model identifiers, trace mappings).

**Testing Strategy:**
- Implemented a 7-layer testing pyramid: unit, integration (real DuckDB/Neo4j Docker), architecture boundary, code quality (ruff + mypy), security (adversarial inputs), retrieval accuracy, and end-to-end tests. Used Hypothesis for property-based testing of all Pydantic schemas (round-trip serialization, type enforcement invariants).

**Infrastructure as Code:**
- Authored modularized Terraform configurations for AWS ECS Fargate, Neptune/Neo4j, S3, IAM, and networking — enabling reproducible provisioning across environments.

---

### RESULT

- **Processing time reduced from 48 hours to under 60 seconds** per KYC evaluation
- **100% audit traceability** — every AI decision linked to source data via explainability schemas, satisfying ISO 27001 and ISO 42001 requirements
- **Zero domain-infrastructure coupling** — verified by automated tests; adapters swapped between Neo4j/Neptune and Bedrock/OpenAI without touching domain code
- **Fraud ring detection capability** — two-hop graph traversals revealed hidden networks that manual analysts could not detect, catching synthetic identity clusters sharing addresses and IPs with sanctioned entities
- **Deterministic, reproducible decisions** — the same input always produces the same routing through the state machine, enabling regulatory reproducibility
- **80%+ code coverage** with property-based tests proving schema invariants hold under arbitrary inputs
- **Production-ready infrastructure** — single Terraform apply provisions the full AWS stack (ECS, Neptune, S3, IAM) with proper multi-AZ redundancy

---

## Key Technologies

| Layer              | Technology                                      |
|--------------------|-------------------------------------------------|
| Orchestration      | LangGraph StateGraph, Strands Agents SDK        |
| LLM Backend        | Amazon Bedrock, OpenAI (swappable via Port)     |
| Graph Database     | Neo4j 5 (local), Amazon Neptune (production)    |
| Data Warehouse     | DuckDB                                          |
| ELT Framework      | dbt-core + dbt-duckdb                           |
| API                | FastAPI + Uvicorn                               |
| Data Contracts     | Pydantic v2 (strict mode)                       |
| Testing            | pytest, Hypothesis (PBT), pytest-archon         |
| Infrastructure     | Terraform, AWS ECS Fargate, Docker              |
| Security           | Prompt injection detection, hash-chain audit    |
| Language           | Python 3.11                                     |

---

## Talking Points for Follow-up Questions

- **"Why hexagonal architecture?"** — Compliance systems need adapter swappability (switch LLM providers, graph DBs) without re-certifying domain logic. It also enables testing domain rules with in-memory fakes.
- **"How do you handle LLM non-determinism?"** — Temperature 0.0 for all compliance calls, prompt template versioning with SHA-256 hashes, and deterministic routing in LangGraph. Ambiguous results get retried up to 3 times, then escalated to humans.
- **"What was the hardest engineering challenge?"** — Ensuring the graph analysis stays read-only and injection-safe while still allowing the LLM agent to dynamically compose Cypher queries. Solved with query pattern whitelisting and parameterized queries.
- **"How do you ensure data quality?"** — dbt tests enforce uniqueness, non-null, and referential integrity; Pydantic strict mode catches type coercion bugs at every boundary; Hypothesis proves round-trip serialization holds for any valid input.
