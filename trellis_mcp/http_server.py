"""Private VM HTTP MCP Server with constant-time Bearer Token authentication ([REQ-MCP-05..08]).

Exposes:
- `GET    /healthz`          -> Unauthenticated liveness probe (`200 OK`)
- `GET    /readyz`           -> Unauthenticated readiness/observability probe (version, bundle hash, uptime)
- `GET    /favicon.ico`      -> Unauthenticated dashboard favicon
- `GET    /metrics`          -> Admin-only JSON metrics and per-key usage counters (`[REQ-P2-05]`)
- `POST   /mcp`              -> Protected JSON-RPC 2.0 MCP endpoint (`Authorization: Bearer <API_KEY>`)
- `GET    /bundle.json`      -> Protected skill & rule bundle for zero-clone remote client setup
- `GET    /install.sh`       -> Protected shell bootstrap script (`curl -H "Authorization: Bearer $KEY" .../install.sh | sh`)
- `GET    /admin/keys`       -> Admin-only list of issued user/team API keys (`[REQ-MCP-08]`)
- `POST   /admin/keys`       -> Admin-only auto-generation of a new user/team API key (`[REQ-MCP-08]`)
- `PATCH  /admin/keys/<id>`  -> Admin-only update of a key's label or role
- `DELETE /admin/keys/<id>`  -> Admin-only immediate key revocation (`[REQ-MCP-08]`)
- `GET    /admin/dashboard`  -> Unauthenticated HTML shell for the admin key-management dashboard (`[REQ-P3-02]`)
- `POST   /admin/session`    -> Exchange an admin API key for a short-lived HttpOnly session cookie (`[REQ-P3-06]`)
- `GET    /admin/session`    -> Return the current browser session status
- `DELETE /admin/session`    -> Revoke and clear the browser session
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone
from email.message import Message
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import OpenerDirector, ProxyHandler, Request, build_opener

from trellis_mcp import __version__
from trellis_mcp.audit import TrellisAuditLogger, hash_payload_sha256
from trellis_mcp.branding import FAVICON_ICO
from trellis_mcp.installer import build_remote_bundle, render_remote_install_script
from trellis_mcp.pipeline import build_a2a_agent_card
from trellis_mcp.server import SUPPORTED_PROTOCOL_VERSIONS, TrellisMCPServer
from trellis_mcp.tools import PACKAGE_ROOT
from trellis_mcp.ui import DASHBOARD_HTML

_ACTIVE_SERVERS: dict[str, "TrellisHTTPServer"] = {}

# Hardening defaults (P0 security gaps: DoS, signature, transport)
DEFAULT_MAX_BODY_BYTES = 1_048_576  # 1 MiB
DEFAULT_RATE_LIMIT = 120  # requests allowed per client per window
DEFAULT_RATE_WINDOW_SEC = 60.0
DEFAULT_REQUEST_TIMEOUT_SEC = 15.0
DEFAULT_SESSION_TTL_SEC = 900  # 15 minutes
DEFAULT_MAX_TRACKED_IPS = 2048
_SIGNATURE_HEADER = "x-trellis-signature"
_BUNDLE_SIGNATURE_HEADER = "x-trellis-bundle-signature"
_CSRF_HEADER = "x-trellis-csrf"
_SESSION_VERSION = "v1"
_SESSION_COOKIE_SECURE = "__Host-trellis_admin"
_SESSION_COOKIE_DEV = "trellis_admin_session"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})
_SAFE_URL_RE = re.compile(r"^https?://[A-Za-z0-9._:\-\[\]]+(?:/[A-Za-z0-9._/\-]*)?$")
_VERSION_ASSIGN_RE = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')


def _is_loopback_host(host: str) -> bool:
    return host.strip().lower() in _LOOPBACK_HOSTS


def _strip_host_port(host_header: str) -> str:
    raw = host_header.strip().lower()
    if not raw:
        return ""
    if raw.startswith("["):
        end = raw.find("]")
        return raw[: end + 1] if end != -1 else raw
    return raw.split(":", 1)[0]


def _parse_semver(version_str: str) -> tuple[int, ...]:
    nums = [int(p) for p in re.findall(r"\d+", version_str)]
    return tuple(nums) if nums else (0, 0, 0)


def _extract_pyz_version(archive_bytes: bytes) -> str | None:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as zf:
            if "trellis_mcp/__init__.py" not in zf.namelist():
                return None
            init_src = zf.read("trellis_mcp/__init__.py").decode("utf-8", errors="ignore")
    except (zipfile.BadZipFile, OSError):
        return None
    m = _VERSION_ASSIGN_RE.search(init_src)
    return m.group(1).strip() if m else None

# Default read-only tool allowlist for `member` API keys ([REQ-TRL-18]).
# Excludes write-capable and server-filesystem-scanning tools (handoff, doctor, scan, mcp_registry, analytics).
DEFAULT_MEMBER_SCOPES: tuple[str, ...] = (
    "trellis_get_standard",
    "trellis_rca",
    "trellis_spec",
    "trellis_enhance",
    "trellis_budget",
    "trellis_review",
    "trellis_test",
    "trellis_classify",
    "trellis_verify",
    "trellis_search_knowledge",
    "trellis_route_model",
    "trellis_pipeline",
    "trellis_synthesize",
)


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
    """File-backed API key registry with hashed-at-rest tokens, expiry, scopes, caching, and rotation ([REQ-MCP-08])."""

    def __init__(self, keys_file: Path) -> None:
        self.keys_file = keys_file.resolve()
        self._lock = threading.Lock()
        self._cache_sig: tuple[int, int] | None = None
        self._cached_records: list[dict[str, Any]] = []

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

    def _load_records_cached(self) -> list[dict[str, Any]]:
        """Return cached key records when file mtime_ns and size are unchanged ([REQ-TRL-06])."""
        try:
            st = self.keys_file.stat()
            sig = (int(st.st_mtime_ns), int(st.st_size))
        except OSError:
            self._cache_sig = None
            self._cached_records = []
            return []
        if self._cache_sig == sig:
            return self._cached_records
        records = self._load_records()
        self._cache_sig = sig
        self._cached_records = records
        return records

    def _save_records(self, records: list[dict[str, Any]], *, apply_acl: bool = True) -> None:
        existed = self.keys_file.exists()
        self.keys_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": __version__, "keys": records}
        self.keys_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        if apply_acl or not existed:
            _restrict_key_file_permissions(self.keys_file)
        try:
            st = self.keys_file.stat()
            self._cache_sig = (int(st.st_mtime_ns), int(st.st_size))
            self._cached_records = list(records)
        except OSError:
            self._cache_sig = None

    @staticmethod
    def _sanitize_record(rec: dict[str, Any]) -> dict[str, Any]:
        return {
            "key_id": rec.get("key_id"),
            "label": rec.get("label"),
            "role": rec.get("role", "member"),
            "scopes": rec.get("scopes"),
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
        self,
        label: str,
        role: str = "member",
        expires_days: float | None = None,
        scopes: list[str] | None = None,
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
        if scopes is not None:
            cleaned_scopes = [str(s).strip() for s in scopes if str(s).strip()]
            norm_scopes: list[str] | None = (
                cleaned_scopes if cleaned_scopes else (list(DEFAULT_MEMBER_SCOPES) if norm_role == "member" else None)
            )
        elif norm_role == "member":
            norm_scopes = list(DEFAULT_MEMBER_SCOPES)
        else:
            norm_scopes = None

        record = {
            "key_id": key_id,
            "label": label.strip() or slug,
            "role": norm_role,
            "scopes": norm_scopes,
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

    def update_key(
        self,
        id_or_label: str,
        label: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any] | None:
        """Update the label or role of an existing key."""
        norm_role = role.strip().lower() if role is not None else None
        if norm_role is not None and norm_role not in ("admin", "member"):
            raise ValueError("Role must be 'admin' or 'member'.")
        target = str(id_or_label or "").strip()
        if not target:
            return None
        with self._lock:
            records = self._load_records()
            for rec in records:
                if rec.get("key_id") != target and rec.get("label") != target:
                    continue
                if label is not None:
                    new_label = label.strip()
                    if not new_label:
                        raise ValueError("Label cannot be empty.")
                    if len(new_label) > 64:
                        raise ValueError("Label must be 64 characters or fewer.")
                    rec["label"] = new_label
                if norm_role is not None:
                    rec["role"] = norm_role
                    if norm_role == "member" and not rec.get("scopes"):
                        rec["scopes"] = list(DEFAULT_MEMBER_SCOPES)
                self._save_records(records)
                return self._sanitize_record(rec)
        return None

    def ensure_admin_key(self) -> tuple[str | None, bool]:
        """Return an existing active admin key or auto-generate one ([REQ-MCP-08-01]).

        Returns `(raw_key, generated)`. Hashed records cannot be recovered,
        so `(None, False)` indicates an active hashed admin already exists.
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
            if rec.get("token_hash") and rec.get("salt"):
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
            and bool(rec.get("token_hash") and rec.get("salt"))
            for rec in records
        )

    def migrate_legacy_plaintext_keys(self) -> int:
        """Hash any legacy plaintext `token` entries in place and strip raw tokens ([REQ-TRL-23])."""
        migrated = 0
        with self._lock:
            records = self._load_records()
            for rec in records:
                raw_tok = rec.get("token")
                if not raw_tok:
                    continue
                salt = secrets.token_hex(16)
                rec["salt"] = salt
                rec["token_hash"] = _hash_token(str(raw_tok), salt)
                rec.pop("token", None)
                if str(rec.get("role", "member")).lower() == "member" and not rec.get("scopes"):
                    rec["scopes"] = list(DEFAULT_MEMBER_SCOPES)
                migrated += 1
            if migrated:
                self._save_records(records)
        return migrated

    def authenticate(
        self, candidate: str | None
    ) -> tuple[str, str, str] | None:
        """Verify a candidate token against salted SHA-256 hashes only ([REQ-P2-05, REQ-TRL-23])."""
        if not candidate:
            return None
        now = datetime.now(timezone.utc)
        matched: tuple[str, str, str] | None = None
        with self._lock:
            records = self._load_records_cached()
            dirty = False
            for rec in records:
                if rec.get("revoked") or self._is_expired(rec, now):
                    continue
                salt = rec.get("salt")
                token_hash = rec.get("token_hash")
                if not (token_hash and salt):
                    continue
                is_match = hmac.compare_digest(_hash_token(candidate, str(salt)), str(token_hash))
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
                self._save_records(records, apply_acl=False)
        return matched

    def get_scopes(self, key_id: str) -> list[str] | None:
        """Return allowed tool scopes for `key_id`, defaulting member keys to read-only ([REQ-TRL-03, REQ-TRL-18])."""
        with self._lock:
            for rec in self._load_records_cached():
                if rec.get("key_id") == key_id:
                    scopes = rec.get("scopes")
                    if isinstance(scopes, list) and scopes:
                        return list(scopes)
                    if str(rec.get("role", "member")).lower() == "member":
                        return list(DEFAULT_MEMBER_SCOPES)
                    return None
        return None

    def verify_token(self, candidate: str | None) -> str | None:
        """Verify a candidate Bearer token in constant time and return its role or None."""
        identity = self.authenticate(candidate)
        return identity[0] if identity else None

    def active_key_count(self) -> int:
        """Return the number of non-revoked, non-expired keys ([REQ-P2-05])."""
        now = datetime.now(timezone.utc)
        with self._lock:
            records = self._load_records_cached()
        return sum(1 for rec in records if not rec.get("revoked") and not self._is_expired(rec, now))

    def find_active(self, id_or_label: str) -> dict[str, Any] | None:
        """Return sanitized metadata for an active key by `key_id` or `label`."""
        target = id_or_label.strip()
        if not target:
            return None
        with self._lock:
            records = self._load_records_cached()
        for rec in records:
            if not rec.get("revoked") and (
                rec.get("key_id") == target or rec.get("label") == target
            ):
                return self._sanitize_record(rec)
        return None

    def list_keys(self) -> list[dict[str, Any]]:
        """Return sanitized metadata for all keys in the store."""
        with self._lock:
            records = self._load_records_cached()
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
        host: str = "127.0.0.1",
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
        session_ttl_sec: float | None = None,
        session_secret: str | None = None,
        secure_cookies: bool | None = None,
        allowed_origins: list[str] | tuple[str, ...] | None = None,
        audit_log: Path | None = None,
        auth_failure_limit: int = 5,
        auth_lockout_sec: float = 60.0,
        enable_remote_deploy: bool = False,
        deploy_signing_key: str | None = None,
        insecure_http: bool = False,
        public_url: str | None = None,
        allowed_hosts: list[str] | tuple[str, ...] | None = None,
        trusted_proxies: list[str] | tuple[str, ...] | None = None,
        max_tracked_ips: int = DEFAULT_MAX_TRACKED_IPS,
    ) -> None:
        if (tls_cert is None) != (tls_key is None):
            raise ValueError("Both `tls_cert` and `tls_key` must be provided together for HTTPS.")
        if not _is_loopback_host(host) and not (tls_cert and tls_key) and not insecure_http:
            raise ValueError(
                "Refusing to bind non-loopback host without TLS ([REQ-TRL-21]). "
                "Pass --tls-cert and --tls-key, or pass --insecure-http explicitly."
            )

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
        self.enable_remote_deploy = bool(enable_remote_deploy)
        self.deploy_signing_key = (
            deploy_signing_key
            if deploy_signing_key is not None
            else os.environ.get("TRELLIS_DEPLOY_SIGNING_KEY", "")
        ).strip() or None
        self.insecure_http = bool(insecure_http)
        raw_public_url = (
            public_url if public_url is not None else os.environ.get("TRELLIS_PUBLIC_URL", "")
        ).strip().rstrip("/")
        if raw_public_url and not _SAFE_URL_RE.match(raw_public_url):
            raise ValueError(f"Invalid public_url format: {raw_public_url!r}")
        self.public_url: str | None = raw_public_url or None
        env_proxies = [
            p.strip() for p in os.environ.get("TRELLIS_TRUSTED_PROXIES", "").split(",") if p.strip()
        ]
        self.trusted_proxies: set[str] = (
            {str(p).strip() for p in trusted_proxies if str(p).strip()}
            if trusted_proxies is not None
            else set(env_proxies)
        )
        env_hosts = [
            _strip_host_port(h)
            for h in os.environ.get("TRELLIS_ALLOWED_HOSTS", "").split(",")
            if h.strip()
        ]
        host_allow: set[str] = set(_LOOPBACK_HOSTS) if _is_loopback_host(host) else set()
        if host.strip() and host.strip() not in ("0.0.0.0", "::"):
            host_allow.add(_strip_host_port(host))
        if self.public_url:
            parsed_pub = urlparse(self.public_url)
            if parsed_pub.hostname:
                host_allow.add(parsed_pub.hostname.lower())
        if allowed_hosts is not None:
            host_allow.update(_strip_host_port(str(h)) for h in allowed_hosts if str(h).strip())
        host_allow.update(h for h in env_hosts if h)
        self.allowed_hosts: set[str] = {h for h in host_allow if h}
        self.max_tracked_ips = max(1, int(max_tracked_ips))
        self.max_body_bytes = int(max_body_bytes)
        self.rate_limit = int(rate_limit)
        self.rate_window_sec = float(rate_window_sec)
        self.request_timeout_sec = float(request_timeout_sec)
        self.scheme = "https" if tls_cert and tls_key else "http"
        ttl = (
            session_ttl_sec
            if session_ttl_sec is not None
            else float(os.environ.get("TRELLIS_SESSION_TTL_SEC", DEFAULT_SESSION_TTL_SEC))
        )
        self.session_ttl_sec = max(60, int(ttl))
        self.session_secret = (
            session_secret
            if session_secret is not None
            else os.environ.get("TRELLIS_SESSION_SECRET", "")
        ).strip() or secrets.token_hex(32)
        env_secure = os.environ.get("TRELLIS_SECURE_COOKIES", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        self.secure_cookies = (
            bool(secure_cookies)
            if secure_cookies is not None
            else (self.scheme == "https" or env_secure)
        )
        self.session_cookie_name = (
            _SESSION_COOKIE_SECURE if self.secure_cookies else _SESSION_COOKIE_DEV
        )
        self._rate_lock = threading.Lock()
        self._rate_hits: dict[str, list[float]] = {}
        self._auth_fail_lock = threading.Lock()
        self._auth_failures: dict[str, list[float]] = {}
        self._auth_lockout_until: dict[str, float] = {}
        self.auth_failure_limit = int(auth_failure_limit)
        self.auth_lockout_sec = float(auth_lockout_sec)
        env_origins = [
            o.strip().rstrip("/")
            for o in os.environ.get("TRELLIS_ALLOWED_ORIGINS", "").split(",")
            if o.strip()
        ]
        self.allowed_origins: set[str] | None = (
            {str(o).strip().rstrip("/") for o in allowed_origins if str(o).strip()}
            if allowed_origins is not None
            else (set(env_origins) if env_origins else None)
        )
        resolved_audit_path: Path | None = audit_log
        if resolved_audit_path is None and os.environ.get("TRELLIS_AUDIT_LOG"):
            resolved_audit_path = Path(os.environ["TRELLIS_AUDIT_LOG"])
        self.audit_logger = TrellisAuditLogger(resolved_audit_path)
        self._bundle_cache_lock = threading.Lock()
        self._bundle_digest_cache: str | None = None
        self._bundle_digest_ts: float = 0.0
        self._bundle_digest_ttl: float = 5.0
        self._sessions_lock = threading.Lock()
        self._sessions: dict[str, int] = {}
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

                peer_ip = self.client_address[0] if self.client_address else "unknown"
                req_headers = {k: v for k, v in self.headers.items()}
                norm_hdrs = {k.lower(): v for k, v in req_headers.items()}
                client_ip = parent._resolve_client_ip(peer_ip, norm_hdrs)
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

                status, resp_headers, resp_body = parent.dispatch_http(
                    method=method,
                    path=self.path,
                    headers=req_headers,
                    body=raw_body,
                    client_ip=peer_ip,
                )
                self._send(status, resp_headers, resp_body)

            def do_GET(self) -> None:  # noqa: N802
                self._handle_all("GET")

            def do_POST(self) -> None:  # noqa: N802
                self._handle_all("POST")

            def do_PATCH(self) -> None:  # noqa: N802
                self._handle_all("PATCH")

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

    def _resolve_client_ip(self, peer_ip: str, norm_headers: dict[str, str]) -> str:
        """Resolve end-client IP, honoring X-Forwarded-For only from configured trusted proxies ([REQ-TRL-23])."""
        clean_peer = (peer_ip or "unknown").strip()
        if clean_peer not in self.trusted_proxies:
            return clean_peer
        xff = (norm_headers.get("x-forwarded-for") or "").strip()
        if not xff:
            return clean_peer
        hops = [h.strip() for h in xff.split(",") if h.strip()]
        for hop in reversed(hops):
            if hop not in self.trusted_proxies:
                return hop
        return hops[0] if hops else clean_peer

    def _evict_rate_hits_locked(self, now: float) -> None:
        cutoff = now - self.rate_window_sec
        stale = [
            ip for ip, stamps in self._rate_hits.items()
            if not stamps or stamps[-1] < cutoff
        ]
        for ip in stale:
            self._rate_hits.pop(ip, None)
        if len(self._rate_hits) > self.max_tracked_ips:
            # Drop oldest-activity IPs to guarantee bounded memory under IP spray
            ordered = sorted(
                self._rate_hits.items(),
                key=lambda item: item[1][-1] if item[1] else 0.0,
            )
            excess = len(self._rate_hits) - self.max_tracked_ips
            for ip, _ in ordered[:excess]:
                self._rate_hits.pop(ip, None)

    def _allow_request(self, client_ip: str) -> bool:
        """Sliding-window per-client rate limiter with bounded TTL eviction ([REQ-TRL-23])."""
        if self.rate_limit <= 0:
            return True
        now = time.monotonic()
        with self._rate_lock:
            self._evict_rate_hits_locked(now)
            hits = [t for t in self._rate_hits.get(client_ip, []) if now - t < self.rate_window_sec]
            if len(hits) >= self.rate_limit:
                self._rate_hits[client_ip] = hits
                return False
            hits.append(now)
            self._rate_hits[client_ip] = hits
            if len(self._rate_hits) > self.max_tracked_ips:
                self._evict_rate_hits_locked(now)
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

    def _authenticate_token(self, candidate: str | None) -> tuple[str, str, str] | None:
        """Validate a raw API key and return `(role, key_id, label)`."""
        if not candidate:
            return None
        if self.api_key and hmac.compare_digest(
            candidate.encode("utf-8"), self.api_key.encode("utf-8")
        ):
            return ("admin", "env-admin", "env:TRELLIS_API_KEY")
        return self.key_store.authenticate(candidate)

    def _authenticate_request(
        self,
        auth_header: str | None,
        cookie_header: str | None = None,
        allow_cookie: bool = False,
    ) -> tuple[tuple[str, str, str] | None, str | None]:
        """Return `((role, key_id, label), source)` for Bearer or browser-session auth."""
        identity = self._authenticate_token(extract_bearer_token(auth_header))
        if identity is not None:
            return identity, "bearer"
        if allow_cookie:
            session = self._read_session(cookie_header)
            if session is not None:
                return session[0], "cookie"
        return None, None

    def _authenticate_identity(
        self, auth_header: str | None, cookie_header: str | None = None
    ) -> tuple[str, str, str] | None:
        """Return `(role, key_id, label)` for a valid Authorization header ([REQ-P2-05])."""
        identity, _ = self._authenticate_request(
            auth_header, cookie_header, allow_cookie=False
        )
        return identity

    def _authenticate_role(self, auth_header: str | None) -> str | None:
        """Return 'admin', 'member', or None for the provided Authorization header."""
        identity = self._authenticate_identity(auth_header)
        return identity[0] if identity else None

    @staticmethod
    def _b64url_encode(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _b64url_decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)

    @staticmethod
    def _cookie_value(cookie_header: str | None, name: str) -> str | None:
        if not cookie_header:
            return None
        try:
            jar = SimpleCookie()
            jar.load(cookie_header)
        except CookieError:
            return None
        morsel = jar.get(name)
        return morsel.value if morsel is not None else None

    def _create_session_token(
        self, identity: tuple[str, str, str]
    ) -> tuple[str, int]:
        now = int(time.time())
        expires = now + self.session_ttl_sec
        session_id = secrets.token_hex(16)
        payload = {
            "sub": identity[1],
            "iat": now,
            "exp": expires,
            "jti": session_id,
            "nonce": secrets.token_hex(8),
        }
        encoded = self._b64url_encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signing_input = f"{_SESSION_VERSION}.{encoded}"
        signature = hmac.new(
            self.session_secret.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        with self._sessions_lock:
            self._sessions = {
                sid: exp for sid, exp in self._sessions.items() if exp > now
            }
            self._sessions[session_id] = expires
        return f"{signing_input}.{signature}", expires

    def _session_payload(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != _SESSION_VERSION:
            return None
        signing_input = f"{parts[0]}.{parts[1]}"
        expected = hmac.new(
            self.session_secret.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, parts[2]):
            return None
        try:
            payload = json.loads(self._b64url_decode(parts[1]).decode("utf-8"))
        except (ValueError, TypeError, UnicodeDecodeError, binascii.Error):
            return None
        return payload if isinstance(payload, dict) else None

    def _revoke_session_token(self, token: str | None) -> None:
        payload = self._session_payload(token)
        if not payload:
            return
        session_id = str(payload.get("jti", "")).strip()
        if not session_id:
            return
        with self._sessions_lock:
            self._sessions.pop(session_id, None)

    def _verify_session_token(
        self, token: str | None
    ) -> tuple[tuple[str, str, str], int] | None:
        payload = self._session_payload(token)
        if payload is None:
            return None
        try:
            expires = int(payload.get("exp", 0))
        except (TypeError, ValueError):
            return None
        now = int(time.time())
        if expires <= now:
            return None
        session_id = str(payload.get("jti", "")).strip()
        if not session_id:
            return None
        with self._sessions_lock:
            stored_expiry = self._sessions.get(session_id)
            if stored_expiry is None or stored_expiry <= now:
                return None
        subject = str(payload.get("sub", "")).strip()
        if not subject:
            return None
        if subject == "env-admin":
            if not self.api_key:
                return None
            return ("admin", "env-admin", "env:TRELLIS_API_KEY"), expires
        record = self.key_store.find_active(subject)
        if not record or record.get("role") != "admin":
            return None
        expires_at = _parse_utc(record.get("expires_at"))
        if expires_at is not None and expires_at <= datetime.now(timezone.utc):
            return None
        return (
            str(record.get("role", "admin")),
            str(record.get("key_id", subject)),
            str(record.get("label", "unknown")),
        ), expires

    def _read_session(
        self, cookie_header: str | None
    ) -> tuple[tuple[str, str, str], int] | None:
        token = self._cookie_value(cookie_header, self.session_cookie_name)
        return self._verify_session_token(token)

    def _session_cookie_header(self, token: str, max_age: int) -> str:
        parts = [
            f"{self.session_cookie_name}={token}",
            "Path=/",
            "HttpOnly",
            "SameSite=Strict",
            f"Max-Age={max_age}",
        ]
        if self.secure_cookies:
            parts.append("Secure")
        return "; ".join(parts)

    def _clear_session_cookie_header(self) -> str:
        parts = [
            f"{self.session_cookie_name}=",
            "Path=/",
            "HttpOnly",
            "SameSite=Strict",
            "Max-Age=0",
            "Expires=Thu, 01 Jan 1970 00:00:00 GMT",
        ]
        if self.secure_cookies:
            parts.append("Secure")
        return "; ".join(parts)

    def _host_allowed(self, headers: dict[str, str]) -> bool:
        """Validate the HTTP Host header against configured/loopback allowlist to stop DNS rebinding ([REQ-TRL-21])."""
        raw_host = (headers.get("host") or "").strip()
        if not raw_host:
            return True
        if not self.allowed_hosts:
            return True
        hostname = _strip_host_port(raw_host)
        return hostname in self.allowed_hosts

    def _public_base_url(self, headers: dict[str, str], peer_ip: str = "127.0.0.1") -> str:
        """Resolve public server base URL from --public-url or validated Host/proxy headers ([REQ-TRL-21])."""
        if self.public_url:
            return self.public_url
        raw_host = (headers.get("host") or "").strip()
        if raw_host and self._host_allowed(headers):
            host_part = raw_host
        else:
            connect_host = "127.0.0.1" if self.host in ("0.0.0.0", "::") else self.host
            host_part = f"{connect_host}:{self.port}"
        scheme = self.scheme
        if peer_ip in self.trusted_proxies:
            xfp = (headers.get("x-forwarded-proto") or "").strip().lower()
            if xfp in ("http", "https"):
                scheme = xfp
        candidate = f"{scheme}://{host_part}"
        if not _SAFE_URL_RE.match(candidate):
            return self.base_url
        return candidate

    def _csrf_ok(self, headers: dict[str, str], auth_source: str | None) -> bool:
        if auth_source != "cookie":
            return True
        if (headers.get(_CSRF_HEADER) or "").strip() != "1":
            return False
        origin = (headers.get("origin") or "").strip()
        if not origin:
            return True
        if not self._host_allowed(headers):
            return False
        if self.public_url and origin.rstrip("/") == self.public_url:
            return True
        host = (headers.get("host") or f"{self.host}:{self.port}").strip()
        scheme = (headers.get("x-forwarded-proto") or self.scheme).strip().lower()
        return origin.rstrip("/") == f"{scheme}://{host}"

    def _origin_allowed(self, headers: dict[str, str]) -> bool:
        """Validate Origin header on /mcp and /admin/* against explicit, public_url, or verified allowlisted Host ([REQ-TRL-01, REQ-TRL-21])."""
        origin = (headers.get("origin") or "").strip().rstrip("/")
        if not origin:
            return True
        if self.allowed_origins is not None:
            return origin in {o.strip().rstrip("/") for o in self.allowed_origins if o.strip()}
        allowed: set[str] = set()
        if self.public_url:
            allowed.add(self.public_url)
        raw_host = (headers.get("host") or "").strip()
        if raw_host and self._host_allowed(headers):
            scheme = (headers.get("x-forwarded-proto") or self.scheme).strip().lower()
            allowed.update({f"{scheme}://{raw_host}", f"http://{raw_host}", f"https://{raw_host}"})
        if _is_loopback_host(self.host):
            allowed.update(
                {
                    f"http://127.0.0.1:{self.port}",
                    f"http://localhost:{self.port}",
                    f"https://127.0.0.1:{self.port}",
                    f"https://localhost:{self.port}",
                    "http://127.0.0.1",
                    "http://localhost",
                }
            )
        return origin in allowed

    def _evict_auth_state_locked(self, now: float) -> None:
        cutoff = now - 60.0
        stale_fail = [
            ip for ip, stamps in self._auth_failures.items()
            if not stamps or stamps[-1] < cutoff
        ]
        for ip in stale_fail:
            self._auth_failures.pop(ip, None)
        expired_locks = [
            ip for ip, until in self._auth_lockout_until.items()
            if until <= now
        ]
        for ip in expired_locks:
            self._auth_lockout_until.pop(ip, None)
        if len(self._auth_failures) > self.max_tracked_ips:
            ordered = sorted(
                self._auth_failures.items(),
                key=lambda item: item[1][-1] if item[1] else 0.0,
            )
            excess = len(self._auth_failures) - self.max_tracked_ips
            for ip, _ in ordered[:excess]:
                self._auth_failures.pop(ip, None)
        if len(self._auth_lockout_until) > self.max_tracked_ips:
            ordered_locks = sorted(self._auth_lockout_until.items(), key=lambda item: item[1])
            excess = len(self._auth_lockout_until) - self.max_tracked_ips
            for ip, _ in ordered_locks[:excess]:
                self._auth_lockout_until.pop(ip, None)

    def _is_locked_out(self, client_ip: str) -> int | None:
        now = time.monotonic()
        with self._auth_fail_lock:
            self._evict_auth_state_locked(now)
            until = self._auth_lockout_until.get(client_ip, 0.0)
            if until > now:
                return max(1, int(until - now))
            if client_ip in self._auth_lockout_until:
                self._auth_lockout_until.pop(client_ip, None)
        return None

    def _record_auth_failure(self, client_ip: str) -> None:
        now = time.monotonic()
        cutoff = now - 60.0
        with self._auth_fail_lock:
            self._evict_auth_state_locked(now)
            history = [t for t in self._auth_failures.get(client_ip, []) if t >= cutoff]
            history.append(now)
            self._auth_failures[client_ip] = history
            if len(history) >= max(1, self.auth_failure_limit):
                self._auth_lockout_until[client_ip] = now + max(1.0, self.auth_lockout_sec)
            if len(self._auth_failures) > self.max_tracked_ips:
                self._evict_auth_state_locked(now)

    def _clear_auth_failures(self, client_ip: str) -> None:
        with self._auth_fail_lock:
            self._auth_failures.pop(client_ip, None)
            self._auth_lockout_until.pop(client_ip, None)

    def _bundle_digest_cached(self) -> str:
        now = time.monotonic()
        with self._bundle_cache_lock:
            if (now - self._bundle_digest_ts) < self._bundle_digest_ttl and self._bundle_digest_cache:
                return self._bundle_digest_cache
        bundle_raw = json.dumps(build_remote_bundle(self.workspace_root)).encode("utf-8")
        digest = hashlib.sha256(bundle_raw).hexdigest()
        with self._bundle_cache_lock:
            self._bundle_digest_cache = digest
            self._bundle_digest_ts = now
        return digest

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
        client_ip: str = "127.0.0.1",
    ) -> tuple[int, dict[str, str], bytes]:
        """Process an HTTP request, record metrics and audit log, and return `(status, headers, body)` ([REQ-P2-05], [REQ-TRL-02])."""
        started = time.monotonic()
        audit_ctx: dict[str, Any] = {}
        norm_hdrs = {k.lower(): v for k, v in headers.items()}
        effective_ip = self._resolve_client_ip(client_ip, norm_hdrs)
        status, resp_headers, resp_body = self._dispatch_http(
            method,
            path,
            headers,
            body,
            client_ip=effective_ip,
            peer_ip=client_ip,
            audit_ctx=audit_ctx,
        )
        elapsed = time.monotonic() - started
        clean_path = path.split("?", 1)[0].rstrip("/") or "/"
        self._record_metrics(method, clean_path, status, elapsed)
        try:
            self.audit_logger.record(
                client_ip=effective_ip,
                key_id=audit_ctx.get("key_id"),
                role=audit_ctx.get("role"),
                method=method.upper(),
                path=clean_path,
                status=status,
                latency_ms=elapsed * 1000.0,
                tool=audit_ctx.get("tool"),
                model=audit_ctx.get("model"),
                decision=audit_ctx.get("decision"),
                args_sha256=hash_payload_sha256(body) if body else None,
            )
        except OSError:
            pass
        return status, resp_headers, resp_body

    def _dispatch_http(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes = b"",
        *,
        client_ip: str = "127.0.0.1",
        peer_ip: str = "127.0.0.1",
        audit_ctx: dict[str, Any] | None = None,
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
                    "bundle_sha256": self._bundle_digest_cached(),
                    "max_body_bytes": self.max_body_bytes,
                    "rate_limit": self.rate_limit,
                },
            )

        if method == "GET" and clean_path == "/.well-known/agent.json":
            return _json_resp(
                200,
                build_a2a_agent_card(self._public_base_url(norm_headers, peer_ip=peer_ip)),
            )

        if method == "GET" and clean_path == "/favicon.ico":
            return (
                200,
                {
                    "Content-Type": "image/x-icon",
                    "Content-Length": str(len(FAVICON_ICO)),
                    "Cache-Control": "public, max-age=86400",
                    "X-Content-Type-Options": "nosniff",
                },
                FAVICON_ICO,
            )

        if method == "GET" and clean_path in ("/admin", "/admin/dashboard"):
            nonce = secrets.token_urlsafe(16)
            raw = DASHBOARD_HTML.replace("__NONCE__", nonce).encode("utf-8")
            return (
                200,
                {
                    "Content-Type": "text/html; charset=utf-8",
                    "Content-Length": str(len(raw)),
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Referrer-Policy": "no-referrer",
                    "Cross-Origin-Opener-Policy": "same-origin",
                    "Cross-Origin-Resource-Policy": "same-origin",
                    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                    "Content-Security-Policy": (
                        f"default-src 'none'; script-src 'nonce-{nonce}'; "
                        f"style-src 'nonce-{nonce}'; img-src 'self'; connect-src 'self'; "
                        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
                    ),
                },
                raw,
            )

        if clean_path == "/admin/session":
            cookie_hdr = norm_headers.get("cookie")
            if method == "GET":
                session = self._read_session(cookie_hdr)
                if session is None:
                    return _json_resp(
                        200,
                        {"authenticated": False},
                        extra_headers={
                            "Cache-Control": "no-store",
                            "Set-Cookie": self._clear_session_cookie_header(),
                        },
                    )
                identity, expires = session
                expires_at = datetime.fromtimestamp(
                    expires, timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
                return _json_resp(
                    200,
                    {
                        "authenticated": True,
                        "role": identity[0],
                        "key_id": identity[1],
                        "label": identity[2],
                        "expires_at": expires_at,
                    },
                    extra_headers={"Cache-Control": "no-store"},
                )
            if method == "POST":
                try:
                    req_data = json.loads(body.decode("utf-8") if body else "{}")
                except json.JSONDecodeError as exc:
                    return _json_resp(400, {"error": f"Invalid JSON body: {exc}"})
                candidate = str(req_data.get("api_key", "")).strip()
                identity = self._authenticate_token(candidate)
                if identity is None:
                    return _json_resp(
                        401,
                        {
                            "error": "Unauthorized",
                            "message": "Invalid administrator API key.",
                        },
                        extra_headers={
                            "WWW-Authenticate": 'Bearer realm="trellis-mcp"'
                        },
                    )
                if identity[0] != "admin":
                    return _json_resp(
                        403,
                        {
                            "error": "Forbidden",
                            "message": "Administrator API key required for dashboard access.",
                        },
                    )
                token, expires = self._create_session_token(identity)
                max_age = max(1, expires - int(time.time()))
                expires_at = datetime.fromtimestamp(
                    expires, timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
                self._record_key_usage(identity, clean_path)
                return _json_resp(
                    200,
                    {
                        "status": "authenticated",
                        "role": identity[0],
                        "key_id": identity[1],
                        "label": identity[2],
                        "expires_at": expires_at,
                    },
                    extra_headers={
                        "Cache-Control": "no-store",
                        "Set-Cookie": self._session_cookie_header(token, max_age),
                    },
                )
            if method == "DELETE":
                session_token = self._cookie_value(
                    cookie_hdr, self.session_cookie_name
                )
                self._revoke_session_token(session_token)
                return _json_resp(
                    200,
                    {"status": "signed_out"},
                    extra_headers={
                        "Cache-Control": "no-store",
                        "Set-Cookie": self._clear_session_cookie_header(),
                    },
                )
            return _json_resp(
                405, {"error": f"Method not allowed on /admin/session: {method}"}
            )

        if (clean_path == "/mcp" or clean_path.startswith("/admin/") or clean_path == "/install.sh") and not self._host_allowed(
            norm_headers
        ):
            return _json_resp(
                403,
                {
                    "error": "Forbidden",
                    "message": "Request Host header is not in the Trellis server allowlist ([REQ-TRL-21]).",
                },
            )

        if (clean_path == "/mcp" or clean_path.startswith("/admin/")) and not self._origin_allowed(
            norm_headers
        ):
            return _json_resp(
                403,
                {
                    "error": "Forbidden",
                    "message": "Request Origin is not in the Trellis server allowlist ([REQ-TRL-01]).",
                },
            )

        retry_after = self._is_locked_out(client_ip)
        if retry_after is not None:
            return _json_resp(
                429,
                {
                    "error": "Too Many Requests",
                    "message": "Authentication temporarily locked out after repeated failures ([REQ-TRL-03]).",
                },
                extra_headers={"Retry-After": str(retry_after)},
            )

        auth_hdr = norm_headers.get("authorization")
        cookie_hdr = norm_headers.get("cookie")
        allow_cookie = (
            clean_path == "/metrics"
            or clean_path == "/admin/keys"
            or clean_path.startswith("/admin/keys/")
        )
        identity, auth_source = self._authenticate_request(
            auth_hdr, cookie_hdr, allow_cookie=allow_cookie
        )
        role = identity[0] if identity else None
        if role is None:
            self._record_auth_failure(client_ip)
            return _json_resp(
                401,
                {
                    "error": "Unauthorized",
                    "message": "Valid 'Authorization: Bearer <API_KEY>' header required ([REQ-MCP-06]).",
                },
                extra_headers={"WWW-Authenticate": 'Bearer realm="trellis-mcp"'},
            )
        self._clear_auth_failures(client_ip)
        if identity is not None:
            self._record_key_usage(identity, clean_path)
            if audit_ctx is not None:
                audit_ctx["role"] = identity[0]
                audit_ctx["key_id"] = identity[1]

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

        # Admin Bundle Hot-Deploy Endpoint ([REQ-MCP-09, REQ-TRL-20])
        if clean_path == "/admin/deploy":
            if not self.enable_remote_deploy:
                return _json_resp(
                    403,
                    {
                        "error": "Forbidden",
                        "message": "Remote hot-deploy endpoint /admin/deploy is disabled by default ([REQ-TRL-20]).",
                    },
                )
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
            if not self.deploy_signing_key:
                return _json_resp(
                    403,
                    {
                        "error": "Deploy signing key not configured",
                        "message": "Configure a separate --deploy-signing-key / TRELLIS_DEPLOY_SIGNING_KEY ([REQ-TRL-20]).",
                    },
                )
            if candidate and hmac.compare_digest(
                self.deploy_signing_key.encode("utf-8"), candidate.encode("utf-8")
            ):
                return _json_resp(
                    403,
                    {
                        "error": "Deploy key separation violation",
                        "message": "Deploy signing key must be distinct from the admin bearer token ([REQ-TRL-20]).",
                    },
                )
            provided_sig = (norm_headers.get(_SIGNATURE_HEADER) or "").strip().lower()
            if not provided_sig:
                return _json_resp(
                    400,
                    {
                        "error": "Missing X-Trellis-Signature header",
                        "message": "Sign the .pyz bytes with HMAC-SHA256 using the configured deploy signing key ([REQ-TRL-20]).",
                    },
                )
            expected_sig = compute_hmac_signature(body, self.deploy_signing_key)
            if not hmac.compare_digest(expected_sig, provided_sig):
                return _json_resp(
                    403,
                    {
                        "error": "Invalid deploy signature",
                        "message": "X-Trellis-Signature must match HMAC-SHA256(payload, deploy_signing_key) ([REQ-TRL-20]).",
                    },
                )
            if not body or not zipfile.is_zipfile(io.BytesIO(body)):
                return _json_resp(400, {"error": "Invalid .pyz bundle payload (must be a valid zipapp archive)."})
            with zipfile.ZipFile(io.BytesIO(body), "r") as zf:
                if "trellis_mcp/__main__.py" not in zf.namelist():
                    return _json_resp(400, {"error": "Archive is missing trellis_mcp/__main__.py."})

            uploaded_version = _extract_pyz_version(body)
            if not uploaded_version:
                return _json_resp(
                    400,
                    {"error": "Archive is missing trellis_mcp/__init__.py with a valid __version__."},
                )

            target_pyz = (
                self.workspace_root
                if self.workspace_root.is_file()
                else (self.workspace_root / "trellis-mcp.pyz")
            )
            uploaded_tuple = _parse_semver(uploaded_version)
            running_tuple = _parse_semver(__version__)
            if target_pyz.is_file():
                existing_ver = _extract_pyz_version(target_pyz.read_bytes()) or __version__
                if uploaded_tuple <= _parse_semver(existing_ver):
                    return _json_resp(
                        409,
                        {
                            "error": "Version conflict",
                            "message": f"Uploaded version {uploaded_version} must be strictly greater than deployed version {existing_ver} ([REQ-TRL-20]).",
                        },
                    )
            elif uploaded_tuple < running_tuple:
                return _json_resp(
                    409,
                    {
                        "error": "Version downgrade rejected",
                        "message": f"Uploaded version {uploaded_version} is lower than running version {__version__} ([REQ-TRL-20]).",
                    },
                )

            artifact_sha256 = hash_payload_sha256(body)
            target_pyz.parent.mkdir(parents=True, exist_ok=True)
            backup_path: Path | None = None
            if target_pyz.is_file():
                backup_path = target_pyz.with_suffix(".pyz.bak")
                shutil.copy2(target_pyz, backup_path)

            tmp_fd, tmp_name = tempfile.mkstemp(
                prefix=".trellis-deploy-", suffix=".tmp", dir=str(target_pyz.parent)
            )
            try:
                with os.fdopen(tmp_fd, "wb") as tmp_fh:
                    tmp_fh.write(body)
                    tmp_fh.flush()
                    os.fsync(tmp_fh.fileno())
                os.replace(tmp_name, target_pyz)
            except OSError:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise

            self.mcp_server = TrellisMCPServer(workspace_root=target_pyz)
            with self._bundle_cache_lock:
                self._bundle_digest_cache = None
                self._bundle_digest_ts = 0.0
            if audit_ctx is not None:
                audit_ctx["decision"] = f"deploy:v={uploaded_version}:sha256={artifact_sha256}"
            return _json_resp(
                200,
                {
                    "status": "deployed",
                    "target": str(target_pyz),
                    "backup": str(backup_path) if backup_path else None,
                    "bytes": len(body),
                    "sha256": artifact_sha256,
                    "deployed_version": uploaded_version,
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
            if method in ("POST", "DELETE", "PATCH") and not self._csrf_ok(
                norm_headers, auth_source
            ):
                return _json_resp(
                    403,
                    {
                        "error": "Forbidden",
                        "message": "Missing or invalid X-Trellis-CSRF header for cookie-authenticated requests.",
                    },
                )
            public_base = self._public_base_url(norm_headers, peer_ip=peer_ip)

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
                raw_scopes = req_data.get("scopes")
                scopes = (
                    [str(s).strip() for s in raw_scopes if str(s).strip()]
                    if isinstance(raw_scopes, list)
                    else None
                )
                expires_days = req_data.get("expires_days")
                created = self.key_store.generate_key(
                    label=label,
                    role=req_role,
                    expires_days=int(expires_days) if expires_days is not None else None,
                    scopes=scopes,
                )
                created["install_command"] = (
                    f'export TRELLIS_API_KEY="{created["api_key"]}" && '
                    f'curl -fsSL -H "Authorization: Bearer $TRELLIS_API_KEY" {public_base}/install.sh | sh'
                )
                created["mcp_endpoint"] = f"{public_base}/mcp"
                return _json_resp(201, created)

            if method == "PATCH":
                target_id = clean_path[len("/admin/keys/") :].strip() if clean_path.startswith("/admin/keys/") else ""
                if not target_id:
                    return _json_resp(400, {"error": "Key ID required for update"})
                try:
                    req_data = json.loads(body.decode("utf-8") if body else "{}")
                except json.JSONDecodeError as exc:
                    return _json_resp(400, {"error": f"Invalid JSON body: {exc}"})
                if "label" not in req_data and "role" not in req_data:
                    return _json_resp(400, {"error": "Provide label and/or role to update"})
                try:
                    updated = self.key_store.update_key(
                        target_id,
                        label=req_data.get("label") if "label" in req_data else None,
                        role=req_data.get("role") if "role" in req_data else None,
                    )
                except ValueError as exc:
                    return _json_resp(400, {"error": str(exc)})
                if updated is None:
                    return _json_resp(404, {"error": f"Key not found: {target_id}"})
                return _json_resp(200, {"status": "updated", "key": updated})

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
                script = render_remote_install_script(
                    self._public_base_url(norm_headers, peer_ip=peer_ip)
                )
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

            proto_hdr = (norm_headers.get("mcp-protocol-version") or "").strip()
            if proto_hdr and proto_hdr not in SUPPORTED_PROTOCOL_VERSIONS:
                return _json_resp(
                    400,
                    {
                        "error": "Bad Request",
                        "message": f"Unsupported MCP-Protocol-Version: {proto_hdr} ([REQ-TRL-04]).",
                        "supported": list(SUPPORTED_PROTOCOL_VERSIONS),
                    },
                )

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

            scopes = self.key_store.get_scopes(identity[1]) if identity is not None else None

            def _scope_error(item: dict[str, Any]) -> tuple[int, dict[str, str], bytes] | None:
                if item.get("method") != "tools/call":
                    return None
                params = item.get("params") or {}
                tool_name = params.get("name")
                if audit_ctx is not None and isinstance(tool_name, str):
                    audit_ctx["tool"] = tool_name
                if scopes is not None and isinstance(tool_name, str) and tool_name not in scopes:
                    if audit_ctx is not None:
                        audit_ctx["decision"] = "deny:scope"
                    return _json_resp(
                        403,
                        {
                            "error": "Forbidden",
                            "message": f"API key scope does not permit tool '{tool_name}' ([REQ-TRL-03]).",
                        },
                    )
                return None

            caller_label = identity[2] if identity is not None else None

            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict) and (err := _scope_error(item)) is not None:
                        return err
                responses = [
                    resp
                    for item in payload
                    if isinstance(item, dict)
                    and (
                        resp := self.mcp_server.handle_request(
                            item,
                            caller_label=caller_label,
                            caller_role=role,
                            remote_mode=True,
                        )
                    )
                    is not None
                ]
                return _json_resp(200, responses)

            if isinstance(payload, dict) and (err := _scope_error(payload)) is not None:
                return err

            response = self.mcp_server.handle_request(
                payload,
                caller_label=caller_label,
                caller_role=role,
                remote_mode=True,
            )
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
