# API Reference Summary

Interactive OpenAPI documentation is available at `http://localhost:8000/docs` after startup.

## Authentication

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@example.local",
  "password": "ChangeMeNow!123"
}
```

Use the returned token:

```http
Authorization: Bearer <access-token>
```

## Cases

```text
POST   /api/v1/cases
GET    /api/v1/cases
GET    /api/v1/cases/{case_id}
PATCH  /api/v1/cases/{case_id}
```

## Evidence

```text
POST   /api/v1/cases/{case_id}/evidence
GET    /api/v1/cases/{case_id}/evidence
GET    /api/v1/evidence/{evidence_id}
GET    /api/v1/evidence/{evidence_id}/custody
GET    /api/v1/evidence/{evidence_id}/custody/verify
POST   /api/v1/evidence/{evidence_id}/verify
POST   /api/v1/evidence/{evidence_id}/legal-hold
POST   /api/v1/evidence/{evidence_id}/process
```

Upload uses `multipart/form-data` fields:

```text
source_type: email | auth_log | mailbox_audit | generic_json
acquisition_method: optional string
notes: optional string
file: evidence file
```

## Analytics

```text
GET    /api/v1/cases/{case_id}/events
POST   /api/v1/cases/{case_id}/detections/run
GET    /api/v1/cases/{case_id}/findings
POST   /api/v1/cases/{case_id}/correlations/run
GET    /api/v1/cases/{case_id}/entities
GET    /api/v1/cases/{case_id}/relationships
```

## Narratives

```text
POST   /api/v1/cases/{case_id}/narratives/generate
GET    /api/v1/cases/{case_id}/claims
PATCH  /api/v1/claims/{claim_id}/review
```

Review example:

```json
{
  "decision": "approved",
  "rationale": "Verified against the original email and identity audit events"
}
```

Allowed decisions:

```text
approved
rejected
needs_evidence
edited
```

## Reports

```text
POST   /api/v1/cases/{case_id}/reports/generate
GET    /api/v1/cases/{case_id}/reports
GET    /api/v1/reports/{report_id}/download/pdf
GET    /api/v1/reports/{report_id}/download/json
```

At least one narrative claim must be approved before report generation.

## Audit

```text
GET    /api/v1/cases/{case_id}/audit
```

The starter endpoint is restricted to `admin` and `reviewer` roles.
