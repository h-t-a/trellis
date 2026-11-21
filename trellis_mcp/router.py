"""Tier- and data-classification-driven multi-AI model router + LiteLLM config generator ([REQ-TRL-11, REQ-TRL-28])."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trellis_mcp.tools import PACKAGE_ROOT, _err, _ok

_TASK_PRIORITIES: dict[str, list[str]] = {
    "coding": [
        "anthropic/claude-sonnet-5-5",
        "openai/gpt-5-codex",
        "xai/grok-4-fast",
        "gemini/gemini-2.5-pro",
        "mistral/codestral-latest",
        "on_prem/qwen2.5-coder:32b",
    ],
    "review": [
        "openai/gpt-5",
        "anthropic/claude-opus-5-5",
        "gemini/gemini-2.5-pro",
        "xai/grok-4",
        "mistral/mistral-large-latest",
        "on_prem/llama-3.3-70b-instruct",
    ],
    "research": [
        "perplexity/sonar-pro",
        "perplexity/sonar-reasoning-pro",
        "gemini/gemini-2.5-pro",
        "xai/grok-4",
        "anthropic/claude-sonnet-5-5",
        "on_prem/qwen2.5:32b",
    ],
    "classify": [
        "gemini/gemini-2.5-flash",
        "anthropic/claude-haiku-5-5",
        "xai/grok-4-fast",
        "on_prem/qwen2.5:7b",
    ],
    "general": [
        "anthropic/claude-sonnet-5-5",
        "gemini/gemini-2.5-pro",
        "openai/gpt-5",
        "xai/grok-4",
        "perplexity/sonar-pro",
        "mistral/mistral-large-latest",
        "on_prem/llama-3.3-70b-instruct",
    ],
}

_CATALOG_CACHE: dict[str, Any] = {}


def load_aibom_catalog(workspace_root: Path | None = None) -> dict[str, Any]:
    """Load model catalog dynamically from docs/standards/ai-bom.json ([REQ-TRL-28])."""
    root = (workspace_root or Path.cwd()).resolve()
    cache_key = str(root)
    if cache_key in _CATALOG_CACHE:
        return _CATALOG_CACHE[cache_key]

    aibom_path: Path | None = None
    candidates = [
        root / "docs" / "standards" / "ai-bom.json",
        PACKAGE_ROOT / "docs" / "standards" / "ai-bom.json",
        PACKAGE_ROOT.parent / "docs" / "standards" / "ai-bom.json",
    ]
    for cand in candidates:
        if cand.is_file():
            aibom_path = cand
            break

    models: list[dict[str, Any]] = []
    if aibom_path and aibom_path.is_file():
        try:
            raw = json.loads(aibom_path.read_text(encoding="utf-8"))
            models = raw.get("models", [])
        except Exception:
            models = []

    on_prem: dict[str, dict[str, str]] = {}
    cloud_chains: dict[str, list[dict[str, str]]] = {
        "research": [],
        "coding": [],
        "review": [],
        "classify": [],
        "general": [],
    }
    aliases: dict[str, str] = {}
    models_by_id: dict[str, dict[str, Any]] = {}

    for m in models:
        mid = m.get("id", "")
        if not mid:
            continue
        models_by_id[mid] = m
        provider = m.get("provider", "unknown")
        deployment = m.get("deployment", "")
        max_tier = str(m.get("max_data_tier", "internal")).strip().title()
        tasks = [t.lower() for t in m.get("recommended_tasks", [])]

        # Register alias lookups
        aliases[mid.lower()] = mid
        if "/" in mid:
            aliases[mid.split("/", 1)[1].lower()] = mid
        for al in m.get("aliases", []):
            aliases[str(al).lower()] = mid

        if deployment == "on-prem":
            for task in ("coding", "review", "research", "classify", "general"):
                if task in tasks and task not in on_prem:
                    on_prem[task] = {"model": mid, "provider": provider}
        else:
            for task in ("research", "coding", "review", "classify", "general"):
                if task in tasks:
                    cloud_chains[task].append(
                        {
                            "model": mid,
                            "provider": provider,
                            "max_tier": max_tier,
                        }
                    )

    # Built-in fallbacks if on_prem catalog incomplete
    fallback_on_prem = {
        "coding": {"model": "on_prem/qwen2.5-coder:32b", "provider": "ollama-on-prem"},
        "review": {"model": "on_prem/llama-3.3-70b-instruct", "provider": "vllm-on-prem"},
        "research": {"model": "on_prem/qwen2.5:32b", "provider": "ollama-on-prem"},
        "classify": {"model": "on_prem/qwen2.5:7b", "provider": "ollama-on-prem"},
        "general": {"model": "on_prem/mistral-nemo:12b", "provider": "ollama-on-prem"},
    }
    for k, v in fallback_on_prem.items():
        if k not in on_prem:
            on_prem[k] = v

    # Sort each cloud chain by task priorities, then append on-prem fallback
    for task, chain in cloud_chains.items():
        priority_list = _TASK_PRIORITIES.get(task, [])
        def _sort_key(item: dict[str, str]) -> int:
            m_id = item["model"]
            try:
                return priority_list.index(m_id)
            except ValueError:
                return 100
        chain.sort(key=_sort_key)
        if on_prem.get(task):
            op = on_prem[task]
            chain.append({"model": op["model"], "provider": op["provider"], "max_tier": "Restricted"})

    result = {
        "models": models,
        "models_by_id": models_by_id,
        "on_prem": on_prem,
        "cloud_chains": cloud_chains,
        "aliases": aliases,
    }
    _CATALOG_CACHE[cache_key] = result
    return result


def resolve_model_alias(model_or_alias: str, workspace_root: Path | None = None) -> str:
    """Resolve a model alias (e.g. `claude-sonnet-latest`) to its canonical catalog ID ([REQ-TRL-28])."""
    catalog = load_aibom_catalog(workspace_root)
    clean = model_or_alias.strip().lower()
    return catalog.get("aliases", {}).get(clean, model_or_alias)


def select_route(
    *,
    task_type: str = "general",
    data_classification: str = "Internal",
    tier: int = 2,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """Select primary model, fallback chain, and residency policy from Tier & Data Classification."""
    catalog = load_aibom_catalog(workspace_root)
    on_prem_catalog = catalog["on_prem"]
    cloud_fallback_chains = catalog["cloud_chains"]

    norm_task = task_type.strip().lower() if task_type else "general"
    if norm_task not in on_prem_catalog:
        norm_task = "general"
    norm_class = data_classification.strip().title() if data_classification else "Internal"
    if norm_class not in ("Public", "Internal", "Confidential", "Restricted"):
        norm_class = "Confidential"
    norm_tier = int(tier)

    on_prem_only = norm_class in ("Restricted", "Confidential") or norm_tier >= 3
    if on_prem_only:
        primary = on_prem_catalog[norm_task]
        fallbacks = [
            primary,
            on_prem_catalog["general"],
        ]
        # Deduplicate while preserving order
        seen: set[str] = set()
        chain = [item for item in fallbacks if not (item["model"] in seen or seen.add(item["model"]))]
        reason = (
            f"Data classification `{norm_class}` / Tier `{norm_tier}` requires strict on-prem residency; "
            "external cloud APIs are blocked."
        )
    else:
        raw_chain = list(cloud_fallback_chains.get(norm_task, []))
        if norm_class == "Internal":
            # Exclude live web-search models (max_tier == Public) for Internal proprietary prompts
            chain = [
                {"model": item["model"], "provider": item["provider"]}
                for item in raw_chain
                if item.get("max_tier") != "Public"
            ]
        else:
            chain = [{"model": item["model"], "provider": item["provider"]} for item in raw_chain]
        primary = chain[0] if chain else on_prem_catalog[norm_task]
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
    """MCP tool implementing Tier/Classification-based Multi-AI routing ([REQ-TRL-11, REQ-TRL-28])."""
    data_class = str(args.get("data_classification", "")).strip()
    if not data_class:
        return _err("`data_classification` is required for trellis_route_model.")
    task_type = str(args.get("task_type", "general")).strip() or "general"
    tier = int(args.get("tier", 2))
    emit_litellm = bool(args.get("emit_litellm_config", False))

    route = select_route(
        task_type=task_type,
        data_classification=data_class,
        tier=tier,
        workspace_root=workspace_root,
    )
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
