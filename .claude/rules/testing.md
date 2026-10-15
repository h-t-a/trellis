# Rule: Testing Discipline

**Canonical Sources:**
- [Testing Standard](../../docs/standards/testing-standard.md)
- [Performance Testing & SLA Standard](../../docs/standards/performance-sla.md)
- [AI Boundary Standard](../../docs/standards/ai-boundary.md)

## Summary Checklist (`[DRAFT]`)

1. **Never Delete, Skip, or Weaken Tests (Tier 3 Prohibition):**
   - AI must **never** delete, skip (`.skip`, `@Ignore`, `@Disabled`), or weaken an existing test or assertion to make a build pass.
2. **Failing Test First (Red -> Green):**
   - Every new behavior or bug fix must include a test that **fails before the code change** and **passes after the change**.
3. **Meaningful Assertions & Requirement Traceability:**
   - Every test must state the requirement or bug scenario it verifies.
   - A human must review every AI-written test to confirm its assertions verify real behavior rather than trivially passing.
4. **Synthetic Data Only:**
   - Never use real customer or production data in test fixtures (Tier 3 prohibition).
5. **Performance Testing Accuracy:**
   - Report latency as **percentiles (`p50`, `p95`, `p99`)** alongside **error rate**, never averages alone.
   - Size virtual users with Little's Law ($\text{VUs} \approx \text{TPS} \times (\text{Response Time} + \text{Think Time})$) and hold target load for the sustained SLA window (see [performance-sla.md](../../docs/standards/performance-sla.md)).
