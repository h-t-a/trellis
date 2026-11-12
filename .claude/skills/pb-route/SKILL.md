---
name: pb-route
description: Select legally licensed cloud vs strict on-prem open-weight AI models by task type, AI Boundary Tier, and Data Classification, with optional LiteLLM config generation. Invoke as /pb-route.
---

# Skill: `/pb-route` — Policy-Driven Multi-AI Model Router

**Canonical Standards:**
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)
- [docs/standards/data-classification.md](../../../docs/standards/data-classification.md)
- [docs/standards/ai-bom.json](../../../docs/standards/ai-bom.json)

## Execution Steps

1. **Determine Task & Classification Inputs:**
   - Identify `task_type` (`coding`, `review`, `research`, `classify`, `general`), `data_classification` (`Public`, `Internal`, `Confidential`, `Restricted`), and `tier` (`1`, `2`, `3`).
2. **Route via `trellis_route_model`:**
   - Call `trellis_route_model` (set `emit_litellm_config: true` when generating gateway configs).
   - Verify residency rules:
     - `Restricted` / `Confidential` / `Tier >= 3`: Cloud APIs blocked; routes strictly to commercial open-weight on-prem models (`Apache-2.0` / `Llama 3.3`).
     - `Internal`: Commercial cloud APIs allowed excluding live web-search endpoints (`perplexity/*`).
     - `Public`: Full commercial catalog including web-grounded `perplexity/sonar-pro`, `xai/grok-4`, Gemini, Claude, OpenAI, and Mistral.
3. **Verify License Compliance:**
   - Confirm selected models appear in [docs/standards/ai-bom.json](../../../docs/standards/ai-bom.json) with `commercial_use: true`.
