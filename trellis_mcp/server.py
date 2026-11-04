"""Zero-dependency Model Context Protocol (MCP) JSON-RPC 2.0 server over stdio ([REQ-MCP-01])."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, TextIO

from trellis_mcp import __version__
from trellis_mcp.tools import (
    PACKAGE_ROOT,
    STANDARD_FILE_MAP,
    TOOL_DEFINITIONS,
    read_bundled_text,
    tool_trellis_budget,
    tool_trellis_doctor,
    tool_trellis_enhance,
    tool_trellis_get_standard,
    tool_trellis_handoff,
    tool_trellis_rca,
    tool_trellis_review,
    tool_trellis_spec,
)

PROMPT_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "pb-rca",
        "description": "Fast 9-step Root Cause Analysis + minimal fix workflow (absorbs /pb-fix).",
        "arguments": [
            {"name": "symptom", "description": "Observed bug symptom or error log", "required": True}
        ],
    },
    {
        "name": "pb-spec",
        "description": "Spec-Driven Development generator (Class M Micro-Spec or Class L Full Spec).",
        "arguments": [
            {"name": "title", "description": "Feature or bugfix title", "required": True},
            {"name": "task_class", "description": "M or L", "required": False},
        ],
    },
    {
        "name": "pb-enhance",
        "description": "Little's Law concurrency sizing + Big-O & I/O complexity optimization (absorbs /pb-complexity).",
        "arguments": [
            {"name": "target", "description": "Target endpoint or function", "required": True},
            {"name": "mode", "description": "analyze or implement", "required": False},
        ],
    },
    {
        "name": "pb-handoff",
        "description": "Compact <=25-line session handoff packet before /clear or /compact.",
        "arguments": [
            {"name": "goal", "description": "Active task goal", "required": True}
        ],
    },
    {
        "name": "pb-review",
        "description": "Pre-PR review against Story DoD, Testing Standard, Security Baseline, and Git convention.",
        "arguments": [],
    },
    {
        "name": "pb-plan",
        "description": "Pre-coding Implementation Plan gate (Class M / Class L).",
        "arguments": [
            {"name": "feature", "description": "Feature or story summary", "required": True}
        ],
    },
    {
        "name": "pb-release-check",
        "description": "Release-level Definition of Done & Performance SLA gate.",
        "arguments": [],
    },
]


class TrellisMCPServer:
    """MCP JSON-RPC 2.0 Server exposing Trellis tools, resources, and prompts."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self._tool_dispatch: dict[str, Callable[[dict[str, Any], Path | None], dict[str, Any]]] = {
            "trellis_get_standard": tool_trellis_get_standard,
            "trellis_rca": tool_trellis_rca,
            "trellis_spec": tool_trellis_spec,
            "trellis_enhance": tool_trellis_enhance,
            "trellis_budget": tool_trellis_budget,
            "trellis_handoff": tool_trellis_handoff,
            "trellis_review": tool_trellis_review,
            "trellis_doctor": tool_trellis_doctor,
        }

    def handle_request(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single JSON-RPC 2.0 request or notification."""
        method = str(message.get("method", ""))
        msg_id = message.get("id")
        params = message.get("params") or {}

        # Notifications (no id) do not return a response
        if msg_id is None or method.startswith("notifications/"):
            return None

        try:
            if method == "initialize":
                protocol_version = params.get("protocolVersion", "2024-11-05")
                return self._response(
                    msg_id,
                    {
                        "protocolVersion": protocol_version,
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "resources": {"subscribe": False, "listChanged": False},
                            "prompts": {"listChanged": False},
                        },
                        "serverInfo": {
                            "name": "trellis-mcp",
                            "version": __version__,
                        },
                    },
                )

            if method == "ping":
                return self._response(msg_id, {})

            if method == "tools/list":
                return self._response(msg_id, {"tools": TOOL_DEFINITIONS})

            if method == "tools/call":
                tool_name = str(params.get("name", ""))
                tool_args = dict(params.get("arguments") or {})
                handler = self._tool_dispatch.get(tool_name)
                if not handler:
                    return self._error(msg_id, -32601, f"Unknown tool: {tool_name}")
                result = handler(tool_args, self.workspace_root)
                return self._response(msg_id, result)

            if method == "resources/list":
                resources = []
                for key, rel_path in STANDARD_FILE_MAP.items():
                    kind = "templates" if rel_path.startswith("templates/") else "standards"
                    resources.append(
                        {
                            "uri": f"trellis://{kind}/{key}",
                            "name": f"Trellis: {key}",
                            "description": f"Authoritative Trellis document ({rel_path})",
                            "mimeType": "text/markdown",
                        }
                    )
                return self._response(msg_id, {"resources": resources})

            if method == "resources/read":
                uri = str(params.get("uri", ""))
                key = uri.rstrip("/").split("/")[-1]
                res = tool_trellis_get_standard({"name": key}, self.workspace_root)
                if res.get("isError"):
                    return self._error(msg_id, -32602, res["content"][0]["text"])
                return self._response(
                    msg_id,
                    {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "text/markdown",
                                "text": res["content"][0]["text"],
                            }
                        ]
                    },
                )

            if method == "prompts/list":
                return self._response(msg_id, {"prompts": PROMPT_DEFINITIONS})

            if method == "prompts/get":
                name = str(params.get("name", ""))
                skill_text = read_bundled_text(
                    f".agents/skills/{name}/SKILL.md", workspace_root=self.workspace_root
                )
                if skill_text is not None:
                    return self._response(
                        msg_id,
                        {
                            "description": f"Trellis /{name} workflow prompt",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {"type": "text", "text": skill_text},
                                }
                            ],
                        },
                    )
                name = str(params.get("name", ""))
                skill_file = self.workspace_root / ".agents" / "skills" / name / "SKILL.md"
                if not skill_file.exists():
                    skill_file = PACKAGE_ROOT / ".agents" / "skills" / name / "SKILL.md"
                if not skill_file.exists():
                    return self._error(msg_id, -32602, f"Unknown prompt/skill: {name}")
                name = str(params.get("name", ""))
                skill_text = read_bundled_text(
                    f".agents/skills/{name}/SKILL.md", workspace_root=self.workspace_root
                )
                if skill_text is None:
                    return self._error(msg_id, -32602, f"Unknown prompt/skill: {name}")
                return self._response(
                    msg_id,
                    {
                        "description": f"Trellis /{name} workflow prompt",
                        "messages": [
                            {
                                "role": "user",
                                "content": {"type": "text", "text": skill_text},
                            }
                        ],
                    },
                )

            return self._error(msg_id, -32601, f"Method not found: {method}")
        except Exception as exc:  # pragma: no cover - defensive JSON-RPC error wrapper
            return self._error(msg_id, -32603, f"Internal error: {exc}")

    def serve_stdio(
        self, in_stream: TextIO = sys.stdin, out_stream: TextIO = sys.stdout
    ) -> None:
        """Run the newline-delimited JSON-RPC 2.0 loop over stdio."""
        for raw_line in in_stream:
            line = raw_line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                err_resp = self._error(None, -32700, f"Parse error: {exc}")
                out_stream.write(json.dumps(err_resp) + "\n")
                out_stream.flush()
                continue

            response = self.handle_request(message)
            if response is not None:
                out_stream.write(json.dumps(response) + "\n")
                out_stream.flush()

    @staticmethod
    def _response(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": code, "message": message},
        }
