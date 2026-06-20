import re

PII_PATTERNS = {
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "PHONE": re.compile(r"\b[6-9]\d{9}\b"),
    "IP": re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"),
    "AADHAAR": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "TOKEN": re.compile(r"\b[a-fA-F0-9]{32,}\b"),
    "USER_ID": re.compile(r"\buser_[a-zA-Z0-9]{6,}\b"),
    "SESSION": re.compile(r"\bsession_[a-zA-Z0-9]{8,}\b")
}

def sanitize_text(text: str) -> str:
    """
    Detects and masks common PII in the input text.
    Returns sanitized text safe for agent processing.
    """
    if not text:
        return text

    sanitized = text
    for label, pattern in PII_PATTERNS.items():
        sanitized = pattern.sub(f"[{label}]", sanitized)
    return sanitized
