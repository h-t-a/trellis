"""Stateful Multi-AI pipeline, loop detection, multi-model synthesis, and A2A Agent Card ([REQ-TRL-12, 13])."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from trellis_mcp import __version__
from trellis_mcp.identity import resolve_approver_from_args
from trellis_mcp.tools import _err, _ok

PIPELINE_STAGES: tuple[str, ...] = ("research", "plan", "spec", "implement", "review", "deploy")
_HUMAN_GATED_STAGES = {"implement", "deploy"}
_WORD_RE = re.compile(r"[a-z0-9_.-]{3,}")
_NEGATION_RE = re.compile(r"\b(no|not|never|avoid|block|disable|refuse|cannot|shouldn't|don't)\b", re.IGNORECASE)
_AFFIRM_RE = re.compile(r"\b(yes|enable|allow|keep|default|recommend|should|must)\b", re.IGNORECASE)


def build_a2a_agent_card(base_url: str) -> dict[str, Any]:
    """Return an A2A-compatible Agent Card describing Trellis capabilities ([REQ-TRL-13])."""
    clean_base = base_url.rstrip("/")
    return {
        "name": "trellis-mcp",
        "description": "Governance-first Agentic Engineering & Multi-AI Collaboration MCP Server.",
        "url": f"{clean_base}/mcp",
        "version": __version__,
        "protocol": "a2a-0.2+mcp",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True,
            "humanInTheLoop": True,
            "vmfKnowledgeSearch": True,
        },
        "authentication": {
            "schemes": ["Bearer"],
        },
        "skills": [
            {"id": "pb-plan", "name": "Implementation Plan & Tier Gate"},
            {"id": "pb-spec", "name": "Spec-Driven Development"},
            {"id": "pb-enhance", "name": "Complexity & Little's Law Analyzer"},
            {"id": "pb-rca", "name": "9-Step Fast Root Cause Analysis"},
            {"id": "pb-review", "name": "Pre-PR Governance & Cross-Model Review"},
            {"id": "trellis-search-knowledge", "name": "vMF Semantic Search & Anomaly Gate"},
            {"id": "trellis-route-model", "name": "Tier & Classification Model Router"},
            {"id": "trellis-synthesize", "name": "Multi-Model Consensus & Divergence Synthesis"},
        ],
    }


def tool_trellis_pipeline(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Validate and advance the stateful pb-pipeline workflow ([REQ-TRL-12])."""
    current_stage = str(args.get("current_stage", "")).strip().lower()
    target_stage = str(args.get("target_stage", "")).strip().lower()
    if current_stage not in PIPELINE_STAGES or target_stage not in PIPELINE_STAGES:
        return _err(
            f"Stages must be one of: {', '.join(PIPELINE_STAGES)}."
        )

    tier = int(args.get("tier", 2))
    human_approved = bool(args.get("human_approved", False))
    history = [str(item) for item in (args.get("history") or [])]
    max_steps = max(1, int(args.get("max_steps", 12)))
    writer_model = str(args.get("writer_model", "")).strip()
    reviewer_model = str(args.get("reviewer_model", "")).strip()
    cross_model_review = bool(args.get("cross_model_review", True))
    approver = resolve_approver_from_args(args, workspace_root)

    counts = Counter(history)
    repeated_step = next((step for step, cnt in counts.items() if cnt >= 3), None)
    if repeated_step or len(history) >= max_steps:
        reason = (
            f"Step `{repeated_step}` repeated {counts[repeated_step]} times."
            if repeated_step
            else f"Execution reached max_steps={max_steps}."
        )
        return _ok(
            f"""# Trellis Pipeline State (`[REQ-TRL-12]`)

- **Status:** **LOOP_DETECTED**
- **Current Stage:** `{current_stage}` -> **Target:** `{target_stage}`
- **Approver / Operator:** `{approver.name}` (`{approver.source}`)
- **Reason:** {reason}
- **Action Required:** Halt automated retries and escalate to human operator (`{approver.name}`).
"""
        )

    if target_stage in _HUMAN_GATED_STAGES and tier >= 2 and not human_approved:
        return _ok(
            f"""# Trellis Pipeline State (`[REQ-TRL-12]`)

- **Status:** **PAUSED_FOR_APPROVAL**
- **Transition:** `{current_stage}` -> `{target_stage}`
- **AI Boundary Tier:** `Tier {tier}`
- **Approver:** `{approver.name}` (`{approver.source}`)
- **Action Required:** Human approval (`human_approved=true`) from `{approver.name}` is mandatory before entering `{target_stage}`.
"""
        )

    if (
        target_stage == "review"
        and cross_model_review
        and writer_model
        and reviewer_model
        and writer_model.lower() == reviewer_model.lower()
    ):
        return _err(
            f"Cross-model review violation (`[REQ-TRL-13]`): `reviewer_model` (`{reviewer_model}`) "
            f"must differ from `writer_model` (`{writer_model}`)."
        )

    return _ok(
        f"""# Trellis Pipeline State (`[REQ-TRL-12]`)

- **Status:** **READY_TO_ADVANCE**
- **Transition:** `{current_stage}` -> `{target_stage}`
- **AI Boundary Tier:** `Tier {tier}` (Human Approved: `{human_approved}`)
- **Approver:** `{approver.name}` (`{approver.source}`)
- **Writer Model:** `{writer_model or "unspecified"}` | **Reviewer Model:** `{reviewer_model or "unspecified"}`
- **History Steps:** `{len(history)}/{max_steps}`
"""
    )


def _stance_label(text: str) -> str:
    has_neg = bool(_NEGATION_RE.search(text))
    has_pos = bool(_AFFIRM_RE.search(text))
    if has_neg and not has_pos:
        return "negative/cautious"
    if has_pos and not has_neg:
        return "affirmative"
    return "mixed/conditional"


def tool_trellis_synthesize(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Synthesize multi-model outputs into consensus, divergences, confidence, and citations ([REQ-TRL-13])."""
    prompt = str(args.get("prompt", "")).strip()
    responses = list(args.get("responses") or [])
    if not prompt or len(responses) < 1:
        return _err("`prompt` and at least one entry in `responses` are required for trellis_synthesize.")

    normalized: list[dict[str, Any]] = []
    token_sets: list[set[str]] = []
    all_citations: list[str] = []
    confidences: list[float] = []

    for item in responses:
        if not isinstance(item, dict):
            continue
        model = str(item.get("model", "unknown")).strip() or "unknown"
        answer = str(item.get("answer", "")).strip()
        conf = float(item.get("confidence", 0.5))
        citations = [str(c) for c in (item.get("citations") or []) if str(c).strip()]
        stance = _stance_label(answer)
        normalized.append(
            {
                "model": model,
                "answer": answer,
                "confidence": max(0.0, min(1.0, conf)),
                "citations": citations,
                "stance": stance,
            }
        )
        token_sets.append(set(_WORD_RE.findall(answer.lower())))
        all_citations.extend(citations)
        confidences.append(max(0.0, min(1.0, conf)))

    if not normalized:
        return _err("At least one valid response object is required.")

    # Compute consensus terms (present in >=2 models) and pairwise divergences
    term_freq: Counter[str] = Counter()
    for tset in token_sets:
        for tok in tset:
            term_freq[tok] += 1
    shared_terms = sorted(tok for tok, cnt in term_freq.items() if cnt >= min(2, len(normalized)))

    divergences: list[str] = []
    stances = {r["stance"] for r in normalized}
    if len(stances) > 1:
        stance_summary = "; ".join(f"`{r['model']}` -> {r['stance']}" for r in normalized)
        divergences.append(f"Stance divergence detected: {stance_summary}")

    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            union = token_sets[i] | token_sets[j]
            jaccard = (len(token_sets[i] & token_sets[j]) / len(union)) if union else 1.0
            if jaccard < 0.35:
                divergences.append(
                    f"Low lexical overlap (`{jaccard:.2f}`) between `{normalized[i]['model']}` and `{normalized[j]['model']}`."
                )

    avg_conf = sum(confidences) / len(confidences)
    unique_citations = list(dict.fromkeys(all_citations))
    model_rows = "\n".join(
        f"| `{r['model']}` | `{r['stance']}` | `{r['confidence']:.2f}` | {', '.join(r['citations']) or 'none'} | {r['answer'][:140]} |"
        for r in normalized
    )
    div_block = "\n".join(f"- {d}" for d in divergences) if divergences else "- Models are broadly aligned."
    consensus_text = ", ".join(f"`{t}`" for t in shared_terms[:12]) if shared_terms else "none"

    return _ok(
        f"""# Trellis Multi-Model Synthesis (`[REQ-TRL-13]`)

- **Prompt:** {prompt}
- **Models Compared:** `{len(normalized)}` | **Mean Confidence:** `{avg_conf:.2f}`
- **Consensus Topics:** {consensus_text}
- **Aggregated Citations:** {', '.join(f'`{c}`' for c in unique_citations) if unique_citations else 'none'}

## Model Perspectives
| Model | Stance | Confidence | Citations | Summary |
| :--- | :--- | :--- | :--- | :--- |
{model_rows}

## Divergences & Disagreements
{div_block}
"""
    )
