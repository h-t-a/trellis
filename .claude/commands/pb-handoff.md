---
name: pb-handoff
description: Save a compact (under 40 lines) session state handoff summary before starting a new conversation or splitting a Class L epic. Invoke as /pb-handoff.
---

# Skill: `/pb-handoff` — Compact Session State Handoff

**Canonical Standard:** [docs/standards/quota-efficiency.md](../../docs/standards/quota-efficiency.md)

## When to Use
- Prefer built-in **`/compact`** when continuing the *same* Class M task in-session.
- Use **`/pb-handoff`** (or call `trellis_handoff` on `@trellis-mcp`) when closing a sub-task of a Class L epic or switching sessions.

## Execution Steps

1. **Generate a Compact Handoff Summary (Strictly ≤ 40 Lines):**
   - Include only these 5 sections:
     1. **Objective & Spec/Ticket ID** (`SPEC-NNN` / `[REQ-NNN-XX]`)
     2. **Completed & Verified** (commits, passing tests)
     3. **Key Decisions & Constraints** (1 line each)
     4. **Next Immediate Steps** (numbered, max 3 items)
     5. **Exact Files to `@`-Mention in Next Session** (relative paths only; never `.env` or secrets)
2. **Save Location:**
   - Write to `.agents/scratch/handoff-latest.md` (or output inline if requested) so the next session can attach `@.agents/scratch/handoff-latest.md` with minimal token overhead.
