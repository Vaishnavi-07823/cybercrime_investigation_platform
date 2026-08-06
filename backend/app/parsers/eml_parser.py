from __future__ import annotations

import hashlib
import re
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from urllib.parse import urlparse

from app.parsers.common import parse_time


URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def _addresses(values: list[str]) -> list[str]:
    return [address.casefold() for _, address in getaddresses(values) if address]


def _extract_body(message) -> tuple[str, str]:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            content_type = part.get_content_type()
            try:
                content = part.get_content()
            except Exception:
                continue
            if not isinstance(content, str):
                continue
            if content_type == "text/plain":
                plain_parts.append(content)
            elif content_type == "text/html":
                html_parts.append(content)
    else:
        try:
            content = message.get_content()
        except Exception:
            content = ""
        if isinstance(content, str):
            if message.get_content_type() == "text/html":
                html_parts.append(content)
            else:
                plain_parts.append(content)
    return "\n".join(plain_parts), "\n".join(html_parts)


def parse_eml(raw: bytes) -> list[dict]:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    event_time, inferred = parse_time(message.get("Date"))
    senders = _addresses(message.get_all("From", []))
    recipients = _addresses(
        message.get_all("To", []) + message.get_all("Cc", []) + message.get_all("Bcc", [])
    )
    reply_to = _addresses(message.get_all("Reply-To", []))
    plain, html = _extract_body(message)
    combined = f"{plain}\n{html}"
    urls = sorted(set(URL_RE.findall(combined)))[:200]
    domains = sorted(
        {
            address.rsplit("@", 1)[1]
            for address in [*senders, *recipients, *reply_to]
            if "@" in address
        }
        | {
            urlparse(url).hostname.casefold()
            for url in urls
            if urlparse(url).hostname
        }
    )

    attachments = []
    for part in message.iter_attachments():
        payload = part.get_payload(decode=True) or b""
        attachments.append(
            {
                "filename": part.get_filename(),
                "media_type": part.get_content_type(),
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )

    sender = senders[0] if senders else None
    sender_domain = sender.rsplit("@", 1)[1] if sender and "@" in sender else None
    observables = []
    for address in sorted(set([*senders, *recipients, *reply_to])):
        observables.append({"type": "email", "value": address})
    for domain in domains:
        observables.append({"type": "domain", "value": domain})
    for url in urls:
        observables.append({"type": "url", "value": url})
    for attachment in attachments:
        observables.append({"type": "sha256", "value": attachment["sha256"]})

    return [
        {
            "event_type": "email.message",
            "event_action": "received",
            "event_outcome": "unknown",
            "event_time": event_time,
            "observed_time": event_time,
            "actor": {"email": sender},
            "source": {"email": sender, "domain": sender_domain},
            "destination": {"emails": recipients},
            "observables": observables,
            "payload": {
                "message_id": message.get("Message-ID"),
                "subject": message.get("Subject"),
                "from": senders,
                "to": recipients,
                "reply_to": reply_to,
                "sender_domain": sender_domain,
                "domains": domains,
                "urls": urls,
                "attachments": attachments,
                "authentication_results": message.get("Authentication-Results"),
                "received_headers": message.get_all("Received", []),
                "body_preview": (plain or html)[:4000],
            },
            "quality": {"timestamp_inferred": inferred, "parse_confidence": 0.98},
        }
    ]
