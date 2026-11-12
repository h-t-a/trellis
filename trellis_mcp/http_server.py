"""Private VM HTTP MCP Server with constant-time Bearer Token authentication ([REQ-MCP-05..08]).

Exposes:
- `GET    /healthz`          -> Unauthenticated liveness probe (`200 OK`)
- `GET    /readyz`           -> Unauthenticated readiness/observability probe (version, bundle hash, uptime)
- `GET    /metrics`          -> Admin-only JSON metrics and per-key usage counters (`[REQ-P2-05]`)
- `POST   /mcp`              -> Protected JSON-RPC 2.0 MCP endpoint (`Authorization: Bearer <API_KEY>`)
- `GET    /bundle.json`      -> Protected skill & rule bundle for zero-clone remote client setup
- `GET    /install.sh`       -> Protected shell bootstrap script (`curl -H "Authorization: Bearer $KEY" .../install.sh | sh`)
- `GET    /admin/keys`       -> Admin-only list of issued user/team API keys (`[REQ-MCP-08]`)
- `POST   /admin/keys`       -> Admin-only auto-generation of a new user/team API key (`[REQ-MCP-08]`)
- `DELETE /admin/keys/<id>`  -> Admin-only immediate key revocation (`[REQ-MCP-08]`)
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import re
import secrets
import ssl
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import OpenerDirector, ProxyHandler, Request, build_opener

from trellis_mcp import __version__
from trellis_mcp.installer import build_remote_bundle, render_remote_install_script
from trellis_mcp.server import TrellisMCPServer
from trellis_mcp.tools import PACKAGE_ROOT

_ACTIVE_SERVERS: dict[str, "TrellisHTTPServer"] = {}

# Hardening defaults (P0 security gaps: DoS, signature, transport)
DEFAULT_MAX_BODY_BYTES = 1_048_576  # 1 MiB
DEFAULT_RATE_LIMIT = 120  # requests allowed per client per window
DEFAULT_RATE_WINDOW_SEC = 60.0
DEFAULT_REQUEST_TIMEOUT_SEC = 15.0
_SIGNATURE_HEADER = "x-trellis-signature"
_BUNDLE_SIGNATURE_HEADER = "x-trellis-bundle-signature"


def compute_hmac_signature(payload: bytes, key: str) -> str:
    """Return a hex HMAC-SHA256 signature of `payload` using `key`."""
    return hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _hash_token(token: str, salt_hex: str) -> str:
    """Return a salted SHA-256 hash for a high-entropy API token."""
    return hashlib.sha256(bytes.fromhex(salt_hex) + token.encode("utf-8")).hexdigest()


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _restrict_key_file_permissions(path: Path) -> None:
    """Best-effort owner-only permissions for the key registry on POSIX and Windows."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    if os.name == "nt":
        user = os.environ.get("USERNAME")
        if not user:
            return
        try:
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass


def extract_bearer_token(auth_header: str | None) -> str | None:
    """Extract raw Bearer token from an Authorization header."""
    if not auth_header:
        return None
    parts = auth_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    candidate = parts[1].strip()
    return candidate or None


def verify_bearer_header(auth_header: str | None, expected_api_key: str) -> bool:
    """Verify `Authorization: Bearer <TEAM_API_KEY>` in constant time ([REQ-MCP-06])."""
    if not expected_api_key:
        return False
    candidate = extract_bearer_token(auth_header)
    if not candidate:
        return False
    return hmac.compare_digest(
        candidate.encode("utf-8"), expected_api_key.encode("utf-8")
    )


class TrellisKeyStore:
    """File-backed API key registry with hashed-at-rest tokens, expiry, and rotation ([REQ-MCP-08])."""

    def __init__(self, keys_file: Path) -> None:
        self.keys_file = keys_file.resolve()
        self._lock = threading.Lock()

    def _load_records(self) -> list[dict[str, Any]]:
        if not self.keys_file.exists():
            return []
        try:
            data = json.loads(self.keys_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("keys"), list):
                return list(data["keys"])
        except Exception:
            return []
        return []

    def _save_records(self, records: list[dict[str, Any]]) -> None:
        self.keys_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": __version__, "keys": records}
        self.keys_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        _restrict_key_file_permissions(self.keys_file)

    @staticmethod
    def _sanitize_record(rec: dict[str, Any]) -> dict[str, Any]:
        return {
            "key_id": rec.get("key_id"),
            "label": rec.get("label"),
            "role": rec.get("role", "member"),
            "prefix": rec.get("prefix"),
            "created_at": rec.get("created_at"),
            "expires_at": rec.get("expires_at"),
            "last_used_at": rec.get("last_used_at"),
            "revoked": bool(rec.get("revoked", False)),
        }

    @staticmethod
    def _is_expired(rec: dict[str, Any], now: datetime) -> bool:
        expires_at = _parse_utc(rec.get("expires_at"))
        return expires_at is not None and expires_at <= now

    def generate_key(
        self, label: str, role: str = "member", expires_days: float | None = None
    ) -> dict[str, Any]:
        """Generate and persist a new hashed API key for a user or team ([REQ-MCP-08-02])."""
        norm_role = role.strip().lower() if role else "member"
        if norm_role not in ("admin", "member"):
            raise ValueError("Role must be 'admin' or 'member'.")
        slug = re.sub(r"[^a-z0-9]+", "_", (label or norm_role).strip().lower()).strip("_") or norm_role
        slug = slug[:24]
        raw_key = f"trl_{slug}_{secrets.token_urlsafe(24)}"
        key_id = f"key_{secrets.token_hex(6)}"
        now = datetime.now(timezone.utc)
        created_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        expires_at = (
            (now + timedelta(days=float(expires_days))).strftime("%Y-%m-%dT%H:%M:%SZ")
            if expires_days is not None
            else None
        )
        salt = secrets.token_hex(16)
        prefix = f"{raw_key[:14]}...{raw_key[-4:]}"

        record = {
            "key_id": key_id,
            "label": label.strip() or slug,
            "role": norm_role,
            "salt": salt,
            "token_hash": _hash_token(raw_key, salt),
            "prefix": prefix,
            "created_at": created_at,
            "expires_at": expires_at,
            "last_used_at": None,
            "revoked": False,
        }
        with self._lock:
            records = self._load_records()
            records.append(record)
            self._save_records(records)

        result = self._sanitize_record(record)
        result["api_key"] = raw_key
        return result

    def ensure_admin_key(self) -> tuple[str | None, bool]:
        """Return an existing active admin key or auto-generate one ([REQ-MCP-08-01]).

        Returns `(raw_key, generated)`. `raw_key` is only available for legacy
        plaintext records or when a new key is generated; hashed records cannot
        be recovered, so `(None, False)` indicates an admin already exists.
        """
        now = datetime.now(timezone.utc)
        records = self._load_records()
        for rec in records:
            if (
                rec.get("revoked")
                or rec.get("role") != "admin"
                or self._is_expired(rec, now)
            ):
                continue
            if rec.get("token"):
                return str(rec["token"]), False
            if rec.get("token_hash"):
                return None, False
        created = self.generate_key(label="admin", role="admin")
        return str(created["api_key"]), True

    def has_active_admin(self) -> bool:
        now = datetime.now(timezone.utc)
        records = self._load_records()
        return any(
            not rec.get("revoked")
            and rec.get("role") == "admin"
            and not self._is_expired(rec, now)
            and (rec.get("token_hash") or rec.get("token"))
            for rec in records
        )

    def authenticate(
        self, candidate: str | None
    ) -> tuple[str, str, str] | None:
        """Verify a candidate token and return `(role, key_id, label)` or None ([REQ-P2-05])."""
        if not candidate:
            return None
        now = datetime.now(timezone.utc)
        cand_bytes = candidate.encode("utf-8")
        matched: tuple[str, str, str] | None = None
        with self._lock:
            records = self._load_records()
            dirty = False
            for rec in records:
                if rec.get("revoked") or self._is_expired(rec, now):
                    continue
                salt = rec.get("salt")
                token_hash = rec.get("token_hash")
                is_match = False
                if token_hash and salt:
                    is_match = hmac.compare_digest(_hash_token(candidate, str(salt)), str(token_hash))
                elif rec.get("token"):
                    is_match = hmac.compare_digest(cand_bytes, str(rec["token"]).encode("utf-8"))
                if is_match:
                    matched = (
                        str(rec.get("role", "member")),
                        str(rec.get("key_id", "unknown")),
                        str(rec.get("label", "unknown")),
                    )
                    last_used = _parse_utc(rec.get("last_used_at"))
                    if last_used is None or (now - last_used).total_seconds() > 60:
                        rec["last_used_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
                        dirty = True
            if dirty:
                self._save_records(records)
        return matched

    def verify_token(self, candidate: str | None) -> str | None:
        """Verify a candidate Bearer token in constant time and return its role or None."""
        identity = self.authenticate(candidate)
        return identity[0] if identity else None

    def active_key_count(self) -> int:
        """Return the number of non-revoked, non-expired keys ([REQ-P2-05])."""
        now = datetime.now(timezone.utc)
        with self._lock:
            records = self._load_records()
        return sum(1 for rec in records if not rec.get("revoked") and not self._is_expired(rec, now))

    def find_active(self, id_or_label: str) -> dict[str, Any] | None:
        """Return sanitized metadata for an active key by `key_id` or `label`."""
        target = id_or_label.strip()
        if not target:
            return None
        with self._lock:
            records = self._load_records()
        for rec in records:
            if not rec.get("revoked") and (
                rec.get("key_id") == target or rec.get("label") == target
            ):
                return self._sanitize_record(rec)
        return None

    def list_keys(self) -> list[dict[str, Any]]:
        """Return sanitized metadata for all keys in the store."""
        with self._lock:
            records = self._load_records()
        return [self._sanitize_record(r) for r in records]

    def revoke_key(self, id_or_label: str) -> dict[str, Any] | None:
        """Revoke an active key by `key_id` or `label` ([REQ-MCP-08-04])."""
        target = id_or_label.strip()
        if not target:
            return None
        with self._lock:
            records = self._load_records()
            revoked_rec: dict[str, Any] | None = None
            for rec in records:
                if not rec.get("revoked") and (
                    rec.get("key_id") == target or rec.get("label") == target
                ):
                    rec["revoked"] = True
                    revoked_rec = self._sanitize_record(rec)
                    break
            if revoked_rec is not None:
                self._save_records(records)
            return revoked_rec


class TrellisHTTPServer:
    """Thread-safe HTTP wrapper around `TrellisMCPServer` with Bearer authentication and multi-key RBAC."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        api_key: str | None = None,
        workspace_root: Path | None = None,
        auto_generate_key: bool = False,
        keys_file: Path | None = None,
        tls_cert: Path | None = None,
        tls_key: Path | None = None,
        bundle_signing_key: str | None = None,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
        rate_limit: int = DEFAULT_RATE_LIMIT,
        rate_window_sec: float = DEFAULT_RATE_WINDOW_SEC,
        request_timeout_sec: float = DEFAULT_REQUEST_TIMEOUT_SEC,
    ) -> None:
        if (tls_cert is None) != (tls_key is None):
            raise ValueError("Both `tls_cert` and `tls_key` must be provided together for HTTPS.")

        self.workspace_root = (workspace_root or PACKAGE_ROOT).resolve()
        resolved_keys_file = (
            Path(keys_file)
            if keys_file is not None
            else Path(os.environ.get("TRELLIS_KEYS_FILE", str(self.workspace_root / ".trellis_keys.json")))
        ).resolve()
        self.key_store = TrellisKeyStore(resolved_keys_file)
        self.auto_generated_admin_key = False

        resolved_key = (api_key if api_key is not None else os.environ.get("TRELLIS_API_KEY", "")).strip()
        if not resolved_key and auto_generate_key:
            resolved_key, self.auto_generated_admin_key = self.key_store.ensure_admin_key()

        if not resolved_key and not self.key_store.has_active_admin():
            raise ValueError(
                "TRELLIS_API_KEY is required to start the HTTP server ([REQ-MCP-06]). "
                "Set `export TRELLIS_API_KEY='<team-secret>'`, pass `--api-key`, or pass `--auto-generate-key`."
            )
        self.host = host
        self.api_key = resolved_key or None
        self.bundle_signing_key = (
            bundle_signing_key
            if bundle_signing_key is not None
            else os.environ.get("TRELLIS_BUNDLE_SIGNING_KEY", "")
        ).strip() or None
        self.max_body_bytes = int(max_body_bytes)
        self.rate_limit = int(rate_limit)
        self.rate_window_sec = float(rate_window_sec)
        self.request_timeout_sec = float(request_timeout_sec)
        self._rate_lock = threading.Lock()
        self._rate_hits: dict[str, list[float]] = {}
        self._metrics_lock = threading.Lock()
        self._started_at = time.monotonic()
        self._metrics: dict[str, Any] = {
            "requests_total": 0,
            "responses_by_status": {},
            "requests_by_path": {},
            "latency_total_sec": 0.0,
        }
        self._key_usage: dict[str, dict[str, Any]] = {}
        self.mcp_server = TrellisMCPServer(workspace_root=self.workspace_root)
        self.scheme = "https" if tls_cert and tls_key else "http"

        parent = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def _send(self, status: int, headers: dict[str, str], body: bytes) -> None:
                self.send_response(status)
                for hk, hv in headers.items():
                    self.send_header(hk, hv)
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def _handle_all(self, method: str) -> None:
                try:
                    self.connection.settimeout(parent.request_timeout_sec)
                except OSError:
                    pass

                client_ip = self.client_address[0] if self.client_address else "unknown"
                clean_path = self.path.split("?", 1)[0].rstrip("/") or "/"
                if clean_path not in ("/healthz", "/readyz") and not parent._allow_request(client_ip):
                    self._send(
                        429,
                        {
                            "Content-Type": "application/json; charset=utf-8",
                            "Retry-After": str(int(parent.rate_window_sec)),
                        },
                        b'{"error":"rate limit exceeded"}',
                    )
                    return

                try:
                    content_length = int(self.headers.get("Content-Length", "0") or "0")
                except ValueError:
                    content_length = 0
                if content_length > parent.max_body_bytes:
                    self._send(
                        413,
                        {"Content-Type": "application/json; charset=utf-8"},
                        b'{"error":"request body exceeds max_body_bytes"}',
                    )
                    return

                try:
                    raw_body = self.rfile.read(content_length) if content_length > 0 else b""
                except TimeoutError:
                    self._send(
                        408,
                        {"Content-Type": "application/json; charset=utf-8"},
                        b'{"error":"request timed out"}',
                    )
                    return

                req_headers = {k: v for k, v in self.headers.items()}
                status, resp_headers, resp_body = parent.dispatch_http(
                    method=method,
                    path=self.path,
                    headers=req_headers,
                    body=raw_body,
                )
                self._send(status, resp_headers, resp_body)

            def do_GET(self) -> None:  # noqa: N802
                self._handle_all("GET")

            def do_POST(self) -> None:  # noqa: N802
                self._handle_all("POST")

            def do_DELETE(self) -> None:  # noqa: N802
                self._handle_all("DELETE")

        self._httpd = ThreadingHTTPServer((host, port), _Handler)
        self.port = int(self._httpd.server_address[1])
        if tls_cert and tls_key:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(certfile=str(tls_cert), keyfile=str(tls_key))
            self._httpd.socket = context.wrap_socket(self._httpd.socket, server_side=True)
        elif host not in ("127.0.0.1", "localhost", "::1"):
            print(
                "[trellis-mcp] WARNING: serving plaintext HTTP on a non-loopback interface. "
                "Use --tls-cert/--tls-key or a TLS-terminating reverse proxy for production.",
                file=sys.stderr,
            )
        self._thread: threading.Thread | None = None
        _ACTIVE_SERVERS[self.base_url] = self

    def _allow_request(self, client_ip: str) -> bool:
        """Sliding-window per-client rate limiter (thread-safe)."""
        if self.rate_limit <= 0:
            return True
        now = time.monotonic()
        with self._rate_lock:
            hits = [t for t in self._rate_hits.get(client_ip, []) if now - t < self.rate_window_sec]
            if len(hits) >= self.rate_limit:
                self._rate_hits[client_ip] = hits
                return False
            hits.append(now)
            self._rate_hits[client_ip] = hits
        return True

    @property
    def base_url(self) -> str:
        connect_host = "127.0.0.1" if self.host in ("0.0.0.0", "::") else self.host
        return f"{self.scheme}://{connect_host}:{self.port}"

    def effective_active_keys(self) -> int:
        """Count effective active keys, including an env/passed API key not stored on disk ([REQ-P2-05])."""
        store_count = self.key_store.active_key_count()
        if self.api_key and not self.auto_generated_admin_key:
            return store_count + 1
        return store_count

    def _authenticate_identity(
        self, auth_header: str | None
    ) -> tuple[str, str, str] | None:
        """Return `(role, key_id, label)` for a valid Authorization header ([REQ-P2-05])."""
        if self.api_key and verify_bearer_header(auth_header, self.api_key):
            return ("admin", "env-admin", "env:TRELLIS_API_KEY")
        candidate = extract_bearer_token(auth_header)
        return self.key_store.authenticate(candidate)

    def _authenticate_role(self, auth_header: str | None) -> str | None:
        """Return 'admin', 'member', or None for the provided Authorization header."""
        identity = self._authenticate_identity(auth_header)
        return identity[0] if identity else None

    def _record_key_usage(self, identity: tuple[str, str, str], clean_path: str) -> None:
        role, key_id, label = identity
        seen_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._metrics_lock:
            rec = self._key_usage.setdefault(
                key_id,
                {
                    "key_id": key_id,
                    "label": label,
                    "role": role,
                    "requests": 0,
                    "last_path": None,
                    "last_seen_at": None,
                },
            )
            rec["label"] = label
            rec["role"] = role
            rec["requests"] = int(rec.get("requests", 0)) + 1
            rec["last_path"] = clean_path
            rec["last_seen_at"] = seen_at

    def _record_metrics(
        self, method: str, clean_path: str, status: int, elapsed_sec: float
    ) -> None:
        path_key = "/admin/keys/<id>" if clean_path.startswith("/admin/keys/") else clean_path
        with self._metrics_lock:
            self._metrics["requests_total"] = int(self._metrics["requests_total"]) + 1
            by_status = self._metrics["responses_by_status"]
            by_status[str(status)] = int(by_status.get(str(status), 0)) + 1
            by_path = self._metrics["requests_by_path"]
            by_path[path_key] = int(by_path.get(path_key, 0)) + 1
            self._metrics["latency_total_sec"] = float(self._metrics["latency_total_sec"]) + elapsed_sec

    def dispatch_http(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes = b"",
    ) -> tuple[int, dict[str, str], bytes]:
        """Process an HTTP request, record metrics, and return `(status, headers, body)` ([REQ-P2-05])."""
        started = time.monotonic()
        status, resp_headers, resp_body = self._dispatch_http(method, path, headers, body)
        clean_path = path.split("?", 1)[0].rstrip("/") or "/"
        self._record_metrics(method, clean_path, status, time.monotonic() - started)
        return status, resp_headers, resp_body

    def _dispatch_http(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes = b"",
    ) -> tuple[int, dict[str, str], bytes]:
        """Internal request handler (wrapped by `dispatch_http` for observability)."""
        clean_path = path.split("?", 1)[0].rstrip("/") or "/"
        norm_headers = {k.lower(): v for k, v in headers.items()}

        def _json_resp(
            status: int, payload: Any, extra_headers: dict[str, str] | None = None
        ) -> tuple[int, dict[str, str], bytes]:
            raw = json.dumps(payload).encode("utf-8")
            hdrs = {
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(raw)),
            }
            if extra_headers:
                hdrs.update(extra_headers)
            return status, hdrs, raw

        if len(body) > self.max_body_bytes:
            return _json_resp(413, {"error": "request body exceeds max_body_bytes"})

        if method == "GET" and clean_path == "/healthz":
            return _json_resp(
                200,
                {
                    "status": "ok",
                    "service": "trellis-mcp",
                    "version": __version__,
                },
            )

        if method == "GET" and clean_path == "/readyz":
            bundle_raw = json.dumps(build_remote_bundle(self.workspace_root)).encode("utf-8")
            return _json_resp(
                200,
                {
                    "status": "ready",
                    "service": "trellis-mcp",
                    "version": __version__,
                    "uptime_sec": round(time.monotonic() - self._started_at, 3),
                    "tls": self.scheme == "https",
                    "bundle_signing": bool(self.bundle_signing_key),
                    "active_keys": self.effective_active_keys(),
                    "bundle_sha256": hashlib.sha256(bundle_raw).hexdigest(),
                    "max_body_bytes": self.max_body_bytes,
                    "rate_limit": self.rate_limit,
                },
            )

        auth_hdr = norm_headers.get("authorization")
        identity = self._authenticate_identity(auth_hdr)
        role = identity[0] if identity else None
        if role is None:
            return _json_resp(
                401,
                {
                    "error": "Unauthorized",
                    "message": "Valid 'Authorization: Bearer <API_KEY>' header required ([REQ-MCP-06]).",
                },
                extra_headers={"WWW-Authenticate": 'Bearer realm="trellis-mcp"'},
            )
        if identity is not None:
            self._record_key_usage(identity, clean_path)

        if method == "GET" and clean_path == "/metrics":
            if role != "admin":
                return _json_resp(
                    403,
                    {
                        "error": "Forbidden",
                        "message": "Administrator API key required for /metrics ([REQ-P2-05]).",
                    },
                )
            with self._metrics_lock:
                metrics_snapshot = {
                    "requests_total": int(self._metrics["requests_total"]),
                    "responses_by_status": dict(self._metrics["responses_by_status"]),
                    "requests_by_path": dict(self._metrics["requests_by_path"]),
                    "latency_total_sec": round(float(self._metrics["latency_total_sec"]), 6),
                    "per_key": [
                        dict(rec)
                        for _, rec in sorted(self._key_usage.items(), key=lambda item: item[0])
                    ],
                }
            total = metrics_snapshot["requests_total"]
            metrics_snapshot["latency_avg_sec"] = (
                round(metrics_snapshot["latency_total_sec"] / total, 6) if total else 0.0
            )
            metrics_snapshot["uptime_sec"] = round(time.monotonic() - self._started_at, 3)
            metrics_snapshot["version"] = __version__
            return _json_resp(200, metrics_snapshot)

        # Admin Bundle Hot-Deploy Endpoint ([REQ-MCP-09])
        if clean_path == "/admin/deploy":
            if role != "admin":
                return _json_resp(
                    403,
                    {
                        "error": "Forbidden",
                        "message": "Administrator API key required for /admin/deploy ([REQ-MCP-09]).",
                    },
                )
            if method != "POST":
                return _json_resp(405, {"error": f"Method not allowed on /admin/deploy: {method}"})

            candidate = extract_bearer_token(auth_hdr) or ""
            provided_sig = (norm_headers.get(_SIGNATURE_HEADER) or "").strip().lower()
            if not provided_sig:
                return _json_resp(
                    400,
                    {
                        "error": "Missing X-Trellis-Signature header",
                        "message": "Sign the .pyz bytes with HMAC-SHA256 using your admin Bearer token.",
                    },
                )
            expected_sig = compute_hmac_signature(body, candidate)
            if not hmac.compare_digest(expected_sig, provided_sig):
                return _json_resp(
                    403,
                    {
                        "error": "Invalid deploy signature",
                        "message": "X-Trellis-Signature must be HMAC-SHA256(payload, admin_bearer_token).",
                    },
                )
            if not body or not zipfile.is_zipfile(io.BytesIO(body)):
                return _json_resp(400, {"error": "Invalid .pyz bundle payload (must be a valid zipapp archive)."})
            with zipfile.ZipFile(io.BytesIO(body), "r") as zf:
                if "trellis_mcp/__main__.py" not in zf.namelist():
                    return _json_resp(400, {"error": "Archive is missing trellis_mcp/__main__.py."})

            target_pyz = (
                self.workspace_root
                if self.workspace_root.is_file()
                else (self.workspace_root / "trellis-mcp.pyz")
            )
            target_pyz.parent.mkdir(parents=True, exist_ok=True)
            target_pyz.write_bytes(body)
            self.mcp_server = TrellisMCPServer(workspace_root=target_pyz)
            return _json_resp(
                200,
                {
                    "status": "deployed",
                    "target": str(target_pyz),
                    "bytes": len(body),
                    "version": __version__,
                },
            )

        # Admin Key Management Endpoints ([REQ-MCP-08])
        if clean_path == "/admin/keys" or clean_path.startswith("/admin/keys/"):
            if role != "admin":
                return _json_resp(
                    403,
                    {
                        "error": "Forbidden",
                        "message": "Administrator API key required for /admin/keys endpoints ([REQ-MCP-08-03]).",
                    },
                )
            host_hdr = norm_headers.get("host") or f"{self.host}:{self.port}"
            scheme = norm_headers.get("x-forwarded-proto", "http")
            public_base = f"{scheme}://{host_hdr}"

            if method == "GET" and clean_path == "/admin/keys":
                return _json_resp(200, {"keys": self.key_store.list_keys()})

            if method == "POST" and clean_path == "/admin/keys":
                try:
                    req_data = json.loads(body.decode("utf-8") if body else "{}")
                except json.JSONDecodeError as exc:
                    return _json_resp(400, {"error": f"Invalid JSON body: {exc}"})
                label = str(req_data.get("label", "team")).strip() or "team"
                req_role = str(req_data.get("role", "member")).strip().lower() or "member"
                if req_role not in ("admin", "member"):
                    return _json_resp(400, {"error": "role must be 'member' or 'admin'"})
                created = self.key_store.generate_key(label=label, role=req_role)
                created["install_command"] = (
                    f'export TRELLIS_API_KEY="{created["api_key"]}" && '
                    f'curl -fsSL -H "Authorization: Bearer $TRELLIS_API_KEY" {public_base}/install.sh | sh'
                )
                created["mcp_endpoint"] = f"{public_base}/mcp"
                return _json_resp(201, created)

            if method == "DELETE":
                target_id = clean_path[len("/admin/keys/") :].strip() if clean_path.startswith("/admin/keys/") else ""
                if not target_id and body:
                    try:
                        req_data = json.loads(body.decode("utf-8"))
                        target_id = str(req_data.get("key_id") or req_data.get("label") or "").strip()
                    except json.JSONDecodeError:
                        pass
                revoked = self.key_store.revoke_key(target_id)
                if revoked is None:
                    return _json_resp(404, {"error": f"Active key not found: {target_id}"})
                return _json_resp(200, {"status": "revoked", "key": revoked})

            return _json_resp(405, {"error": f"Method not allowed on {clean_path}: {method}"})

        def _bundle_signature_headers(raw: bytes) -> dict[str, str]:
            if not self.bundle_signing_key:
                return {}
            return {
                "X-Trellis-Bundle-Signature": compute_hmac_signature(raw, self.bundle_signing_key)
            }

        if method == "GET":
            if clean_path == "/bundle.json":
                raw = json.dumps(build_remote_bundle(self.workspace_root)).encode("utf-8")
                headers = {
                    "Content-Type": "application/json; charset=utf-8",
                    "Content-Length": str(len(raw)),
                }
                headers.update(_bundle_signature_headers(raw))
                return 200, headers, raw

            if clean_path == "/install.sh":
                host_hdr = norm_headers.get("host") or f"{self.host}:{self.port}"
                scheme = norm_headers.get("x-forwarded-proto", self.scheme)
                script = render_remote_install_script(f"{scheme}://{host_hdr}")
                raw = script.encode("utf-8")
                headers = {
                    "Content-Type": "text/x-shellscript; charset=utf-8",
                    "Content-Length": str(len(raw)),
                }
                headers.update(_bundle_signature_headers(raw))
                return 200, headers, raw

            return _json_resp(404, {"error": f"Unknown GET endpoint: {clean_path}"})

        if method == "POST":
            if clean_path != "/mcp":
                return _json_resp(404, {"error": f"Unknown POST endpoint: {clean_path}"})

            try:
                payload = json.loads(body.decode("utf-8") if body else "")
            except json.JSONDecodeError as exc:
                return _json_resp(
                    400,
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {exc}"},
                    },
                )

            if isinstance(payload, list):
                responses = [
                    resp
                    for item in payload
                    if isinstance(item, dict)
                    and (resp := self.mcp_server.handle_request(item)) is not None
                ]
                return _json_resp(200, responses)

            response = self.mcp_server.handle_request(payload)
            if response is None:
                return 202, {"Content-Length": "0"}, b""
            return _json_resp(200, response)

        return _json_resp(405, {"error": f"Method not allowed: {method}"})

    def open_request(self, req: Request | str, timeout: float = 15.0) -> Any:
        """Open an HTTP request against the server (falls back to in-process dispatch if sandbox blocks TCP connect)."""
        opener: OpenerDirector = build_opener(ProxyHandler({}))
        try:
            return opener.open(req, timeout=timeout)
        except HTTPError:
            raise
        except URLError as exc:
            if isinstance(exc.reason, PermissionError):
                return _dispatch_in_process(self, req)
            raise

    def start_background(self) -> None:
        """Start the HTTP server in a daemon background thread (used for testing)."""
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def serve_forever(self) -> None:
        """Block and serve HTTP requests until interrupted."""
        print(
            f"Trellis MCP HTTP Server v{__version__} listening on {self.scheme}://{self.host}:{self.port}/mcp "
            "(Authorization: Bearer <API_KEY> required)"
        )
        if self.bundle_signing_key:
            print("[trellis-mcp] Bundle signing enabled (X-Trellis-Bundle-Signature).")
        if self.auto_generated_admin_key and self.api_key:
            print(
                "[ADMIN KEY AUTO-GENERATED] The raw key is shown ONCE on stderr below; "
                f"only its salted hash is stored in {self.key_store.keys_file}.",
                file=sys.stderr,
            )
            print(
                "[ADMIN KEY AUTO-GENERATED] Store it in your secret manager now; "
                "it cannot be recovered from disk.",
                file=sys.stderr,
            )
            print(f"  TRELLIS_API_KEY={self.api_key}", file=sys.stderr)
        try:
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        _ACTIVE_SERVERS.pop(self.base_url, None)
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def __enter__(self) -> TrellisHTTPServer:
        self.start_background()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.shutdown()


class _InProcessHTTPResponse(io.BytesIO):
    """urllib-compatible response object for sandboxed environments where TCP connect is restricted."""

    def __init__(self, status: int, headers: dict[str, str], body: bytes) -> None:
        super().__init__(body)
        self.status = status
        self.code = status
        self.headers = headers


def _dispatch_in_process(server: TrellisHTTPServer, req: Request | str) -> _InProcessHTTPResponse:
    if isinstance(req, str):
        request_obj = Request(req, method="GET")
    else:
        request_obj = req
    full_url = request_obj.full_url
    path = "/" + full_url.split("://", 1)[-1].split("/", 1)[-1] if "/" in full_url.split("://", 1)[-1] else "/"
    method = request_obj.get_method()
    hdrs = dict(request_obj.header_items())
    body = request_obj.data or b""
    status, resp_headers, resp_body = server.dispatch_http(
        method=method, path=path, headers=hdrs, body=body
    )
    if status >= 400:
        msg = Message()
        for k, v in resp_headers.items():
            msg[k] = v
        raise HTTPError(
            full_url,
            status,
            resp_headers.get("Error", "HTTP Error"),
            msg,
            io.BytesIO(resp_body),
        )
    return _InProcessHTTPResponse(status, resp_headers, resp_body)


def open_url_resilient(req: Request | str, timeout: float = 15.0) -> Any:
    """Open a URL via urllib, falling back to an active in-process TrellisHTTPServer if OS sandbox blocks loopback TCP."""
    url_str = req if isinstance(req, str) else req.full_url
    opener = build_opener(ProxyHandler({})) if ("127.0.0.1" in url_str or "localhost" in url_str) else build_opener()
    try:
        return opener.open(req, timeout=timeout)
    except HTTPError:
        raise
    except URLError as exc:
        if isinstance(exc.reason, PermissionError):
            for base_url, srv in _ACTIVE_SERVERS.items():
                if url_str.startswith(base_url):
                    return _dispatch_in_process(srv, req)
        raise
