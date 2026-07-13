# Implementation Plan: Hexagonal-GraphRAG-KYC-Pipeline

## Overview

This plan implements the autonomous multi-agent KYC evaluation pipeline following hexagonal architecture with DDD bounded contexts. Implementation proceeds from foundational project structure through domain schemas, ports, adapters, agents, orchestrator, API, ELT pipeline, testing, infrastructure, and developer experience layers — each task building incrementally on preceding work.

## Tasks

- [x] 1. Project scaffolding and configuration
  - [x] 1.1 Create pyproject.toml with all dependencies and tool configurations
    - Define project metadata, Python 3.11+ requirement
    - Add dependencies: pydantic, pydantic-settings, fastapi, uvicorn, langgraph, strands-agents, neo4j, duckdb, dbt-core, dbt-duckdb, structlog, prometheus-client, python-jose, httpx
    - Add dev dependencies: pytest, pytest-cov, pytest-asyncio, hypothesis, pytest-archon, ruff, mypy, docker
    - Configure Ruff with strict rule set (PEP 8, import ordering, type annotations, docstrings)
    - Configure Mypy in strict mode disallowing Any in public interfaces
    - _Requirements: 19.1, 19.2, 26.10_

  - [x] 1.2 Create directory structure matching hexagonal architecture
    - Create src/domain/ports/, src/domain/schemas/, src/domain/identity/, src/domain/sanctions/, src/domain/graph_analysis/, src/domain/reporting/, src/domain/orchestration/
    - Create src/infrastructure/adapters/, src/infrastructure/resilience/, src/infrastructure/observability/
    - Create src/application/, src/api/routes/, src/api/middleware/
    - Create src/agents/
    - Create dbt_kyc/models/staging/, dbt_kyc/models/marts/, dbt_kyc/seeds/
    - Create terraform/modules/networking/, terraform/modules/ecs/, terraform/modules/neptune/, terraform/modules/s3/, terraform/modules/iam/
    - Create tests/unit/, tests/integration/, tests/architecture/, tests/quality/, tests/security/, tests/retrieval/, tests/e2e/, tests/property/
    - Add __init__.py files to all Python packages
    - _Requirements: 26.1, 26.2, 26.3, 26.4, 26.5, 26.6, 26.7, 26.8, 26.9_

  - [x] 1.3 Create Docker Compose for local development
    - Create docker-compose.yml with Neo4j 5-community service (ports 7687, 7474)
    - Create docker-compose.test.yml for CI test infrastructure
    - Create Dockerfile with multi-stage build (base, production, test)
    - Configure Neo4j with APOC plugin enabled
    - _Requirements: 19.3, 29.4_

  - [x] 1.4 Create Makefile with common development commands
    - Add targets: lint, format, typecheck, test, test-unit, test-integration, test-property, test-architecture, test-security, test-e2e, build, run, docker-up, docker-down
    - _Requirements: 19.4_

- [ ] 2. Domain layer — Pydantic schemas and value objects
  - [-] 2.1 Implement core Pydantic schemas (identity, sanctions, graph_analysis)
    - Create src/domain/schemas/identity.py with CustomerOnboardingPayload, FieldValidation, RegistryCheck, IdentityVerificationResult (strict=True, custom validators for email RFC 5322, phone E.164, IP address)
    - Create src/domain/schemas/sanctions.py with WatchlistEntry, WatchlistMatch, WatchlistSearchResult, SanctionsScreeningResult (strict=True)
    - Create src/domain/schemas/graph_analysis.py with GraphNode, GraphEdge, FraudPath (path_length ≤ 2), GraphAnalysisResult (strict=True)
    - _Requirements: 14.1, 14.2, 14.3, 3.1, 3.7, 4.4, 5.7_

  - [-] 2.2 Implement reporting, audit, and config schemas
    - Create src/domain/schemas/reporting.py with ExplainabilitySchema, ReportSection, ComplianceReport (strict=True)
    - Create src/domain/schemas/audit.py with AuditLogEntry (strict=True, hash chain fields)
    - Create src/domain/schemas/config.py with DecisionConfig (weights, thresholds) and AppConfig (pydantic-settings, env prefix KYC_)
    - _Requirements: 6.5, 6.6, 12.2, 12.3, 13.1, 13.2, 18.2, 27.1_

  - [-] 2.3 Implement KYCState aggregate root and API schemas
    - Create src/domain/schemas/kyc_state.py with Decision enum (PENDING, APPROVE, DENY, ESCALATE_TO_HUMAN_REVIEW), StateTransition, KYCState (strict=True, retry counters, state_history, terminal decision validator)
    - Create src/domain/schemas/api.py with CustomerOnboardingRequest, EvaluationAcceptedResponse, EvaluationStatusResponse, ComplianceReportResponse, ErrorResponse
    - _Requirements: 2.1, 2.2, 2.5, 2.7, 10.1, 10.2, 10.3_

  - [ ]* 2.4 Write property tests for Pydantic model round-trip serialization
    - **Property 1: Pydantic Model Serialization Round-Trip**
    - Create tests/property/strategies.py with Hypothesis strategies for all schema types
    - Create tests/property/test_pydantic_roundtrip.py testing model_validate_json(instance.model_dump_json()) == instance for all models
    - **Validates: Requirements 2.6, 6.9, 14.7**

  - [ ]* 2.5 Write property tests for strict type enforcement
    - **Property 11: Strict Type Enforcement**
    - Create tests/property/test_type_enforcement.py verifying incorrect types raise ValidationError for all strict models
    - **Validates: Requirements 2.4, 14.8**

- [x] 3. Domain layer — Port interfaces and exceptions
  - [x] 3.1 Implement all Port interfaces as abstract base classes
    - Create src/domain/ports/graph_database_port.py with GraphDatabasePort ABC (neighbor_query, path_extraction, node_lookup, health_check) — max 4 methods
    - Create src/domain/ports/llm_client_port.py with LLMClientPort ABC (generate_text, generate_structured, get_embeddings) — max 3 methods
    - Create src/domain/ports/watchlist_port.py with WatchlistPort ABC (search_by_name, search_by_national_id, search_by_date_of_birth) — max 3 methods
    - Create src/domain/ports/audit_log_port.py with AuditLogPort ABC (log_event, query_by_evaluation_id, query_by_time_range) — max 3 methods
    - Create src/domain/ports/warehouse_port.py with WarehousePort ABC (load_raw_data, execute_query, export_to_csv) — max 3 methods
    - Create src/domain/ports/customer_registry_port.py with CustomerRegistryPort ABC (verify_identity) — max 1 method
    - Ensure ≤ 5 methods per port interface
    - _Requirements: 7.1, 7.5, 7.8, 9.4, 12.6, 17.1, 24.1_

  - [x] 3.2 Implement domain exception hierarchy
    - Create src/domain/exceptions.py with KYCEvaluationError (base), AgentTimeoutError, GraphConnectionError, LLMConnectionError, SecurityViolationError, ValidationError
    - Include evaluation_id context in all exceptions
    - _Requirements: 20.2_

- [x] 4. Domain layer — Bounded context services
  - [x] 4.1 Implement decision engine and orchestration domain logic
    - Create src/domain/orchestration/decision_engine.py with compute_composite_risk_score (weighted sum, clamped [0,1]), evaluate_decision (threshold-based routing), has_critical_flag
    - Implement decision rules: critical_flag → DENY, below approval_threshold → APPROVE, above denial_threshold → DENY, otherwise → ESCALATE
    - _Requirements: 27.1, 27.2, 27.3, 27.4, 27.5, 27.6_

  - [ ]* 4.2 Write property tests for decision engine
    - **Property 2: Composite Risk Score Range Invariant**
    - **Property 3: Decision Determinism**
    - Create tests/property/test_decision_properties.py testing score bounded [0,1] for all valid inputs and decision determinism
    - **Validates: Requirements 27.7, 27.8**

  - [x] 4.3 Implement bounded context service stubs
    - Create src/domain/identity/identity_service.py with IdentityVerificationService (validate fields, compute confidence)
    - Create src/domain/sanctions/sanctions_service.py with SanctionsScreeningService (fuzzy matching logic, threshold classification)
    - Create src/domain/graph_analysis/graph_service.py with GraphAnalysisService (path filtering, risk score computation)
    - Create src/domain/reporting/report_service.py with ComplianceReportService (section assembly, trace mapping)
    - All services accept ports via constructor injection
    - _Requirements: 3.2, 3.6, 4.3, 5.4, 6.1, 7.3, 18.6_

- [x] 5. Checkpoint — Domain layer validation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Infrastructure layer — Resilience patterns
  - [x] 6.1 Implement circuit breaker and retry logic
    - Create src/infrastructure/resilience/circuit_breaker.py with CircuitBreaker class (CLOSED/OPEN/HALF_OPEN states, configurable failure_threshold=5, recovery_timeout=60s)
    - Create src/infrastructure/resilience/retry.py with exponential backoff decorator (base 2s, max 3 retries)
    - _Requirements: 20.3, 20.4, 20.5, 20.6_

  - [x] 6.2 Implement observability infrastructure
    - Create src/infrastructure/observability/logging.py with structlog configuration (JSON renderer, correlation_id, evaluation_id, agent_name, timestamp, log_level, event_type)
    - Create src/infrastructure/observability/metrics.py with Prometheus metrics (evaluation_count, evaluation_duration, agent_invocation_duration, external_call_latency, error_count, active_evaluations)
    - _Requirements: 30.1, 30.2, 30.3, 30.4_

- [x] 7. Infrastructure layer — Adapters
  - [x] 7.1 Implement Neo4j adapter
    - Create src/infrastructure/adapters/neo4j_adapter.py implementing GraphDatabasePort
    - Implement neighbor_query with parameterized Cypher (hop_depth parameter), path_extraction, node_lookup, health_check
    - Integrate circuit breaker for connection failures raising GraphConnectionError
    - Ensure all queries use $param syntax (no string interpolation)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 5.2_

  - [x] 7.2 Implement LLM adapters (Bedrock and OpenAI)
    - Create src/infrastructure/adapters/bedrock_adapter.py implementing LLMClientPort (generate_text, generate_structured, get_embeddings via AWS SDK)
    - Create src/infrastructure/adapters/openai_adapter.py implementing LLMClientPort (OpenAI-compatible API)
    - Capture token usage metadata (LLMInvocationMetadata) on every call
    - Implement rate limit retry with exponential backoff, raise LLMConnectionError after exhaustion
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7_

  - [x] 7.3 Implement watchlist, audit log, warehouse, and registry adapters
    - Create src/infrastructure/adapters/watchlist_api_adapter.py implementing WatchlistPort (multi-source query, normalization to WatchlistEntry)
    - Create src/infrastructure/adapters/s3_audit_log_adapter.py implementing AuditLogPort (append-only with SHA-256 hash chain, verify_chain method)
    - Create src/infrastructure/adapters/duckdb_adapter.py implementing WarehousePort (load_raw_data, execute_query, export_to_csv)
    - Create src/infrastructure/adapters/registry_adapter.py implementing CustomerRegistryPort (simulated registry verification)
    - _Requirements: 12.1, 12.4, 12.7, 12.8, 24.2, 24.3, 8.1_

  - [ ]* 7.4 Write property tests for audit log hash chain integrity
    - **Property 15: Audit Log Hash Chain Integrity**
    - Create tests/property/test_audit_chain.py verifying hash chain ordering, previous_hash linkage, and SHA-256 integrity for any sequence of entries
    - **Validates: Requirements 12.8, 12.4**

- [ ] 8. Agent layer — Strands agents with tools
  - [-] 8.1 Implement Identity_Verifier agent
    - Create src/agents/identity_verifier_agent.py with @tool functions: validate_email_format, validate_phone_e164, validate_national_id, check_government_registry, compute_confidence_score
    - Implement create_identity_verifier_agent factory accepting registry_port and llm_port via constructor injection
    - Configure max_iterations=10, timeout=10s
    - _Requirements: 21.1, 21.2, 21.3, 21.6, 3.1, 3.2, 3.3, 3.6, 3.8_

  - [-] 8.2 Implement Sanctions_Analyst agent
    - Create src/agents/sanctions_analyst_agent.py with @tool functions: search_ofac_sdn, search_eu_sanctions, search_un_sanctions, search_pep_database, compute_match_similarity
    - Implement create_sanctions_analyst_agent factory accepting watchlist_port and llm_port
    - Configure fuzzy matching with configurable threshold (default 0.85), ambiguity boundary (0.70)
    - Configure max_iterations=10, timeout=15s
    - _Requirements: 21.1, 21.3, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8_

  - [-] 8.3 Implement Graph_Analyst agent
    - Create src/agents/graph_analyst_agent.py with @tool functions: query_address_neighborhood, query_ip_neighborhood, query_phone_neighborhood, extract_fraud_paths, compute_network_risk_score
    - Implement create_graph_analyst_agent factory accepting graph_db_port and llm_port
    - Enforce read-only operations (no write tools), hop_depth=2, relevance filter for >100 entities
    - Configure max_iterations=10, timeout=20s
    - _Requirements: 21.1, 21.3, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.8_

  - [-] 8.4 Implement Report_Drafter agent
    - Create src/agents/report_drafter_agent.py with @tool functions: draft_executive_summary, draft_risk_assessment, format_compliance_report, generate_trace_mapping
    - Implement create_report_drafter_agent factory accepting llm_port
    - Generate ExplainabilitySchema metadata for every LLM-generated section
    - Configure max_iterations=10, timeout=30s
    - _Requirements: 21.1, 21.3, 6.1, 6.2, 6.3, 6.4, 6.6, 6.7, 6.8, 13.3, 13.4, 13.5_

  - [ ]* 8.5 Write unit tests for agent tool functions
    - Create tests/unit/test_identity_validation.py testing email, phone, national_id validators
    - Create tests/unit/test_sanctions_matching.py testing fuzzy matching threshold logic
    - Test tool scope enforcement (agent cannot call tools outside its permitted set)
    - _Requirements: 21.4, 21.5, 3.2, 4.3_

- [ ] 9. Application layer — LangGraph orchestrator
  - [~] 9.1 Implement LangGraph StateGraph orchestrator
    - Create src/application/orchestrator.py with build_kyc_graph() factory
    - Define nodes: initialize, verify_identity, screen_sanctions, analyze_graph, draft_report, evaluate_decision, finalize
    - Define conditional edges: route_after_identity_verification (proceed/retry/escalate), route_after_sanctions_screening (proceed/retry/escalate), route_after_decision (finalize)
    - Implement retry logic (max 3 retries per agent), timeout handling (30s), state history recording
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 22.1, 22.2, 22.5, 22.6_

  - [~] 9.2 Implement dependency injection container
    - Create src/application/container.py with Container dataclass (frozen=True) holding all port instances
    - Implement build_container(config: AppConfig) factory that instantiates adapters based on configuration
    - Support adapter swapping via config (Neo4jAdapter vs InMemoryGraphAdapter)
    - Validate all required config values at startup, fail fast on missing values
    - _Requirements: 18.1, 18.3, 18.4, 18.5, 18.6_

  - [ ]* 9.3 Write property test for orchestrator termination
    - **Property 12: Orchestrator Termination**
    - Create tests/property/test_orchestrator_termination.py verifying StateGraph terminates in finite steps for all valid KYCState inputs
    - Bounded by (number_of_nodes × max_retry_count + 1) max visits
    - **Validates: Requirements 22.8, 1.7**

- [~] 10. Checkpoint — Core pipeline validation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. API layer — FastAPI application
  - [~] 11.1 Implement FastAPI application and routes
    - Create src/api/main.py with FastAPI app, lifespan handler (build container on startup), CORS, and metrics endpoint (/metrics)
    - Create src/api/routes/kyc.py with POST /api/v1/kyc/evaluate (202 Accepted), GET /api/v1/kyc/status/{evaluation_id}, GET /api/v1/kyc/report/{evaluation_id}, GET /api/v1/health
    - Create src/api/dependencies.py for FastAPI dependency injection wiring
    - Include X-Correlation-ID header propagation in all responses
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 25.7_

  - [~] 11.2 Implement security middleware
    - Create src/api/middleware/security.py with detect_prompt_injection (regex pattern blocklist), validate_cypher_query (whitelist patterns), sanitize_input (control chars, null bytes, Unicode homoglyphs)
    - Create src/api/middleware/auth.py with JWT bearer token validation, RBAC roles (kyc_analyst, kyc_admin, system_admin)
    - Create src/api/middleware/rate_limit.py with 100 req/min per client, 1MB max payload size
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 34.1, 34.2, 34.8_

  - [ ]* 11.3 Write property tests for prompt injection detection
    - **Property 9: Prompt Injection Rejection**
    - Create tests/property/test_security_properties.py verifying all known injection patterns are detected regardless of surrounding text
    - **Validates: Requirements 11.10**

  - [ ]* 11.4 Write property test for authentication invariant
    - **Property 10: Authentication Invariant**
    - Create tests verifying all requests without valid JWT return 401 without body processing
    - **Validates: Requirements 34.12**

- [ ] 12. ELT pipeline — dbt models and DuckDB
  - [~] 12.1 Create dbt project structure and configuration
    - Create dbt_kyc/dbt_project.yml with project name, model paths, seed paths
    - Create dbt_kyc/profiles.yml with DuckDB connection (local file path)
    - Create dbt_kyc/seeds/raw_customers.csv with sample synthetic onboarding records
    - _Requirements: 8.1, 26.7_

  - [~] 12.2 Implement dbt staging and mart models
    - Create dbt_kyc/models/staging/stg_customers.sql (clean, deduplicate, compute address_hash via md5)
    - Create dbt_kyc/models/staging/schema.yml with source definition
    - Create dbt_kyc/models/marts/nodes_customer.sql, nodes_address.sql, nodes_ip.sql, nodes_phone.sql
    - Create dbt_kyc/models/marts/edges_shares_address.sql, edges_shares_ip.sql, edges_shares_phone.sql
    - Create dbt_kyc/models/marts/schema.yml with unique/not_null tests and referential integrity relationships tests
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.9, 8.10_

  - [~] 12.3 Implement Neo4j graph population from ELT output
    - Create src/infrastructure/adapters/neo4j_loader.py with load_nodes_from_csv and load_edges_from_csv functions
    - Create Neo4j indexes on customer_id, address_hash, ip_address, phone_number
    - Implement parameterized MERGE Cypher statements for idempotent loading
    - _Requirements: 9.1, 9.2, 28.1, 28.2, 28.3, 28.4, 28.5, 28.6_

  - [ ]* 12.4 Write property tests for ELT idempotence and referential integrity
    - **Property 5: ELT Pipeline Idempotence**
    - **Property 6: Referential Integrity of Graph Edges**
    - **Property 7: Entity ID Uniqueness**
    - Create tests/property/test_elt_idempotence.py verifying double-run produces identical output
    - Create tests/property/test_graph_invariants.py verifying edge referential integrity and entity_id uniqueness
    - **Validates: Requirements 8.9, 8.10, 8.11, 28.7, 28.8**

- [ ] 13. Synthetic data generation
  - [~] 13.1 Implement synthetic data generator module
    - Create src/domain/testing/synthetic_data.py with generate_clean_customer, generate_watchlisted_entity, generate_fraud_ring_member functions
    - Generate shared infrastructure (addresses, IPs, phones) linking fraud ring members to flagged entities
    - Generate corresponding WatchlistEntry records for engineered fraud ring members
    - Ensure all generated payloads conform to CustomerOnboardingPayload schema (strict=True)
    - Provide at least 100 records per scenario type
    - _Requirements: 23.1, 23.2, 23.3, 23.4, 23.5, 23.6_

  - [ ]* 13.2 Write property test for synthetic data generator correctness
    - **Property 17: Synthetic Data Generator Correctness**
    - Create tests/property/test_synthetic_data.py verifying all generated payloads pass Pydantic validation
    - **Validates: Requirements 23.7**

- [~] 14. Checkpoint — Full pipeline integration validation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 15. Testing infrastructure — Architecture, quality, and security tests
  - [~] 15.1 Implement architecture boundary tests
    - Create tests/architecture/test_boundaries.py using pytest-archon
    - Test: src/domain/ has zero imports from src/infrastructure/
    - Test: src/domain/ has zero imports from src/api/
    - Test: src/agents/ imports only from src/domain/ and stdlib
    - Test: all Port interfaces are abstract with no concrete logic
    - Test: all Adapters implement exactly one Port
    - Test: no circular dependencies between bounded contexts
    - _Requirements: 7.4, 15.3, 38.1, 38.2, 38.3, 38.4, 38.5, 38.6_

  - [~] 15.2 Implement quality tests (ruff + mypy subprocess assertions)
    - Create tests/quality/test_coding_standards.py executing ruff check and mypy --strict as subprocess assertions
    - Fail on any lint or type error with specific violation details
    - _Requirements: 15.4, 19.7_

  - [~] 15.3 Implement security guardrail tests
    - Create tests/security/test_guardrails.py with adversarial input test cases
    - Test prompt injection patterns are rejected with 400
    - Test tool scope violations are caught and logged
    - Test Cypher injection attempts are blocked by whitelist
    - Test rate limiting enforces 100 req/min
    - Test max payload size (1MB) is enforced
    - _Requirements: 15.5, 11.1, 11.3, 11.5, 11.8, 11.9_

  - [ ]* 15.4 Write property test for Cypher query parameterization
    - **Property 16: Cypher Query Parameterization**
    - Create tests/property/test_cypher_security.py verifying all constructed queries use $param syntax
    - **Validates: Requirements 9.7**

  - [~] 15.5 Implement retrieval tests for Graph_Analyst
    - Create tests/retrieval/test_graph_retrieval.py with engineered fraud profiles
    - Verify Two_Hop_Neighborhood extraction returns correct connected entities
    - Verify path_length invariant (≤ 2 hops) holds for all results
    - _Requirements: 15.6, 5.1, 5.9_

  - [ ]* 15.6 Write property test for graph path length invariant
    - **Property 4: Graph Path Length Invariant**
    - Create tests/property/test_graph_invariants.py (extend) verifying all FraudPath.path_length ≤ 2
    - **Validates: Requirements 5.9, 9.8**

- [ ] 16. Testing infrastructure — Integration and E2E tests
  - [~] 16.1 Implement integration tests
    - Create tests/integration/conftest.py with Docker fixtures for Neo4j (testcontainers or docker-compose)
    - Create tests/integration/test_elt_pipeline.py executing real dbt run against test DuckDB
    - Create tests/integration/test_neo4j_queries.py executing real Cypher against Neo4j container
    - Create tests/integration/test_api_endpoints.py with FastAPI TestClient exercising all endpoints
    - _Requirements: 15.2, 8.7, 8.8_

  - [~] 16.2 Implement end-to-end pipeline tests
    - Create tests/e2e/test_full_pipeline.py exercising: CSV ingestion → dbt transform → Neo4j population → LangGraph orchestration → compliance report output
    - Test all three scenarios: clean_customer (APPROVE), watchlisted_entity (DENY), fraud_ring_member (DENY or ESCALATE)
    - Verify correlation_id propagation end-to-end
    - _Requirements: 15.7, 25.1_

  - [ ]* 16.3 Write property tests for sanctions screening bounds
    - **Property 13: Sanctions Screening Result Bound (Metamorphic)**
    - **Property 14: Watchlist Non-Interference (Metamorphic)**
    - Create tests/property/test_sanctions_properties.py verifying result count ≤ N×M and non-interference
    - **Validates: Requirements 4.9, 24.7**

  - [ ]* 16.4 Write property test for explainability hash integrity
    - **Property 18: Explainability Hash Integrity**
    - Create tests/property/test_explainability.py verifying prompt_template_hash == SHA-256 of actual template
    - **Validates: Requirements 13.7**

- [~] 17. Checkpoint — Complete test suite validation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 18. Infrastructure as Code — Terraform modules
  - [~] 18.1 Implement Terraform root configuration and backend
    - Create terraform/providers.tf with AWS provider (version pinned)
    - Create terraform/backend.tf with S3 remote state + DynamoDB locking
    - Create terraform/variables.tf with all global variables (typed, described)
    - Create terraform/outputs.tf with resource identifiers and endpoints
    - Create terraform/main.tf composing all modules
    - Create terraform/terraform.tfvars.example and terraform/environments/ (dev.tfvars, staging.tfvars, prod.tfvars)
    - _Requirements: 16.1, 16.6, 16.7, 16.8, 16.9, 39.2, 39.3, 39.10_

  - [~] 18.2 Implement Terraform networking and IAM modules
    - Create terraform/modules/networking/ (VPC, public/private subnets across 2 AZs, security groups, ALB)
    - Create terraform/modules/iam/ (ECS task roles, Bedrock access policies, least privilege)
    - Tag all resources: project, environment, service, owner
    - Mark sensitive variables with sensitive=true
    - _Requirements: 16.5, 31.1, 32.1, 34.6, 39.4_

  - [~] 18.3 Implement Terraform ECS, Neptune, and S3 modules
    - Create terraform/modules/ecs/ (cluster, service, task definition, auto-scaling target 70% CPU, min/max task count)
    - Create terraform/modules/neptune/ (cluster, primary instance, read replica in separate AZ, subnet group, prevent_destroy lifecycle)
    - Create terraform/modules/s3/ (raw data bucket, audit log bucket, encryption AES-256, prevent_destroy on audit)
    - _Requirements: 16.2, 16.3, 16.4, 31.2, 31.4, 31.5, 32.2, 32.3, 32.4, 32.5, 34.3, 39.8_

- [ ] 19. Developer experience — Steering files, hooks, and CI/CD
  - [~] 19.1 Create steering files
    - Create .kiro/steering/product.md documenting business logic (synthetic identity ring detection, KYC flow, compliance reqs, AML/CTF alignment)
    - Create .kiro/steering/tech.md documenting technical constraints (Python 3.11+, dependency versions, LLM providers, infrastructure)
    - Create .kiro/steering/structure.md documenting hexagonal architecture rules, DDD boundaries, import restrictions, naming conventions (Port, Adapter, Agent suffixes)
    - Create .kiro/steering/testing.md documenting multi-tiered testing strategy, property-based testing patterns, Hypothesis configuration
    - _Requirements: 35.1, 35.2, 35.3, 35.4, 35.5, 35.7, 19.8_

  - [~] 19.2 Create CI/CD pipeline configuration
    - Create .github/workflows/ci.yml with stages: lint (ruff), typecheck (mypy), unit tests, property tests, architecture tests, security tests, integration tests (Docker), quality tests, coverage gate (≥80%)
    - Create .github/workflows/cd.yml with build Docker image (tagged with commit SHA + semver), security scanning, staging deploy, smoke test, production deploy with promotion gate
    - Implement rollback support and cache dependencies between runs
    - _Requirements: 29.1, 29.2, 29.3, 29.4, 29.5, 29.6, 29.7, 29.8, 29.9, 29.10_

  - [~] 19.3 Create prompt template registry and version management
    - Create src/domain/templates/ directory with versioned prompt templates for each agent
    - Implement template loading with SHA-256 hashing for explainability
    - Store templates with versioned identifiers for historical reproducibility
    - _Requirements: 13.6, 13.7_

- [~] 20. Final checkpoint — Full system validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at logical boundaries
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The design uses Python throughout — all implementation tasks use Python 3.11+ with type annotations
- All adapters are interchangeable via the DI container (swap Neo4jAdapter for InMemoryGraphAdapter in tests)
- Terraform modules follow AWS best practices with state locking, environment separation, and resource lifecycle protection

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4"] },
    { "id": 2, "tasks": ["2.1", "2.2", "2.3"] },
    { "id": 3, "tasks": ["2.4", "2.5", "3.1", "3.2"] },
    { "id": 4, "tasks": ["4.1", "4.3"] },
    { "id": 5, "tasks": ["4.2", "6.1", "6.2"] },
    { "id": 6, "tasks": ["7.1", "7.2", "7.3"] },
    { "id": 7, "tasks": ["7.4", "8.1", "8.2", "8.3", "8.4"] },
    { "id": 8, "tasks": ["8.5", "9.1", "9.2"] },
    { "id": 9, "tasks": ["9.3", "11.1", "11.2"] },
    { "id": 10, "tasks": ["11.3", "11.4", "12.1"] },
    { "id": 11, "tasks": ["12.2", "12.3", "13.1"] },
    { "id": 12, "tasks": ["12.4", "13.2"] },
    { "id": 13, "tasks": ["15.1", "15.2", "15.3"] },
    { "id": 14, "tasks": ["15.4", "15.5", "15.6"] },
    { "id": 15, "tasks": ["16.1", "16.2"] },
    { "id": 16, "tasks": ["16.3", "16.4"] },
    { "id": 17, "tasks": ["18.1"] },
    { "id": 18, "tasks": ["18.2", "18.3"] },
    { "id": 19, "tasks": ["19.1", "19.2", "19.3"] }
  ]
}
```
