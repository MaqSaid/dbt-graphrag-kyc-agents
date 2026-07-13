# Autonomous Multi-Agent KYC Investigation & Fraud Network Pipeline

> **Hexagonal Architecture • GraphRAG • LangGraph • Strands Agents • dbt • Neo4j • FastAPI**

An enterprise-grade, autonomous KYC (Know Your Customer) evaluation pipeline that detects synthetic identity fraud rings using a multi-agent system with graph-based relationship analysis, explainable AI decisions, and ISO 27001/42001 compliance.

---

## STAR Method: Project Overview

### 🎯 Situation (What & Why)

Financial institutions are required by AML/CTF regulations to verify customer identities during onboarding. Traditional KYC checks operate in **isolation** — verifying documents, screening names against watchlists — but fail to detect **synthetic identity fraud rings** where criminals share infrastructure (addresses, IPs, phone numbers) across multiple fabricated identities.

**The gap:** A fraudster can pass every individual check while being one hop away from a blacklisted entity in a relationship graph that nobody is querying.

### 📋 Task (The Challenge)

Build a system that:
1. Accepts customer onboarding requests via API
2. Orchestrates 5 specialized AI agents through a deterministic workflow
3. Discovers hidden multi-hop relationships between applicants and flagged entities using graph traversal (GraphRAG)
4. Generates explainable compliance reports with full audit trails
5. Issues decisions (APPROVE / DENY / ESCALATE) with regulatory-grade documentation

**Constraints:**
- Zero architecture coupling between business logic and infrastructure (Hexagonal)
- Every LLM decision must be traceable and reproducible (ISO 42001)
- Every evaluation must have an immutable audit trail (ISO 27001)
- Must handle 10+ concurrent evaluations under 120 seconds each

### 🛠️ Action (How)

**Architecture:** Hexagonal (Ports & Adapters) with Domain-Driven Design bounded contexts

**Agent Orchestration:**
- **LangGraph** StateGraph manages the evaluation workflow as a deterministic state machine
- **Strands Agents SDK** powers each worker agent with LLM-driven tool selection loops
- No agent communicates directly with another — all coordination flows through typed `KYCState`

**Fraud Detection (GraphRAG):**
- Raw onboarding data is transformed via **dbt + DuckDB** into graph-ready models
- **Neo4j** stores the relationship graph (Customer → Address → Customer linkages)
- The Graph Analyst agent traverses 2-hop neighborhoods to discover connections to watchlisted entities
- Discovered paths become context for LLM-generated risk assessments

**Tech Stack:**
| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Orchestration | LangGraph (StateGraph) |
| Agents | Strands Agents SDK (@tool pattern) |
| Graph DB | Neo4j 5 / Amazon Neptune |
| Warehouse | DuckDB |
| ELT | dbt-core + dbt-duckdb |
| API | FastAPI + Pydantic v2 |
| LLM | Amazon Bedrock / OpenAI-compatible |
| IaC | Terraform (AWS: ECS Fargate, Neptune, S3) |
| Testing | pytest + Hypothesis (property-based) |
| Quality | Ruff + Mypy (strict) |

### 📊 Result (Outcome)

- **5 specialized agents** working as a coordinated team
- **18 correctness properties** verified via property-based testing
- **40 EARS-notation requirements** fully implemented
- **7 architectural boundary tests** preventing layer violations
- **Complete Terraform IaC** for production AWS deployment
- **Decision determinism guaranteed** — same inputs always produce same output
- **Full explainability** — every LLM assertion traced to source data nodes

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                            │
│  POST /evaluate • GET /status/{id} • GET /report/{id} • GET /health  │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ Security Middleware: Injection Detection • JWT Auth • RBAC   │     │
│  └─────────────────────────────────────────────────────────────┘     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│                    Application Layer (LangGraph)                       │
│                                                                       │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐        │
│  │INITIALIZE│───▶│ VERIFY   │───▶│ SCREEN   │───▶│ ANALYZE  │        │
│  │          │    │ IDENTITY │    │SANCTIONS │    │  GRAPH   │        │
│  └─────────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘        │
│                       │retry          │retry          │               │
│                       ▼               ▼               ▼               │
│                  ┌──────────┐    ┌──────────┐    ┌──────────┐        │
│                  │  DRAFT   │───▶│ EVALUATE │───▶│ FINALIZE │        │
│                  │  REPORT  │    │ DECISION │    │          │        │
│                  └──────────┘    └──────────┘    └──────────┘        │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│                      Agent Layer (Strands SDK)                         │
│                                                                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐    │
│  │Identity Verifier │ │Sanctions Analyst│ │ Graph Analyst        │    │
│  │• validate_email  │ │• search_ofac    │ │• query_address_nbr  │    │
│  │• validate_phone  │ │• search_eu      │ │• query_ip_nbr       │    │
│  │• check_registry  │ │• search_un      │ │• extract_fraud_paths│    │
│  │• confidence_score│ │• search_pep     │ │• compute_risk_score │    │
│  └─────────────────┘ │• match_similarity│ └─────────────────────┘    │
│                       └─────────────────┘                             │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ Report Drafter: executive_summary • risk_assessment • trace  │     │
│  └─────────────────────────────────────────────────────────────┘     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ (via Port interfaces)
┌───────────────────────────────▼──────────────────────────────────────┐
│                    Domain Layer (Pure Business Logic)                  │
│                                                                       │
│  Ports (ABCs)        │  Schemas (Pydantic v2)  │  Decision Engine    │
│  • GraphDatabasePort │  • KYCState             │  • composite_score  │
│  • LLMClientPort     │  • CustomerPayload      │  • evaluate_decision│
│  • WatchlistPort     │  • VerificationResult   │  • has_critical_flag│
│  • AuditLogPort      │  • ScreeningResult      │                     │
│  • WarehousePort     │  • GraphAnalysisResult  │  Exceptions         │
│  • RegistryPort      │  • ComplianceReport     │  • KYCEvaluationErr │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ (implements Ports)
┌───────────────────────────────▼──────────────────────────────────────┐
│                   Infrastructure Layer (Adapters)                      │
│                                                                       │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐ ┌───────────────┐   │
│  │Neo4jAdapter│ │BedrockAdptr│ │WatchlistAdptr│ │S3AuditAdapter │   │
│  └────────────┘ └────────────┘ └──────────────┘ └───────────────┘   │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐                     │
│  │OpenAIAdptr │ │DuckDBAdptr │ │RegistryAdptr │  + CircuitBreaker   │
│  └────────────┘ └────────────┘ └──────────────┘  + Retry + Metrics  │
└──────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│                      External Systems                                  │
│  Neo4j │ DuckDB │ Amazon Bedrock │ S3 │ Watchlist APIs │ Registry    │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Flow: Fraud Ring Detection

```
Raw CSV ──▶ DuckDB (load) ──▶ dbt (transform) ──▶ Neo4j (graph)
                                    │
                    ┌───────────────┼────────────────┐
                    ▼               ▼                ▼
            nodes_customer    nodes_address     edges_shares_*
                    │               │                │
                    └───────────────┼────────────────┘
                                    ▼
                        Graph Analyst queries 2-hop
                        neighborhood from customer's
                        address/IP/phone nodes
                                    │
                                    ▼
                    Discovers: Customer → Address → Flagged Entity
                              (path_length = 2, risk = HIGH)
                                    │
                                    ▼
                        DENY decision + Compliance Report
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Runtime |
| uv | latest | Package manager |
| Docker | 24+ | Neo4j container |
| Docker Compose | 2.0+ | Service orchestration |
| Git | 2.40+ | Version control |

**Optional (for production):**
| Tool | Version | Purpose |
|------|---------|---------|
| Terraform | 1.7+ | AWS provisioning |
| AWS CLI | 2.0+ | Cloud access |

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/dbt-graphrag-kyc-agents.git
cd dbt-graphrag-kyc-agents
```

### 2. Install Dependencies

```bash
# Install uv if not already installed
pip install uv

# Install all project dependencies (including dev)
uv sync
```

### 3. Start Infrastructure

```bash
# Start Neo4j (graph database)
make docker-up

# Verify Neo4j is running
# Browser: http://localhost:7474 (neo4j/development)
# Bolt: bolt://localhost:7687
```

### 4. Initialize the Data Pipeline

```bash
# Load seed data into DuckDB and run dbt transformations
make dbt-run

# Verify data quality (unique constraints, referential integrity)
make dbt-test
```

### 5. Configure Environment

Create a `.env` file (or set environment variables):

```bash
# Required
KYC_NEO4J_URI=bolt://localhost:7687
KYC_NEO4J_AUTH=neo4j/development
KYC_AWS_REGION=us-east-1

# Optional (defaults provided)
KYC_DEFAULT_LLM_MODEL=anthropic.claude-sonnet-4-20250514
KYC_DUCKDB_PATH=./data/warehouse.duckdb
KYC_AUDIT_BUCKET=kyc-audit-logs
KYC_RATE_LIMIT_PER_MINUTE=100
```

### 6. Run the Application

```bash
# Start the API server (development mode with hot reload)
make run

# API available at: http://localhost:8000
# Docs: http://localhost:8000/docs
# Health: http://localhost:8000/api/v1/health
```

---

## Usage

### Submit a KYC Evaluation

```bash
curl -X POST http://localhost:8000/api/v1/kyc/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Smith",
    "date_of_birth": "1985-03-15",
    "national_id": "SSN123456789",
    "address": "123 Main St Apt 4 New York NY 10001",
    "email": "john.smith@email.com",
    "phone": "+14155551234",
    "ip_address": "192.168.1.100"
  }'
```

**Response (202 Accepted):**
```json
{
  "evaluation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "accepted",
  "message": "KYC evaluation submitted successfully"
}
```

### Poll Evaluation Status

```bash
curl http://localhost:8000/api/v1/kyc/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Retrieve Compliance Report

```bash
curl http://localhost:8000/api/v1/kyc/report/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

## Running Tests

```bash
# Full test suite
make test-all

# Individual test tiers
make test-unit            # Domain logic (mocked adapters)
make test-property        # Hypothesis property-based tests
make test-architecture    # Hexagonal boundary enforcement
make test-security        # Adversarial input guardrails
make test-quality         # Ruff + Mypy assertions
make test-integration     # Real DuckDB + Neo4j (requires Docker)

# With coverage report
make test                 # Unit tests + coverage
```

### Key Test Commands

| Command | What it verifies |
|---------|-----------------|
| `make test-architecture` | Domain never imports infrastructure |
| `make test-security` | Prompt injection always rejected |
| `make test-property` | Decision scores bounded [0,1], deterministic |
| `make test-quality` | Code passes ruff + mypy strict |

---

## Project Structure

```
dbt-graphrag-kyc-agents/
├── src/
│   ├── domain/              # Pure business logic (no I/O)
│   │   ├── ports/           # 6 abstract interfaces (ABCs)
│   │   ├── schemas/         # 8 Pydantic v2 strict models
│   │   ├── orchestration/   # Decision engine
│   │   └── exceptions.py    # Typed error hierarchy
│   ├── infrastructure/      # External system implementations
│   │   ├── adapters/        # 7 port implementations
│   │   ├── resilience/      # Circuit breaker + retry
│   │   └── observability/   # Structured logging + metrics
│   ├── application/         # Wiring layer
│   │   ├── orchestrator.py  # LangGraph state machine
│   │   └── container.py     # Dependency injection
│   ├── api/                 # HTTP boundary
│   │   ├── routes/          # FastAPI endpoints
│   │   └── middleware/      # Security, auth, rate limiting
│   └── agents/              # 4 Strands agent definitions
├── dbt_kyc/                 # ELT pipeline (dbt + DuckDB)
│   ├── models/staging/      # Cleaning + deduplication
│   ├── models/marts/        # Graph-ready node/edge models
│   └── seeds/               # Sample data with fraud ring
├── terraform/               # AWS Infrastructure as Code
│   └── modules/             # networking, ecs, neptune, s3, iam
├── tests/                   # Multi-tiered test suite
│   ├── property/            # Hypothesis invariant tests
│   ├── architecture/        # Boundary enforcement
│   ├── security/            # Adversarial input tests
│   └── quality/             # Linting/typing assertions
├── .kiro/steering/          # AI development guidance
├── .github/workflows/       # CI/CD pipelines
├── pyproject.toml           # Dependencies + tool config
├── Makefile                 # 20+ development commands
├── Dockerfile               # Multi-stage production build
└── docker-compose.yml       # Local dev (Neo4j)
```

---

## Production Deployment (AWS)

```bash
# Initialize Terraform
cd terraform
terraform init

# Plan infrastructure changes
terraform plan -var-file=environments/prod.tfvars

# Apply (provisions ECS Fargate, Neptune, S3, IAM)
terraform apply -var-file=environments/prod.tfvars
```

**AWS Resources Provisioned:**
- ECS Fargate cluster with auto-scaling (CPU target 70%)
- Amazon Neptune with read replica (multi-AZ)
- S3 buckets (raw data + audit logs, AES-256 encrypted)
- IAM roles with least-privilege Bedrock access
- Application Load Balancer with health checks
- VPC with public/private subnets across 2 AZs

---

## Decision Logic

```
Composite Risk Score = (1 - identity_confidence) × 0.3
                     + sanctions_match_score × 0.4
                     + network_risk_score × 0.3

┌─────────────────────────────────────────────────┐
│ Critical Flag (confirmed match/fraud ring)?      │
│   YES → DENY immediately                        │
│   NO  → Continue to score evaluation            │
├─────────────────────────────────────────────────┤
│ Score < 0.3  → APPROVE                          │
│ Score > 0.7  → DENY                             │
│ 0.3 ≤ Score ≤ 0.7 → ESCALATE_TO_HUMAN_REVIEW   │
└─────────────────────────────────────────────────┘
```

All thresholds and weights are configurable via environment variables without code changes.

---

## License

MIT

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Ensure tests pass (`make test-all`)
4. Ensure linting passes (`make lint && make typecheck`)
5. Submit a Pull Request

Architecture boundary tests run on every PR — your changes must not violate hexagonal import rules.
