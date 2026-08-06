from __future__ import annotations

import os
from pathlib import Path

import httpx


BASE_URL = os.getenv("CIP_BASE_URL", "http://localhost:8000/api/v1")
EMAIL = os.getenv("CIP_ADMIN_EMAIL", "admin@example.local")
PASSWORD = os.getenv("CIP_ADMIN_PASSWORD", "ChangeMeNow!123")
ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = Path("/workspace/sample-data") if Path("/workspace/sample-data").exists() else ROOT / "sample-data"


def require(response: httpx.Response) -> dict:
    response.raise_for_status()
    return response.json()


def main() -> None:
    with httpx.Client(timeout=90) as client:
        login = require(
            client.post(
                f"{BASE_URL}/auth/login",
                json={"email": EMAIL, "password": PASSWORD},
            )
        )
        headers = {"Authorization": f"Bearer {login['access_token']}"}

        case = require(
            client.post(
                f"{BASE_URL}/cases",
                headers=headers,
                json={
                    "title": "Simulated BEC Investigation",
                    "description": "Fictional case for testing the end-to-end evidence workflow.",
                    "case_type": "bec",
                    "severity": "high",
                    "classification": "restricted",
                    "context": {"trusted_domains": ["trusted-supplier.example"]},
                },
            )
        )
        print(f"Created case {case['id']}")

        uploads = [
            ("suspicious-email.eml", "email", "message/rfc822"),
            ("authentication-events.json", "auth_log", "application/json"),
            ("mailbox-audit-events.json", "mailbox_audit", "application/json"),
            ("business-events.json", "generic_json", "application/json"),
        ]
        evidence_ids: list[str] = []
        for filename, source_type, media_type in uploads:
            path = SAMPLE_DIR / filename
            with path.open("rb") as handle:
                evidence = require(
                    client.post(
                        f"{BASE_URL}/cases/{case['id']}/evidence",
                        headers=headers,
                        data={"source_type": source_type, "acquisition_method": "demo_seed"},
                        files={"file": (filename, handle, media_type)},
                    )
                )
            evidence_ids.append(evidence["id"])
            print(f"Uploaded {filename}: {evidence['id']}")

        for evidence_id in evidence_ids:
            result = require(
                client.post(f"{BASE_URL}/evidence/{evidence_id}/process", headers=headers)
            )
            print(f"Processed {evidence_id}: {result['count']} event(s)")

        for endpoint, label in [
            (f"/cases/{case['id']}/detections/run", "detections"),
            (f"/cases/{case['id']}/correlations/run", "correlations"),
            (f"/cases/{case['id']}/narratives/generate", "narrative"),
        ]:
            result = require(client.post(f"{BASE_URL}{endpoint}", headers=headers))
            print(f"Ran {label}: {result['count']}")

        claims = require(client.get(f"{BASE_URL}/cases/{case['id']}/claims", headers=headers))
        for claim in claims:
            require(
                client.patch(
                    f"{BASE_URL}/claims/{claim['id']}/review",
                    headers=headers,
                    json={"decision": "approved", "rationale": "Approved for demo report"},
                )
            )
        print(f"Approved {len(claims)} claim(s)")

        report = require(
            client.post(f"{BASE_URL}/cases/{case['id']}/reports/generate", headers=headers)
        )
        print(f"Generated report {report['id']}")
        print(f"Open the UI and select case: {case['id']}")


if __name__ == "__main__":
    main()
