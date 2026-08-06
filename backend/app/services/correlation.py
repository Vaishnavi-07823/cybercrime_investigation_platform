from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Case, Entity, NormalizedEvent, Relationship
from app.services.audit import record_audit
from app.services.graph import graph_store


def canonicalize(value: object) -> str:
    return unicodedata.normalize("NFKC", str(value)).casefold().strip()


def relationship_fingerprint(
    source_id: str,
    relation_type: str,
    target_id: str,
    event_refs: Iterable[str],
) -> str:
    payload = {
        "source": source_id,
        "relation": relation_type,
        "target": target_id,
        "events": sorted(event_refs),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def get_or_create_entity(
    db: Session,
    *,
    case_id: str,
    entity_type: str,
    value: object,
    attributes: dict | None = None,
    confidence: float = 1.0,
) -> Entity:
    canonical = canonicalize(value)
    entity = db.scalar(
        select(Entity).where(
            Entity.case_id == case_id,
            Entity.entity_type == entity_type,
            Entity.canonical_value == canonical,
        )
    )
    if entity:
        return entity
    entity = Entity(
        case_id=case_id,
        entity_type=entity_type,
        canonical_value=canonical,
        display_value=str(value),
        attributes=attributes or {},
        confidence=confidence,
    )
    db.add(entity)
    db.flush()
    return entity


def create_relationship(
    db: Session,
    *,
    case_id: str,
    source: Entity,
    relation_type: str,
    target: Entity,
    event: NormalizedEvent,
    confidence: float = 1.0,
    directly_observed: bool = True,
    attributes: dict | None = None,
) -> Relationship:
    event_refs = [event.id]
    fingerprint = relationship_fingerprint(source.id, relation_type, target.id, event_refs)
    existing = db.scalar(
        select(Relationship).where(
            Relationship.case_id == case_id,
            Relationship.fingerprint == fingerprint,
        )
    )
    if existing:
        return existing
    relationship = Relationship(
        case_id=case_id,
        source_entity_id=source.id,
        target_entity_id=target.id,
        relation_type=relation_type,
        event_refs=event_refs,
        evidence_refs=[event.evidence_id],
        confidence=confidence,
        directly_observed=directly_observed,
        attributes=attributes or {},
        fingerprint=fingerprint,
    )
    db.add(relationship)
    db.flush()
    return relationship


def run_correlations(
    db: Session,
    case: Case,
    *,
    user_id: str,
    source_ip: str | None = None,
) -> tuple[list[Entity], list[Relationship]]:
    events = list(
        db.scalars(
            select(NormalizedEvent)
            .where(NormalizedEvent.case_id == case.id)
            .order_by(NormalizedEvent.event_time)
        )
    )
    touched_entities: dict[str, Entity] = {}
    touched_relationships: dict[str, Relationship] = {}

    def remember_entity(entity: Entity) -> Entity:
        touched_entities[entity.id] = entity
        return entity

    def remember_relationship(relationship: Relationship) -> Relationship:
        touched_relationships[relationship.id] = relationship
        return relationship

    for event in events:
        user_value = event.actor.get("email") or event.actor.get("user")
        if event.event_type == "identity.authentication" and user_value and event.source.get("ip"):
            user = remember_entity(
                get_or_create_entity(
                    db, case_id=case.id, entity_type="UserAccount", value=user_value
                )
            )
            ip = remember_entity(
                get_or_create_entity(
                    db,
                    case_id=case.id,
                    entity_type="IPAddress",
                    value=event.source["ip"],
                    attributes={"country": event.source.get("country")},
                )
            )
            remember_relationship(
                create_relationship(
                    db,
                    case_id=case.id,
                    source=user,
                    relation_type="AUTHENTICATED_FROM",
                    target=ip,
                    event=event,
                )
            )

        if event.event_type == "mailbox.rule" and user_value:
            user = remember_entity(
                get_or_create_entity(
                    db, case_id=case.id, entity_type="UserAccount", value=user_value
                )
            )
            rule_value = event.payload.get("rule_name") or f"rule:{event.id}"
            rule = remember_entity(
                get_or_create_entity(
                    db,
                    case_id=case.id,
                    entity_type="MailboxRule",
                    value=rule_value,
                    attributes={"external": event.payload.get("external_forwarding", False)},
                )
            )
            remember_relationship(
                create_relationship(
                    db,
                    case_id=case.id,
                    source=user,
                    relation_type="CREATED",
                    target=rule,
                    event=event,
                )
            )
            target_email = event.payload.get("forward_to")
            if target_email:
                target = remember_entity(
                    get_or_create_entity(
                        db,
                        case_id=case.id,
                        entity_type="EmailAddress",
                        value=target_email,
                    )
                )
                remember_relationship(
                    create_relationship(
                        db,
                        case_id=case.id,
                        source=rule,
                        relation_type="FORWARDED_TO",
                        target=target,
                        event=event,
                    )
                )

        if event.event_type == "email.message":
            sender = event.source.get("email")
            domain_value = event.payload.get("sender_domain") or event.source.get("domain")
            if sender:
                email_entity = remember_entity(
                    get_or_create_entity(
                        db, case_id=case.id, entity_type="EmailAddress", value=sender
                    )
                )
                if domain_value:
                    domain = remember_entity(
                        get_or_create_entity(
                            db, case_id=case.id, entity_type="Domain", value=domain_value
                        )
                    )
                    remember_relationship(
                        create_relationship(
                            db,
                            case_id=case.id,
                            source=email_entity,
                            relation_type="USES_DOMAIN",
                            target=domain,
                            event=event,
                        )
                    )

        if event.event_type in {"payment.payee_change", "payment.approval"}:
            account = event.payload.get("bank_account") or event.destination.get("bank_account")
            if account:
                bank = remember_entity(
                    get_or_create_entity(
                        db, case_id=case.id, entity_type="BankAccount", value=account
                    )
                )
                if user_value:
                    user = remember_entity(
                        get_or_create_entity(
                            db, case_id=case.id, entity_type="UserAccount", value=user_value
                        )
                    )
                    relation = (
                        "CHANGED_PAYEE_TO"
                        if event.event_type == "payment.payee_change"
                        else "APPROVED_PAYMENT_TO"
                    )
                    remember_relationship(
                        create_relationship(
                            db,
                            case_id=case.id,
                            source=user,
                            relation_type=relation,
                            target=bank,
                            event=event,
                        )
                    )

    record_audit(
        db,
        action="correlations.run",
        object_type="case",
        object_id=case.id,
        case_id=case.id,
        user_id=user_id,
        source_ip=source_ip,
        details={
            "entities_touched": len(touched_entities),
            "relationships_touched": len(touched_relationships),
        },
    )
    db.commit()

    for entity in touched_entities.values():
        try:
            graph_store.upsert_entity(entity)
        except Exception:
            pass
    for relationship in touched_relationships.values():
        try:
            graph_store.upsert_relationship(
                relationship,
                touched_entities.get(relationship.source_entity_id)
                or db.get(Entity, relationship.source_entity_id),
                touched_entities.get(relationship.target_entity_id)
                or db.get(Entity, relationship.target_entity_id),
            )
        except Exception:
            pass
    return list(touched_entities.values()), list(touched_relationships.values())
