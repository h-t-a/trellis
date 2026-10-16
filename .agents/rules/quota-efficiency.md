---
trigger: always_on
description: Quota efficiency rules, prompt cache preservation, and S/M/L task class matrix with Tier 1 guard
---

# Antigravity Rule: Quota Efficiency & Task Cost Classes

**Canonical Source of Truth:** [docs/standards/quota-efficiency.md](../../docs/standards/quota-efficiency.md)

## 1. Static S/M/L Task Cost Matrix (`[REQ-QUOTA-01]`)

| Class | Scope & Mandatory AI Boundary Guard | Model & Effort | Gate & Session Rule |
| :---: | :--- | :--- | :--- |
| **S** | 1 file, clear cause, **Tier 1 ONLY** *(never auth, validation, schema, API, CI/CD, or ledger code)* | Fast (`Flash`/`Sonnet`), `low` | No Plan artifact needed; run test once. *(Any Tier 2/3 touch auto-upgrades to M/L.)* |
| **M** | 2–5 files, 1 module, or any 1-file Tier 2 change | Default, `medium` | Inline 4-section Micro-Spec in Plan artifact; keep in 1 warm session (`/compact` if >60%). |
| **L** | Cross-module, schema/architecture change, or SLA perf work | Strong (`Pro`/`Opus`), `high` | Standalone Spec (`docs/specs/NNN-<name>.md`) + Plan approval; split into M tasks via `/pb-handoff`. |

## 2. Fast Quota Guards

- **Target with `@file`:** Start from stack traces or `git diff`, never a repo-wide scan.
- **3-Retry Circuit Breaker:** Stop after **3 consecutive failed hypotheses or test runs** and re-plan (`/grill-me`).
- **Batch Checks:** Run tests and linters once per coherent change set, not after every single edit.
