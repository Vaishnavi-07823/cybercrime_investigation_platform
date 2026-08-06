# Technical Architecture

## Runtime components

```mermaid
flowchart TD
    UI[React analyst workspace] --> API[FastAPI REST API]
    API --> PG[(PostgreSQL)]
    API --> MINIO[(MinIO evidence vault)]
    API --> OS[(OpenSearch event index)]
    API --> NEO[(Neo4j correlation graph)]
    API --> REDIS[(Redis)]
    REDIS --> WORKER[Celery worker]
    API --> LLM[Optional OpenAI-compatible LLM]
```

## Evidence processing path

```mermaid
sequenceDiagram
    participant A as Analyst
    participant API as FastAPI
    participant S as MinIO
    participant DB as PostgreSQL
    participant P as Parser
    participant O as OpenSearch

    A->>API: Upload evidence
    API->>API: Calculate SHA-256
    API->>S: Store immutable-style object key
    API->>DB: Evidence metadata + custody entry
    A->>API: Process evidence
    API->>S: Read original bytes
    API->>P: Parse source-specific format
    P-->>API: Canonical events
    API->>DB: Store normalized events
    API->>O: Index searchable representation
```

## Traceability model

```text
Report
  → approved NarrativeClaim
    → Finding / Relationship
      → NormalizedEvent
        → EvidenceArtifact
          → MinIO object + SHA-256
            → CustodyEntry chain
```

## Service responsibilities

### Backend API

- Authentication and local JWT issuance
- Case workflow
- Evidence acquisition
- Integrity verification
- Synchronous parsing and analytics for the MVP
- Narrative generation and validation
- Report generation and download

### PostgreSQL

Authoritative structured store for users, cases, evidence metadata, custody entries, normalized events, findings, entities, relationships, claims, decisions, reports and audit events.

### MinIO

Stores raw evidence and report outputs. Object keys contain case ID, evidence/report ID and content hash. Production deployments should enable object lock, versioning, retention policy and external backup.

### OpenSearch

Derived search index for normalized events. PostgreSQL remains authoritative in the starter implementation. Production deployments should use a retry queue and reconciliation process.

### Neo4j

Derived entity graph. PostgreSQL stores the authoritative entity and relationship metadata, allowing graph reconstruction.

### Redis and Celery

Present as the background-processing foundation. The MVP endpoints execute synchronously for clarity; move expensive parsing, malware analysis, report generation and model inference to versioned Celery tasks in later releases.

## Trust zones

```mermaid
flowchart LR
    U[Untrusted evidence] --> G[Acquisition gateway]
    G --> V[High-integrity evidence zone]
    V --> A[Restricted analytics zone]
    A --> I[Isolated narrative zone]
    I --> H[Human review]
    H --> R[Controlled report export]
```

## Production gaps intentionally left for later

- Enterprise OIDC and phishing-resistant MFA
- Multi-tenant row/key/index isolation
- TLS for every service connection
- WORM/object-lock configuration
- Alembic migrations
- Signed custody manifests and reports
- Dedicated append-only audit sink
- Malware detonation isolation
- High-volume stream processing
- Model registry and model-risk governance
- Data retention and legal-hold engine
- Cross-region disaster recovery
