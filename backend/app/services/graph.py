from __future__ import annotations

from neo4j import GraphDatabase

from app.core.config import get_settings
from app.models import Entity, Relationship


class GraphStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def verify(self) -> None:
        self.driver.verify_connectivity()

    def upsert_entity(self, entity: Entity) -> None:
        query = """
        MERGE (e:Entity {id: $id})
        SET e.case_id = $case_id,
            e.entity_type = $entity_type,
            e.canonical_value = $canonical_value,
            e.display_value = $display_value,
            e.confidence = $confidence
        """
        with self.driver.session() as session:
            session.run(
                query,
                id=entity.id,
                case_id=entity.case_id,
                entity_type=entity.entity_type,
                canonical_value=entity.canonical_value,
                display_value=entity.display_value,
                confidence=entity.confidence,
            )

    def upsert_relationship(
        self,
        relationship: Relationship,
        source: Entity,
        target: Entity,
    ) -> None:
        query = """
        MERGE (s:Entity {id: $source_id})
        MERGE (t:Entity {id: $target_id})
        MERGE (s)-[r:RELATED {id: $relationship_id}]->(t)
        SET r.case_id = $case_id,
            r.relation_type = $relation_type,
            r.confidence = $confidence,
            r.directly_observed = $directly_observed,
            r.event_refs = $event_refs,
            r.evidence_refs = $evidence_refs
        """
        with self.driver.session() as session:
            session.run(
                query,
                source_id=source.id,
                target_id=target.id,
                relationship_id=relationship.id,
                case_id=relationship.case_id,
                relation_type=relationship.relation_type,
                confidence=relationship.confidence,
                directly_observed=relationship.directly_observed,
                event_refs=relationship.event_refs,
                evidence_refs=relationship.evidence_refs,
            )


graph_store = GraphStore()
