"""Thread-safe structured JSONL audit logging with secret and PII redaction ([REQ-TRL-02])."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_AUDIT_SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"\btrl_[A-Za-z0-9_]+_[A-Za-z0-9\-_]{8,}\b"),
    re.compile(r"\bsk-(?:live|test|proj)?-?[A-Za-z0-9]{12,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"(?:password|passwd|api_key|apikey|client_secret)\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
]
_AUDIT_PAN_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def _luhn_ok(digits: str) -> bool:
    if not 13 <= len(digits) <= 19 or not digits.isdigit():
        return False
    total = 0
    for idx, ch in enumerate(reversed(digits)):
        val = int(ch)
        if idx % 2 == 1:
            val *= 2
            if val > 9:
                val -= 9
        total += val
    return total % 10 == 0


def redact_audit_text(text: str) -> str:
    """Redact credentials, tokens, JWTs, and Luhn-valid PANs from audit strings."""
    cleaned = text
    for pat in _AUDIT_SECRET_PATTERNS:
        cleaned = pat.sub("<REDACTED>", cleaned)

    def _mask_pan(match: re.Match[str]) -> str:
        digits = re.sub(r"[^0-9]", "", match.group(0))
        return "<PAN_REDACTED>" if _luhn_ok(digits) else match.group(0)

    return _AUDIT_PAN_RE.sub(_mask_pan, cleaned)


def hash_payload_sha256(payload: bytes | str) -> str:
    """Return a SHA-256 hex digest of a request/argument payload without storing raw content."""
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    return hashlib.sha256(raw).hexdigest()


class TrellisAuditLogger:
    """Append-only JSONL audit sink for HTTP and MCP requests."""

    def __init__(self, log_path: Path | None = None, max_bytes: int = 5_000_000) -> None:
        self.log_path = log_path.resolve() if log_path is not None else None
        self.max_bytes = int(max_bytes)
        self._lock = threading.Lock()

    def record(
        self,
        *,
        client_ip: str,
        key_id: str | None,
        role: str | None,
        method: str,
        path: str,
        status: int,
        latency_ms: float,
        tool: str | None = None,
        model: str | None = None,
        decision: str | None = None,
        args_sha256: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Persist one redacted JSONL audit entry and return the entry dictionary."""
        entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "client_ip": redact_audit_text(client_ip),
            "key_id": key_id or "anonymous",
            "role": role or "none",
            "method": method,
            "path": redact_audit_text(path),
            "tool": tool,
            "model": model,
            "decision": decision,
            "args_sha256": args_sha256,
            "status": int(status),
            "latency_ms": round(float(latency_ms), 3),
        }
        if note:
            entry["note"] = redact_audit_text(note)

        if self.log_path is None:
            return entry

        line = json.dumps(entry, separators=(",", ":")) + "\n"
        with self._lock:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            if self.max_bytes > 0 and self.log_path.exists():
                try:
                    if self.log_path.stat().st_size >= self.max_bytes:
                        rotated = self.log_path.with_suffix(self.log_path.suffix + ".1")
                        self.log_path.replace(rotated)
                except OSError:
                    pass
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        return entry
