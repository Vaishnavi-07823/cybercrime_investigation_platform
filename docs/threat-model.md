# Starter Threat Model

## Protected assets

- Original evidence bytes
- Evidence hashes and custody records
- Personal and confidential data
- Detection rules and model configuration
- Analyst decisions
- Reports and exports
- Credentials and signing keys
- Audit history

## Trust boundaries

1. Evidence source to acquisition API
2. Browser to backend API
3. Backend to infrastructure databases
4. Analytics stores to narrative engine
5. Narrative output to analyst decision
6. Platform to exported report recipient

## Principal threats and controls

| Threat | Starter control | Required production enhancement |
|---|---|---|
| Evidence overwrite | Unique object keys and overwrite prevention | Object lock/WORM, versioning and independent backup |
| Evidence modification | SHA-256 verification | Signed acquisition manifest and trusted timestamp |
| Stolen credentials | Password hashing and expiring JWT | OIDC, phishing-resistant MFA and conditional access |
| Unauthorized case access | Authenticated APIs | Case-scoped ABAC/RBAC and tenant isolation |
| Prompt injection | Evidence treated as data; structured references | Model gateway, content isolation, red-team tests and tool allowlists |
| Hallucinated narrative | Reference validation and analyst approval | Entailment verification and claim-level contradiction checks |
| Search-index inconsistency | PostgreSQL remains authoritative | Durable retry queue and reconciliation jobs |
| Graph false linkage | Evidence-bearing deterministic edges | Probabilistic linkage review and merge/split workflow |
| Malicious upload | Size restriction and parser boundaries | Antivirus, sandboxing, file-type validation and isolated workers |
| Audit tampering | Database audit records | Remote append-only hash-chained audit service |
| Secret exposure | `.env` ignored by Git | Vault/KMS, workload identity and rotation |
| Report alteration | Output SHA-256 manifest | Digital signature and trusted timestamping |
| Denial of service | Container resource separation | Rate limits, quotas, autoscaling and backpressure |

## STRIDE checklist

### Spoofing

- Collector and user authentication
- Workload identity
- Short-lived credentials

### Tampering

- Hash raw and derived records
- Immutable storage
- Signed deployment artifacts

### Repudiation

- Log evidence access, processing, review and export
- Store actor, timestamp, object and action

### Information disclosure

- Encrypt in transit and at rest
- Apply least privilege and data minimization
- Redact or tokenize unnecessary personal information before LLM use

### Denial of service

- File limits, rate limits and queue backpressure
- Resource limits for OpenSearch and Neo4j
- Quarantine malformed evidence

### Elevation of privilege

- Separate analyst, reviewer and administrator privileges
- Never let the narrative model execute privileged actions
- Require explicit approval for exports and destructive actions
