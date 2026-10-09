import hashlib
import ipaddress
import re
from urllib.parse import urlsplit


RULE_ID_PATTERN = re.compile(r'\[id "(?P<id>\d+)"\]')
SEVERITY_PATTERN = re.compile(r'\[severity "(?P<severity>[^"]+)"\]')
TAG_PATTERN = re.compile(r'\[tag "(?P<tag>[^"]+)"\]')
DATA_PATTERN = re.compile(r'\[data "(?P<data>[^"]+)"\]')
URI_PATTERN = re.compile(r'\[uri "(?P<uri>[^"]+)"\]')
FIELD_PATTERN = re.compile(
    r"(?:within|against variable)[ :]+(?P<field>[A-Z][A-Z0-9_]*(?::[A-Za-z0-9_.-]+)?)",
    re.IGNORECASE,
)
SAFE_FIELD_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*(?::[A-Za-z0-9_.-]+)?$", re.IGNORECASE)
MATCHED_DATA_PATTERN = re.compile(r"Matched Data:\s*(?P<data>.*?)\s+found within", re.IGNORECASE | re.DOTALL)
SENSITIVE_FIELD_PATTERN = re.compile(
    r"(?:password|passwd|pwd|secret|token|authorization|cookie|session|csrf|api[_-]?key)",
    re.IGNORECASE,
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|authorization|cookie|session|csrf|api[_-]?key)"
    r"(\s*[:=]\s*)([^\s,;&]+)"
)


def _details(message):
    details = message.get("details") or {}
    raw = message.get("message") or ""
    rule_id = details.get("ruleId") or details.get("rule_id")
    severity = details.get("severity")
    tags = details.get("tags") or []
    matched = details.get("data") or details.get("match")
    if not rule_id:
        match = RULE_ID_PATTERN.search(raw)
        rule_id = match.group("id") if match else "unknown"
    if not severity:
        match = SEVERITY_PATTERN.search(raw)
        severity = match.group("severity") if match else "unknown"
    if not tags:
        tags = TAG_PATTERN.findall(raw)
    if not matched:
        match = DATA_PATTERN.search(raw)
        matched = match.group("data") if match else ""
    return str(rule_id), str(severity).lower(), [str(tag) for tag in tags], str(matched)


def _attack_type(tags):
    for tag in tags:
        lowered = tag.lower()
        if lowered.startswith("attack-"):
            return lowered.removeprefix("attack-")
    return "policy-violation"


def _matched_field(value):
    value = value.strip()
    if SAFE_FIELD_PATTERN.fullmatch(value):
        return value
    match = FIELD_PATTERN.search(value)
    return match.group("field") if match else "redacted"


def _client_ip(value):
    try:
        return str(ipaddress.ip_address(str(value).strip()))
    except ValueError:
        return "unknown"


def _matched_data(value, field):
    """Keep only the short WAF-matched fragment, never the complete request body."""
    if SENSITIVE_FIELD_PATTERN.search(field):
        return "[redacted]"
    match = MATCHED_DATA_PATTERN.search(value)
    if not match:
        return ""
    fragment = " ".join(match.group("data").split())
    fragment = SENSITIVE_VALUE_PATTERN.sub(r"\1\2[redacted]", fragment)
    return fragment[:300]


def normalize_waf_audit(document):
    """Convert ModSecurity JSON into a compact security event suitable for blocking."""
    transaction = document.get("transaction") or document
    request = transaction.get("request") or {}
    response = transaction.get("response") or {}
    uri = request.get("uri") or transaction.get("request_uri")
    transaction_id = str(transaction.get("unique_id") or transaction.get("id") or "unknown")
    client = _client_ip(transaction.get("client_ip") or "unknown")
    fingerprint = hashlib.sha256(client.encode("utf-8")).hexdigest()[:16]
    events = []
    for message in transaction.get("messages") or []:
        rule_id, severity, tags, matched = _details(message)
        raw_message = message.get("message") or ""
        message_uri = URI_PATTERN.search(raw_message)
        path = urlsplit(uri or (message_uri.group("uri") if message_uri else "/")).path or "/"
        matched_field = _matched_field(matched)
        events.append({
            "event": "waf_detection",
            "schema_version": 1,
            "service": "waf",
            "provider": "owasp-crs",
            "engine": "modsecurity",
            "request_id": transaction_id,
            "method": str(request.get("method") or "unknown"),
            "path": path,
            "status_code": int(response.get("http_code") or 0),
            "rule_id": rule_id,
            "severity": severity,
            "attack_type": _attack_type(tags),
            "action": "blocked" if int(response.get("http_code") or 0) == 403 else "detected",
            "matched_field": matched_field,
            "matched_data": _matched_data(matched, matched_field),
            "client_ip": client,
            "client_fingerprint": fingerprint,
        })
    return events
