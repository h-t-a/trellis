---
name: pb-synthesize
description: Combine independent answers from multiple AI models into an explicit agreement and divergence matrix without silent voting. Invoke as /pb-synthesize.
---

# Skill: `/pb-synthesize` — Multi-AI Consensus & Divergence Matrix

**Canonical Standards:**
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)
- [docs/standards/definition-of-done.md](../../../docs/standards/definition-of-done.md)

## Execution Steps

1. **Collect Independent Model Outputs:**
   - Gather structured answers (`model`, `answer`, optional `confidence` and `citations`) from distinct providers (e.g., Claude, Gemini, GPT, Grok, Perplexity, or local Qwen/Llama).
2. **Synthesize via `trellis_synthesize`:**
   - Call `trellis_synthesize` with `prompt` and `responses`.
   - Never collapse disagreements by silent majority vote; surface explicit **Agreements**, **Divergences**, confidence spread, and cited evidence.
3. **Human Escalation on High Divergence:**
   - When models conflict on security, financial logic, or architectural trade-offs, present the divergence table to the named human reviewer (resolved via `git config user.name` or active user) for the final decision.
