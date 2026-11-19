"""Zero-dependency Model Context Protocol (MCP) JSON-RPC 2.0 server over stdio ([REQ-MCP-01])."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, TextIO

from trellis_mcp import __version__
from trellis_mcp.knowledge import tool_trellis_search_knowledge
from trellis_mcp.pipeline import tool_trellis_pipeline, tool_trellis_synthesize
from trellis_mcp.router import tool_trellis_route_model
from trellis_mcp.tools import (
    PACKAGE_ROOT,
    STANDARD_FILE_MAP,
    TOOL_DEFINITIONS,
    list_bundled_skills,
    read_bundled_text,
    tool_trellis_analytics,
    tool_trellis_budget,
    tool_trellis_classify,
    tool_trellis_doctor,
    tool_trellis_enhance,
    tool_trellis_get_standard,
    tool_trellis_handoff,
    tool_trellis_mcp_registry,
    tool_trellis_rca,
    tool_trellis_review,
    tool_trellis_scan,
    tool_trellis_spec,
    tool_trellis_test,
    tool_trellis_verify,
)

SUPPORTED_PROTOCOL_VERSIONS: tuple[str, ...] = ("2025-06-18", "2025-03-26", "2024-11-05")

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
    {
        "name": "pb-git-convention",
        "description": "Enforce Conventional Commits, banking commit types (sec/audit/feat/fix), semantic branches, and pre-push scans.",
        "arguments": [],
    },
    {
        "name": "pb-pipeline",
        "description": "Multi-stage governance orchestrator with Tier 2 gates, loop halts, and cross-model review.",
        "arguments": [
            {"name": "target_stage", "description": "Destination pipeline stage", "required": True}
        ],
    },
    {
        "name": "pb-synthesize",
        "description": "Multi-AI consensus and divergence synthesis matrix across multiple model responses.",
        "arguments": [
            {"name": "prompt", "description": "Original prompt or decision topic", "required": True}
        ],
    },
    {
        "name": "pb-route",
        "description": "Select legally usable commercial or strict on-prem AI models based on tier and data classification.",
        "arguments": [
            {"name": "data_classification", "description": "Public, Internal, Confidential, or Restricted", "required": True},
            {"name": "task_type", "description": "coding, review, research, classify, or general", "required": False},
        ],
    },
    {
        "name": "pb-knowledge",
        "description": "Run vMF semantic search across Trellis standards and RCAs with kappa confidence and access filter.",
        "arguments": [
            {"name": "query", "description": "Search query", "required": True}
        ],
    },
    {
        "name": "pb-data-classification",
        "description": "Classify data sensitivity and run Luhn PAN, JWT, Myanmar NRC, phone, and IBAN redaction scans.",
        "arguments": [],
    },
    {
        "name": "pb-mcp-audit",
        "description": "Audit MCP server allowlist, SHA-256/HMAC standard provenance, and cost/quota telemetry.",
        "arguments": [],
    },
    {
        "name": "pb-security-audit",
        "description": "Audit code, configuration, hooks, and AI customizations against Security Baseline and AI Boundary tiers.",
        "arguments": [],
    },
    {
        "name": "pb-test-writer",
        "description": "Write failing [REQ-NNN-XX] tests first, run full suites, and enforce zero weakened assertions.",
        "arguments": [],
    },
    {
        "name": "pb-perf-test",
        "description": "Design, size, and evaluate performance tests using Performance SLA Standard and Little's Law.",
        "arguments": [],
    },
    {
        "name": "pb-doc",
        "description": "Audit, scaffold, and validate project documentation across Diátaxis, ADRs, C4/arc42, contracts, SRE runbooks, AGENTS.md, and CI gates.",
        "arguments": [
            {"name": "mode", "description": "audit, scaffold, or gate", "required": False},
            {"name": "target_path", "description": "Repository or directory path to audit/scaffold", "required": False},
        ],
    },
]


def _extract_skill_description(skill_text: str, fallback: str) -> str:
    lines = skill_text.splitlines()
    if len(lines) >= 3 and lines[0].strip() == "---":
        for line in lines[1:15]:
            if line.strip() == "---":
                break
            if line.lower().startswith("description:"):
                desc = line.split(":", 1)[1].strip().strip('"').strip("'")
                if desc and desc not in (">-", "|", ">"):
                    return desc
    return fallback


def _build_prompt_catalog(workspace_root: Path | None) -> list[dict[str, Any]]:
    """Expose every canonical `/pb-*` bundled skill via MCP prompts/list."""
    metadata_by_name = {entry["name"]: dict(entry) for entry in PROMPT_DEFINITIONS}
    bundled = list_bundled_skills(workspace_root=workspace_root)
    if not bundled:
        return list(PROMPT_DEFINITIONS)

    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for base in PROMPT_DEFINITIONS:
        name = base["name"]
        if name in bundled:
            ordered.append(dict(base))
            seen.add(name)
    for skill_name, skill_text in sorted(bundled.items()):
        if skill_name in seen:
            continue
        meta = metadata_by_name.get(skill_name)
        ordered.append(
            meta
            or {
                "name": skill_name,
                "description": _extract_skill_description(
                    skill_text, f"Trellis /{skill_name} workflow skill"
                ),
                "arguments": [],
            }
        )
    return ordered


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
            "trellis_test": tool_trellis_test,
            "trellis_scan": tool_trellis_scan,
            "trellis_classify": tool_trellis_classify,
            "trellis_mcp_registry": tool_trellis_mcp_registry,
            "trellis_verify": tool_trellis_verify,
            "trellis_analytics": tool_trellis_analytics,
            "trellis_search_knowledge": tool_trellis_search_knowledge,
            "trellis_route_model": tool_trellis_route_model,
            "trellis_pipeline": tool_trellis_pipeline,
            "trellis_synthesize": tool_trellis_synthesize,
        }

    def handle_request(
        self,
        message: dict[str, Any],
        *,
        caller_label: str | None = None,
        remote_mode: bool = False,
    ) -> dict[str, Any] | None:
        """Process a single JSON-RPC 2.0 request or notification."""
        method = str(message.get("method", ""))
        msg_id = message.get("id")
        params = message.get("params") or {}

        # Notifications (no id) do not return a response
        if msg_id is None or method.startswith("notifications/"):
            return None

        try:
            if method == "initialize":
                requested = str(params.get("protocolVersion", "2024-11-05")).strip()
                protocol_version = (
                    requested if requested in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
                )
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
                if remote_mode:
                    tool_args.setdefault("_remote_mode", True)
                if caller_label:
                    tool_args.setdefault("_auth_label", caller_label)
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
                return self._response(
                    msg_id, {"prompts": _build_prompt_catalog(self.workspace_root)}
                )

            if method == "prompts/get":
                name = str(params.get("name", "")).strip().lstrip("/")
                if not name:
                    return self._error(msg_id, -32602, "Prompt/skill name is required")
                skill_text = read_bundled_text(
                    f".agents/skills/{name}/SKILL.md", workspace_root=self.workspace_root
                )
                if skill_text is None:
                    return self._error(msg_id, -32602, f"Unknown prompt/skill: {name}")
                return self._response(
                    msg_id,
                    {
                        "description": f"Trellis /{name} workflow skill",
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
