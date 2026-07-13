# Product Context: KYC Fraud Detection Pipeline

## Business Domain
This system detects **Synthetic Identity Fraud Rings** during customer onboarding. A synthetic identity fraud ring is a cluster of entities that share infrastructure (addresses, IPs, phone numbers) with known fraudulent or watchlisted entities.

## Core Use Case
1. A new customer submits an onboarding registration
2. The registration appears legitimate on isolated checks
3. The system discovers shared infrastructure linking this customer to flagged entities
4. A multi-hop graph relationship is mapped and explained
5. A compliance risk assessment is generated with full audit trail

## Agent Topology (5 Agents)
- **Orchestrator** (LangGraph): Manages KYCState, routes between agents, handles retries
- **Identity Verifier** (Strands): Validates customer data fields and registry checks
- **Sanctions Analyst** (Strands): Screens against OFAC, EU, UN, PEP watchlists
- **Graph Analyst** (Strands): Queries Neo4j 2-hop neighborhoods for fraud connections
- **Report Drafter** (Strands): Synthesizes findings into compliance audit narrative

## Decision Logic
- Composite risk score = weighted sum of (1-identity_confidence, sanctions_score, network_score)
- Score < 0.3 → APPROVE
- Score > 0.7 → DENY
- Between → ESCALATE_TO_HUMAN_REVIEW
- Any critical flag (confirmed sanctions match, confirmed fraud ring) → immediate DENY

## Compliance Requirements
- ISO 27001: Immutable audit log with hash chain for every evaluation
- ISO 42001: Explainability metadata (prompt hash, tokens, trace mapping) for every LLM call
- AML/CTF: Full documentation for regulatory examination
