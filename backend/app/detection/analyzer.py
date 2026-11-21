from __future__ import annotations

import re
from dataclasses import dataclass, field
from email import policy
from email.message import Message
from email.parser import Parser
from email.utils import parseaddr
from urllib.parse import urlsplit

MAX_UPLOAD_BYTES = 5_000_000
MAX_RAW_CHARS = 2_000_000
MAX_BODY_CHARS = 4_000
MAX_LINKS = 10

SAFE = "Safe"
SUSPICIOUS = "Suspicious"
LIKELY_PHISHING = "Likely phishing"

FREE_WEBMAIL_RE = re.compile(r"(gmail|yahoo|hotmail|outlook)\.com$")
BAIT_DOMAIN_RE = re.compile(r"(verify|support|secure|billing|tracking|docs|login)")
URGENCY_RE = re.compile(
    r"urgent|immediately|within 24|in 24 hours|suspend|expires? (today|now|tonight)|"
    r"final notice|act now|permanently"
)
CREDENTIAL_RE = re.compile(
    r"password|verify your account|sign in|log in|login|otp|ssn|pin\b"
)
MONEY_RE = re.compile(r"gift card|wire transfer|payment|invoice|fee\b")
GENERIC_GREETING_RE = re.compile(r"dear (customer|user|sir|member)")
RISKY_TEXT_EXT_RE = re.compile(r"\.(exe|js|scr|bat|zip)\b")
SECRECY_RE = re.compile(r"confidential|don't tell|keep this private|secret")
SHORTENER_RE = re.compile(r"bit\.ly|tinyurl|t\.co|goo\.gl")
RAW_IP_RE = re.compile(r"//\d+\.\d+\.\d+\.\d+")
DIGIT_DOMAIN_RE = re.compile(r"\d")
SUFFIX_RE = re.compile(r"\.[a-z.]+$")
ANCHOR_RE = re.compile(
    r"<a\s[^>]*href=[\"']([^\"']+)[\"'][^>]*>([\s\S]*?)</a>", re.IGNORECASE
)
BARE_URL_RE = re.compile(r"https?://[^\s\"'<>)]+", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]*>")
DOMAIN_TOKEN_RE = re.compile(
    r"(?:https?://)?([a-z0-9.-]+\.[a-z]{2,})", re.IGNORECASE
)
FILENAME_RE = re.compile(r"filename\*?=[\"']?([^\"';\r\n]+)", re.IGNORECASE)
RISKY_ATTACHMENT_RE = re.compile(
    r"\.(exe|js|scr|bat|vbs|iso|docm|xlsm|zip)$", re.IGNORECASE
)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    reason: str
    weight: int
    category: str

    def as_dict(self) -> dict[str, str | int]:
        return {
            "rule_id": self.rule_id,
            "reason": self.reason,
            "weight": self.weight,
            "category": self.category,
        }


@dataclass
class Analysis:
    score: int
    label: str
    findings: list[Finding] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)
    what_to_do: list[str] = field(default_factory=list)
    parsed: dict[str, object] = field(default_factory=dict)

    @property
    def rule_ids(self) -> list[str]:
        seen: list[str] = []
        for finding in self.findings:
            if finding.rule_id not in seen:
                seen.append(finding.rule_id)
        return seen

    def as_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "label": self.label,
            "findings": [finding.as_dict() for finding in self.findings],
            "rule_ids": self.rule_ids,
            "links": self.links,
            "what_to_do": self.what_to_do,
            "parsed": self.parsed,
        }


def _domain(address: str) -> str:
    _, email_address = parseaddr(address)
    candidate = email_address or address
    if "@" not in candidate:
        return ""
    return candidate.rsplit("@", 1)[1].strip().lower().strip(".")


def _host(url: str) -> str:
    candidate = (url or "").strip()
    if not candidate:
        return ""
    if candidate.startswith("//"):
        candidate = "http:" + candidate
    if "://" not in candidate:
        candidate = "http://" + candidate
    try:
        return (urlsplit(candidate).hostname or "").lower()
    except ValueError:
        return ""


def _domains_match(first: str, second: str) -> bool:
    if not first or not second:
        return True
    return first.endswith(second) or second.endswith(first)


def _content_findings(
    sender: str, link: str, text: str, org_domain: str
) -> list[Finding]:
    findings: list[Finding] = []
    domain = _domain(sender)
    lowered_text = text.lower()
    lowered_link = (link or "").strip().lower()

    def add(rule_id: str, weight: int, reason: str) -> None:
        findings.append(Finding(rule_id, reason, weight, "content"))

    if domain and org_domain and domain != org_domain:
        add(
            "S-01",
            15,
            f"Sender is outside your organization domain ({org_domain}).",
        )
    if domain and FREE_WEBMAIL_RE.search(domain):
        add("S-02", 15, "Free webmail address used for an official request.")
    if domain and DIGIT_DOMAIN_RE.search(SUFFIX_RE.sub("", domain)):
        add("S-03", 25, "Digit inside the domain name (for example, paypa1).")
    if domain and BAIT_DOMAIN_RE.search(domain):
        add("S-04", 10, "Domain contains common bait words.")

    if lowered_link:
        if lowered_link.startswith("http://"):
            add("S-05", 15, "Link is not encrypted (http, not https).")
        if RAW_IP_RE.search(lowered_link):
            add("S-06", 25, "Link uses a raw IP address.")
        if SHORTENER_RE.search(lowered_link):
            add("S-07", 15, "Shortened link hides the real destination.")
        if "@" in lowered_link:
            add("S-08", 20, "Link contains @, which can hide the real host.")
        link_host = _host(lowered_link)
        if domain and link_host and not _domains_match(link_host, domain):
            add("S-09", 10, "Link domain does not match the sender domain.")

    if URGENCY_RE.search(lowered_text):
        add("S-10", 20, "Urgent or threatening language.")
    if CREDENTIAL_RE.search(lowered_text):
        add("S-11", 20, "Asks for credentials or personal data.")
    if MONEY_RE.search(lowered_text):
        add("S-12", 15, "Requests money or payment.")
    if GENERIC_GREETING_RE.search(lowered_text):
        add("S-13", 10, "Generic greeting instead of your name.")
    if RISKY_TEXT_EXT_RE.search(lowered_text):
        add("S-14", 25, "Risky attachment type mentioned.")
    if SECRECY_RE.search(lowered_text):
        add("S-15", 10, "Secrecy pressure.")

    return findings


def _decode_part(part: Message) -> str:
    try:
        decoder = getattr(part, "get_content", None)
        if callable(decoder):
            content = decoder()
            if isinstance(content, str):
                return content
    except Exception:
        pass
    payload = part.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _is_attachment(part: Message) -> bool:
    return bool(part.get_filename()) or part.get_content_disposition() == "attachment"


def _body_and_links(msg: Message) -> tuple[str, list[list[str]], list[str]]:
    text_chunks: list[str] = []
    anchors: list[list[str]] = []
    attachments: list[str] = []

    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.is_multipart():
            continue
        filename = part.get_filename()
        if filename:
            attachments.append(filename.strip())
            continue
        if part.get_content_maintype() != "text" or _is_attachment(part):
            continue
        decoded = _decode_part(part)
        text_chunks.append(decoded)
        for match in ANCHOR_RE.finditer(decoded):
            anchor_text = TAG_RE.sub("", match.group(2)).strip()
            anchors.append([match.group(1), anchor_text])

    text = "\n".join(text_chunks)
    plain = TAG_RE.sub(" ", text)
    links: list[list[str]] = []
    seen: set[str] = set()
    for href, anchor_text in anchors:
        if href not in seen:
            seen.add(href)
            links.append([href, anchor_text])
    for match in BARE_URL_RE.finditer(plain):
        url = match.group(0)
        if url not in seen:
            seen.add(url)
            links.append([url, ""])
    return text, links, attachments


def _header_findings(msg: Message) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    notes: list[str] = []

    from_header = msg.get("From", "")
    from_address = parseaddr(from_header)[1].lower()
    reply_to = parseaddr(msg.get("Reply-To", ""))[1].lower()
    return_path = parseaddr(msg.get("Return-Path", ""))[1].lower()

    def add(rule_id: str, weight: int, reason: str) -> None:
        findings.append(Finding(rule_id, reason, weight, "header"))

    auth_results = (msg.get("Authentication-Results", "") or "").lower()
    received_spf = (msg.get("Received-SPF", "") or "").lower()

    if not auth_results and not received_spf:
        add(
            "E-01",
            10,
            "No SPF/DKIM/DMARC results in the headers (sender cannot be confirmed).",
        )
    else:
        if re.search(r"spf=(fail|softfail|none)", auth_results) or re.match(
            r"(fail|softfail|none)", received_spf
        ):
            add(
                "E-02",
                20,
                "SPF check failed: the sending server is not authorized for this domain.",
            )
        if re.search(r"dkim=(fail|none)", auth_results):
            add(
                "E-03",
                20,
                "DKIM check failed or missing: the message may be forged or altered.",
            )
        if re.search(r"dmarc=(fail|none)", auth_results):
            add(
                "E-04",
                25,
                "DMARC check failed: the domain owner does not vouch for this email.",
            )

    identity_mismatch: list[str] = []
    if reply_to and _domain(reply_to) != _domain(from_address):
        identity_mismatch.append(
            f"Reply-To domain ({_domain(reply_to)}) differs from the sender domain ({_domain(from_address)})"
        )
    display_name = parseaddr(from_header)[0].strip()
    display_match = DOMAIN_TOKEN_RE.search(display_name)
    if display_match:
        claimed = display_match.group(1).lower()
        if from_address and not _domains_match(claimed, _domain(from_address)):
            identity_mismatch.append(
                f"Display name shows {claimed} but the sender domain is {_domain(from_address)}"
            )
    if identity_mismatch:
        add("E-05", 20, " or ".join(identity_mismatch) + ".")

    if return_path and _domain(return_path) != _domain(from_address):
        add(
            "E-06",
            10,
            f"Return-Path domain ({_domain(return_path)}) differs from the sender domain ({_domain(from_address)}).",
        )

    notes.append(from_address)
    return findings, notes


def _attachment_findings(attachments: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for name in attachments:
        cleaned = name.strip().strip("\"'")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        if RISKY_ATTACHMENT_RE.search(cleaned):
            findings.append(
                Finding(
                    "E-08",
                    f"Risky attachment: {cleaned}.",
                    25,
                    "header",
                )
            )
    return findings


def _link_text_findings(links: list[list[str]]) -> list[Finding]:
    findings: list[Finding] = []
    for href, link_text in links:
        if not link_text:
            continue
        match = DOMAIN_TOKEN_RE.match(link_text.strip())
        if not match:
            continue
        claimed = match.group(1).lower()
        host = _host(href)
        if host and not _domains_match(claimed, host):
            findings.append(
                Finding(
                    "E-07",
                    f"Link text shows {claimed} but goes to {host}.",
                    25,
                    "header",
                )
            )
    return findings


def _label(score: int) -> str:
    if score < 30:
        return SAFE
    if score < 60:
        return SUSPICIOUS
    return LIKELY_PHISHING


def _advice(label: str) -> list[str]:
    if label == LIKELY_PHISHING:
        return [
            "Do not click links, open attachments or reply.",
            "Report it as phishing and then delete it.",
            "If you already clicked or typed a password: change that password now, turn on MFA, and check your mail forwarding rules.",
            "Block the sender address.",
        ]
    if label == SUSPICIOUS:
        return [
            "Do not act on it yet.",
            "Contact the sender through a known phone number or the official website.",
            "Check the link destinations before clicking.",
            "Report it if you are still unsure.",
        ]
    return [
        "No strong red flags found. Still hover over links and keep MFA on.",
    ]


def _build(
    header_findings: list[Finding],
    content_findings: list[Finding],
    links: list[list[str]],
    attachments: list[str],
    parsed: dict[str, object],
) -> Analysis:
    findings = [*header_findings, *content_findings]
    score = min(100, sum(finding.weight for finding in findings))
    label = _label(score)
    link_output = [
        {"host": _host(href) or href[:200], "text": text[:120]}
        for href, text in links[:MAX_LINKS]
    ]
    parsed_output = {
        **parsed,
        "attachments": attachments[:MAX_LINKS],
    }
    return Analysis(
        score=score,
        label=label,
        findings=findings,
        links=link_output,
        what_to_do=_advice(label),
        parsed=parsed_output,
    )


def analyze_paste(
    *,
    sender: str = "",
    subject: str = "",
    body: str = "",
    link: str = "",
    org_domain: str = "",
) -> Analysis:
    org = (org_domain or "").strip().lower().lstrip("@")
    text = f"{subject}\n{body}".strip().lower()[:MAX_BODY_CHARS]
    findings = _content_findings(sender.strip().lower(), link.strip().lower(), text, org)
    return _build(
        [],
        findings,
        [[link.strip(), ""]] if link.strip() else [],
        [],
        {
            "from": parseaddr(sender)[1].lower(),
            "reply_to": "",
            "subject": subject.strip()[:300],
            "attachments": [],
        },
    )


def analyze_eml(raw: str | bytes, *, org_domain: str = "") -> Analysis:
    if isinstance(raw, bytes):
        data = raw[:MAX_RAW_CHARS]
        raw_text = data.decode("utf-8", errors="replace")
    else:
        raw_text = raw[:MAX_RAW_CHARS]

    msg = Parser(policy=policy.default).parsestr(raw_text)
    org = (org_domain or "").strip().lower().lstrip("@")

    header_findings, _ = _header_findings(msg)
    body, links, attachments = _body_and_links(msg)

    raw_attachments = [m.group(1) for m in FILENAME_RE.finditer(raw_text)]
    all_attachments = [*attachments, *raw_attachments]

    from_header = msg.get("From", "")
    from_address = parseaddr(from_header)[1].lower()
    subject = str(msg.get("Subject", "") or "")

    text_for_scan = " ".join(
        [
            subject,
            TAG_RE.sub(" ", body),
            " ".join(all_attachments),
        ]
    ).lower()[:MAX_BODY_CHARS]
    first_link = links[0][0] if links else ""

    content_findings = _content_findings(
        from_address, first_link.lower(), text_for_scan, org
    )
    content_findings.extend(_link_text_findings(links))
    content_findings.extend(_attachment_findings(all_attachments))

    return _build(
        header_findings,
        content_findings,
        links,
        all_attachments,
        {
            "from": from_address,
            "reply_to": parseaddr(msg.get("Reply-To", ""))[1].lower(),
            "subject": subject[:300],
            "attachments": all_attachments[:MAX_LINKS],
        },
    )
