"""Tier- and data-classification-driven multi-AI model router + LiteLLM config generator ([REQ-TRL-11])."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trellis_mcp.tools import _err, _ok

_ON_PREM_CATALOG: dict[str, dict[str, str]] = {
    "coding": {"model": "on_prem/qwen2.5-coder:32b", "provider": "ollama-on-prem"},
    "review": {"model": "on_prem/llama-3.3-70b-instruct", "provider": "vllm-on-prem"},
    "research": {"model": "on_prem/qwen2.5:32b", "provider": "ollama-on-prem"},
    "classify": {"model": "on_prem/qwen2.5:7b", "provider": "ollama-on-prem"},
    "general": {"model": "on_prem/mistral-nemo:12b", "provider": "ollama-on-prem"},
}

_CLOUD_FALLBACK_CHAINS: dict[str, list[dict[str, str]]] = {
    "research": [
        {"model": "perplexity/sonar-pro", "provider": "perplexity", "max_tier": "Public"},
        {"model": "perplexity/sonar-reasoning-pro", "provider": "perplexity", "max_tier": "Public"},
        {"model": "gemini/gemini-2.5-pro", "provider": "google", "max_tier": "Internal"},
        {"model": "xai/grok-4", "provider": "xai", "max_tier": "Internal"},
        {"model": "anthropic/claude-sonnet-4", "provider": "anthropic", "max_tier": "Internal"},
        {"model": "on_prem/qwen2.5:32b", "provider": "ollama-on-prem", "max_tier": "Restricted"},
    ],
    "coding": [
        {"model": "anthropic/claude-sonnet-4", "provider": "anthropic", "max_tier": "Internal"},
        {"model": "openai/gpt-5-codex", "provider": "openai", "max_tier": "Internal"},
        {"model": "xai/grok-4-fast", "provider": "xai", "max_tier": "Internal"},
        {"model": "gemini/gemini-2.5-pro", "provider": "google", "max_tier": "Internal"},
        {"model": "on_prem/qwen2.5-coder:32b", "provider": "ollama-on-prem", "max_tier": "Restricted"},
    ],
    "review": [
        {"model": "openai/gpt-5", "provider": "openai", "max_tier": "Internal"},
        {"model": "anthropic/claude-opus-4", "provider": "anthropic", "max_tier": "Internal"},
        {"model": "gemini/gemini-2.5-pro", "provider": "google", "max_tier": "Internal"},
        {"model": "xai/grok-4", "provider": "xai", "max_tier": "Internal"},
        {"model": "mistral/mistral-large-latest", "provider": "mistral", "max_tier": "Internal"},
        {"model": "on_prem/llama-3.3-70b-instruct", "provider": "vllm-on-prem", "max_tier": "Restricted"},
    ],
    "classify": [
        {"model": "gemini/gemini-2.5-flash", "provider": "google", "max_tier": "Internal"},
        {"model": "xai/grok-4-fast", "provider": "xai", "max_tier": "Internal"},
        {"model": "on_prem/qwen2.5:7b", "provider": "ollama-on-prem", "max_tier": "Restricted"},
    ],
    "general": [
        {"model": "anthropic/claude-sonnet-4", "provider": "anthropic", "max_tier": "Internal"},
        {"model": "gemini/gemini-2.5-pro", "provider": "google", "max_tier": "Internal"},
        {"model": "openai/gpt-5", "provider": "openai", "max_tier": "Internal"},
        {"model": "xai/grok-4", "provider": "xai", "max_tier": "Internal"},
        {"model": "perplexity/sonar-pro", "provider": "perplexity", "max_tier": "Public"},
        {"model": "mistral/mistral-large-latest", "provider": "mistral", "max_tier": "Internal"},
        {"model": "on_prem/llama-3.3-70b-instruct", "provider": "vllm-on-prem", "max_tier": "Restricted"},
    ],
}


def select_route(
    *,
    task_type: str = "general",
    data_classification: str = "Internal",
    tier: int = 2,
) -> dict[str, Any]:
    """Select primary model, fallback chain, and residency policy from Tier & Data Classification."""
    norm_task = task_type.strip().lower() if task_type else "general"
    if norm_task not in _ON_PREM_CATALOG:
        norm_task = "general"
    norm_class = data_classification.strip().title() if data_classification else "Internal"
    if norm_class not in ("Public", "Internal", "Confidential", "Restricted"):
        norm_class = "Confidential"
    norm_tier = int(tier)

    on_prem_only = norm_class in ("Restricted", "Confidential") or norm_tier >= 3
    if on_prem_only:
        primary = _ON_PREM_CATALOG[norm_task]
        fallbacks = [
            primary,
            _ON_PREM_CATALOG["general"],
        ]
        # Deduplicate while preserving order
        seen: set[str] = set()
        chain = [item for item in fallbacks if not (item["model"] in seen or seen.add(item["model"]))]
        reason = (
            f"Data classification `{norm_class}` / Tier `{norm_tier}` requires strict on-prem residency; "
            "external cloud APIs are blocked."
        )
    else:
        raw_chain = list(_CLOUD_FALLBACK_CHAINS[norm_task])
        if norm_class == "Internal":
            # Exclude live web-search models (max_tier == Public) for Internal proprietary prompts
            chain = [
                {"model": item["model"], "provider": item["provider"]}
                for item in raw_chain
                if item.get("max_tier") != "Public"
            ]
        else:
            chain = [{"model": item["model"], "provider": item["provider"]} for item in raw_chain]
        primary = chain[0]
        reason = (
            f"Data classification `{norm_class}` / Tier `{norm_tier}` permits vetted commercial "
            "multi-provider routing (excluding live web-search endpoints on Internal data) with "
            "permissive open-weight on-prem fallback."
        )

    return {
        "task_type": norm_task,
        "data_classification": norm_class,
        "tier": norm_tier,
        "cloud_allowed": not on_prem_only,
        "primary": primary,
        "fallback_chain": chain,
        "reason": reason,
    }


def build_litellm_config(route: dict[str, Any]) -> dict[str, Any]:
    """Build a LiteLLM-compatible router config dictionary for the selected route."""
    group_name = f"trellis-{route['task_type']}-{'onprem' if not route['cloud_allowed'] else 'resilient'}"
    model_list = []
    for entry in route["fallback_chain"]:
        api_base = "http://127.0.0.1:11434" if entry["model"].startswith("on_prem/") else None
        litellm_params: dict[str, Any] = {
            "model": entry["model"].replace("on_prem/", "ollama/"),
        }
        if api_base:
            litellm_params["api_base"] = api_base
        model_list.append({"model_name": group_name, "litellm_params": litellm_params})
    return {
        "model_list": model_list,
        "router_settings": {
            "routing_strategy": "simple-shuffle",
            "num_retries": 2,
            "timeout": 30,
            "allowed_fails": 2,
        },
    }


def tool_trellis_route_model(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """MCP tool implementing Tier/Classification-based Multi-AI routing ([REQ-TRL-11])."""
    data_class = str(args.get("data_classification", "")).strip()
    if not data_class:
        return _err("`data_classification` is required for trellis_route_model.")
    task_type = str(args.get("task_type", "general")).strip() or "general"
    tier = int(args.get("tier", 2))
    emit_litellm = bool(args.get("emit_litellm_config", False))

    route = select_route(task_type=task_type, data_classification=data_class, tier=tier)
    chain_lines = "\n".join(
        f"{idx}. `{item['model']}` ({item['provider']})"
        for idx, item in enumerate(route["fallback_chain"], start=1)
    )
    extra = ""
    if emit_litellm:
        cfg_json = json.dumps(build_litellm_config(route), indent=2)
        extra = f"\n## LiteLLM Router Config\n```json\n{cfg_json}\n```\n"

    return _ok(
        f"""# Trellis Policy-Driven Model Router (`[REQ-TRL-11]`)

- **Task Type:** `{route['task_type']}`
- **Data Classification:** **{route['data_classification']}**
- **AI Boundary Tier:** `Tier {route['tier']}`
- **Cloud API Allowed:** `{route['cloud_allowed']}`
- **Primary Model:** `{route['primary']['model']}` (`{route['primary']['provider']}`)
- **Rationale:** {route['reason']}

## Fallback Chain
{chain_lines}
{extra}"""
    )
