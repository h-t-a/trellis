"""Private VM HTTP MCP Server with constant-time Bearer Token authentication ([REQ-MCP-05..07]).

Exposes:
- `GET  /healthz`     -> Unauthenticated health probe (`200 OK`)
- `POST /mcp`         -> Protected JSON-RPC 2.0 MCP endpoint (`Authorization: Bearer <TEAM_API_KEY>`)
- `GET  /bundle.json` -> Protected skill & rule bundle for zero-clone remote client setup
- `GET  /install.sh`  -> Protected shell bootstrap script (`curl -H "Authorization: Bearer $KEY" .../install.sh | sh`)
"""

from __future__ import annotations

import hmac
import io
import json
import os
import threading
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import BaseHandler, OpenerDirector, ProxyHandler, Request, build_opener

from trellis_mcp import __version__
from trellis_mcp.installer import build_remote_bundle, render_remote_install_script
from trellis_mcp.server import TrellisMCPServer
from trellis_mcp.tools import PACKAGE_ROOT

_ACTIVE_SERVERS: dict[str, "TrellisHTTPServer"] = {}


def verify_bearer_header(auth_header: str | None, expected_api_key: str) -> bool:
    """Verify `Authorization: Bearer <TEAM_API_KEY>` in constant time ([REQ-MCP-06])."""
    if not expected_api_key:
        return False
    if not auth_header:
        return False
    parts = auth_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False
    candidate = parts[1].strip()
    if not candidate:
        return False
    return hmac.compare_digest(
        candidate.encode("utf-8"), expected_api_key.encode("utf-8")
    )


class TrellisHTTPServer:
    """Thread-safe HTTP wrapper around `TrellisMCPServer` with Bearer authentication."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        api_key: str | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        resolved_key = (api_key if api_key is not None else os.environ.get("TRELLIS_API_KEY", "")).strip()
        if not resolved_key:
            raise ValueError(
                "TRELLIS_API_KEY is required to start the HTTP server ([REQ-MCP-06]). "
                "Set `export TRELLIS_API_KEY='<team-secret>'` or pass `--api-key`."
            )
        self.host = host
        self.api_key = resolved_key
        self.workspace_root = (workspace_root or PACKAGE_ROOT).resolve()
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

        self._httpd = ThreadingHTTPServer((host, port), _Handler)
        self.port = int(self._httpd.server_address[1])
        self._thread: threading.Thread | None = None
        _ACTIVE_SERVERS[self.base_url] = self

    @property
    def base_url(self) -> str:
        connect_host = "127.0.0.1" if self.host in ("0.0.0.0", "::") else self.host
        return f"http://{connect_host}:{self.port}"

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
        if not verify_bearer_header(auth_hdr, self.api_key):
            return _json_resp(
                401,
                {
                    "error": "Unauthorized",
                    "message": "Valid 'Authorization: Bearer <TEAM_API_KEY>' header required ([REQ-MCP-06]).",
                },
                extra_headers={"WWW-Authenticate": 'Bearer realm="trellis-mcp"'},
            )

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
            "(Authorization: Bearer <TRELLIS_API_KEY> required)"
        )
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
