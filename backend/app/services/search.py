from __future__ import annotations

from opensearchpy import OpenSearch

from app.core.config import get_settings
from app.models import NormalizedEvent


class EventSearch:
    def __init__(self) -> None:
        settings = get_settings()
        self.index = settings.opensearch_index
        self.client = OpenSearch(
            hosts=[settings.opensearch_url],
            verify_certs=settings.opensearch_verify_certs,
            ssl_show_warn=False,
        )

    def ensure_index(self) -> None:
        if self.client.indices.exists(index=self.index):
            return
        self.client.indices.create(
            index=self.index,
            body={
                "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
                "mappings": {
                    "properties": {
                        "case_id": {"type": "keyword"},
                        "evidence_id": {"type": "keyword"},
                        "event_type": {"type": "keyword"},
                        "event_action": {"type": "keyword"},
                        "event_outcome": {"type": "keyword"},
                        "event_time": {"type": "date"},
                        "actor": {"type": "object", "enabled": True},
                        "source": {"type": "object", "enabled": True},
                        "destination": {"type": "object", "enabled": True},
                        "observables": {"type": "object", "enabled": True},
                        "payload": {"type": "object", "enabled": False},
                    }
                },
            },
        )

    def index_event(self, event: NormalizedEvent) -> None:
        body = {
            "id": event.id,
            "case_id": event.case_id,
            "evidence_id": event.evidence_id,
            "event_type": event.event_type,
            "event_action": event.event_action,
            "event_outcome": event.event_outcome,
            "event_time": event.event_time.isoformat(),
            "actor": event.actor,
            "source": event.source,
            "destination": event.destination,
            "observables": event.observables,
            "payload": event.payload,
            "quality": event.quality,
        }
        self.client.index(index=self.index, id=event.id, body=body, refresh=False)


search = EventSearch()
