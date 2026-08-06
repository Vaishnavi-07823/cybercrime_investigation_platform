from pathlib import Path

from app.parsers import parse_auth_log, parse_eml, parse_generic_json, parse_mailbox_audit


SAMPLES = Path(__file__).resolve().parents[2] / "sample-data"


def test_email_parser_extracts_sender_and_url() -> None:
    event = parse_eml((SAMPLES / "suspicious-email.eml").read_bytes())[0]
    assert event["event_type"] == "email.message"
    assert event["payload"]["sender_domain"] == "trusted-supp1ier.example"
    assert event["payload"]["urls"]


def test_auth_parser_extracts_two_events() -> None:
    events = parse_auth_log((SAMPLES / "authentication-events.json").read_bytes())
    assert len(events) == 2
    assert events[1]["source"]["country"] == "NL"
    assert events[1]["payload"]["managed_device"] is False


def test_mailbox_parser_detects_external_forwarding() -> None:
    event = parse_mailbox_audit((SAMPLES / "mailbox-audit-events.json").read_bytes())[0]
    assert event["event_type"] == "mailbox.rule"
    assert event["payload"]["external_forwarding"] is True


def test_generic_parser_preserves_business_event_types() -> None:
    events = parse_generic_json((SAMPLES / "business-events.json").read_bytes())
    assert {event["event_type"] for event in events} == {
        "identity.oauth_consent",
        "payment.payee_change",
        "payment.approval",
    }
