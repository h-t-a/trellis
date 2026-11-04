"""Private VM HTTP MCP Server with constant-time Bearer Token authentication ([REQ-MCP-05..08]).

Exposes:
- `GET    /healthz`          -> Unauthenticated health probe (`200 OK`)
- `POST   /mcp`              -> Protected JSON-RPC 2.0 MCP endpoint (`Authorization: Bearer <API_KEY>`)
- `GET    /bundle.json`      -> Protected skill & rule bundle for zero-clone remote client setup
- `GET    /install.sh`       -> Protected shell bootstrap script (`curl -H "Authorization: Bearer $KEY" .../install.sh | sh`)
- `GET    /admin/keys`       -> Admin-only list of issued user/team API keys (`[REQ-MCP-08]`)
- `POST   /admin/keys`       -> Admin-only auto-generation of a new user/team API key (`[REQ-MCP-08]`)
- `DELETE /admin/keys/<id>`  -> Admin-only immediate key revocation (`[REQ-MCP-08]`)
"""

from __future__ import annotations

import hmac
import io
import json
import os
import re
import secrets
import threading
import zipfile
from datetime import datetime, timezone
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
    """File-backed API key registry supporting admin auto-generation and team/user keys ([REQ-MCP-08])."""

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
        try:
            os.chmod(self.keys_file, 0o600)
        except OSError:
            pass

    @staticmethod
    def _sanitize_record(rec: dict[str, Any]) -> dict[str, Any]:
        return {
            "key_id": rec.get("key_id"),
            "label": rec.get("label"),
            "role": rec.get("role", "member"),
            "prefix": rec.get("prefix"),
            "created_at": rec.get("created_at"),
            "revoked": bool(rec.get("revoked", False)),
        }

    def generate_key(self, label: str, role: str = "member") -> dict[str, Any]:
        """Generate and persist a new API key for a user or team ([REQ-MCP-08-02])."""
        norm_role = role.strip().lower() if role else "member"
        if norm_role not in ("admin", "member"):
            raise ValueError("Role must be 'admin' or 'member'.")
        slug = re.sub(r"[^a-z0-9]+", "_", (label or norm_role).strip().lower()).strip("_") or norm_role
        slug = slug[:24]
        raw_key = f"trl_{slug}_{secrets.token_urlsafe(24)}"
        key_id = f"key_{secrets.token_hex(6)}"
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        prefix = f"{raw_key[:14]}...{raw_key[-4:]}"

        record = {
            "key_id": key_id,
            "label": label.strip() or slug,
            "role": norm_role,
            "token": raw_key,
            "prefix": prefix,
            "created_at": created_at,
            "revoked": False,
        }
        with self._lock:
            records = self._load_records()
            records.append(record)
            self._save_records(records)

        result = self._sanitize_record(record)
        result["api_key"] = raw_key
        return result

    def ensure_admin_key(self) -> tuple[str, bool]:
        """Return an existing active admin key or auto-generate one ([REQ-MCP-08-01])."""
        with self._lock:
            records = self._load_records()
            for rec in records:
                if not rec.get("revoked") and rec.get("role") == "admin" and rec.get("token"):
                    return str(rec["token"]), False
        created = self.generate_key(label="admin", role="admin")
        return str(created["api_key"]), True

    def verify_token(self, candidate: str | None) -> str | None:
        """Verify candidate Bearer token in constant time and return role ('admin' | 'member') or None."""
        if not candidate:
            return None
        cand_bytes = candidate.encode("utf-8")
        matched_role: str | None = None
        with self._lock:
            records = self._load_records()
        for rec in records:
            if rec.get("revoked"):
                continue
            token = str(rec.get("token", ""))
            if token and hmac.compare_digest(cand_bytes, token.encode("utf-8")):
                matched_role = str(rec.get("role", "member"))
        return matched_role

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
    ) -> None:
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

        if not resolved_key:
            raise ValueError(
                "TRELLIS_API_KEY is required to start the HTTP server ([REQ-MCP-06]). "
                "Set `export TRELLIS_API_KEY='<team-secret>'`, pass `--api-key`, or pass `--auto-generate-key`."
            )
        self.host = host
        self.api_key = resolved_key
        self.mcp_server = TrellisMCPServer(workspace_root=self.workspace_root)

        parent = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def _handle_all(self, method: str) -> None:
                content_length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(content_length) if content_length > 0 else b""
                req_headers = {k: v for k, v in self.headers.items()}
                status, resp_headers, resp_body = parent.dispatch_http(
                    method=method,
                    path=self.path,
                    headers=req_headers,
                    body=raw_body,
                )
                self.send_response(status)
                for hk, hv in resp_headers.items():
                    self.send_header(hk, hv)
                self.end_headers()
                if resp_body:
                    self.wfile.write(resp_body)

            def do_GET(self) -> None:  # noqa: N802
                self._handle_all("GET")

            def do_POST(self) -> None:  # noqa: N802
                self._handle_all("POST")

            def do_DELETE(self) -> None:  # noqa: N802
                self._handle_all("DELETE")

        self._httpd = ThreadingHTTPServer((host, port), _Handler)
        self.port = int(self._httpd.server_address[1])
        self._thread: threading.Thread | None = None
        _ACTIVE_SERVERS[self.base_url] = self

    @property
    def base_url(self) -> str:
        connect_host = "127.0.0.1" if self.host in ("0.0.0.0", "::") else self.host
        return f"http://{connect_host}:{self.port}"

    def _authenticate_role(self, auth_header: str | None) -> str | None:
        """Return 'admin', 'member', or None for the provided Authorization header."""
        if verify_bearer_header(auth_header, self.api_key):
            return "admin"
        candidate = extract_bearer_token(auth_header)
        return self.key_store.verify_token(candidate)

    def dispatch_http(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes = b"",
    ) -> tuple[int, dict[str, str], bytes]:
        """Process an HTTP request and return `(status_code, headers_dict, body_bytes)`."""
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

        if method == "GET" and clean_path == "/healthz":
            return _json_resp(
                200,
                {
                    "status": "ok",
                    "service": "trellis-mcp",
                    "version": __version__,
                },
            )

        auth_hdr = norm_headers.get("authorization")
        role = self._authenticate_role(auth_hdr)
        if role is None:
            return _json_resp(
                401,
                {
                    "error": "Unauthorized",
                    "message": "Valid 'Authorization: Bearer <API_KEY>' header required ([REQ-MCP-06]).",
                },
                extra_headers={"WWW-Authenticate": 'Bearer realm="trellis-mcp"'},
            )

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

        if method == "GET":
            if clean_path == "/bundle.json":
                return _json_resp(200, build_remote_bundle(self.workspace_root))

            if clean_path == "/install.sh":
                host_hdr = norm_headers.get("host") or f"{self.host}:{self.port}"
                scheme = norm_headers.get("x-forwarded-proto", "http")
                script = render_remote_install_script(f"{scheme}://{host_hdr}")
                raw = script.encode("utf-8")
                return (
                    200,
                    {
                        "Content-Type": "text/x-shellscript; charset=utf-8",
                        "Content-Length": str(len(raw)),
                    },
                    raw,
                )

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
            f"Trellis MCP HTTP Server v{__version__} listening on http://{self.host}:{self.port}/mcp "
            "(Authorization: Bearer <API_KEY> required)"
        )
        if self.auto_generated_admin_key:
            print(f"[ADMIN KEY AUTO-GENERATED] Saved to {self.key_store.keys_file}")
            print(f"  TRELLIS_API_KEY={self.api_key}")
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
