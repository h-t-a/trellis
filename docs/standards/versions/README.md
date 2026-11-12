# Versioned Standards

Historical standard snapshots live under this directory:

```text
docs/standards/versions/<standard-name>/<version>.md
```

Register each snapshot in [`../standards.json`](../standards.json) under the standard's `versions` map:

```json
{
  "testing-standard": {
    "version": "0.2",
    "path": "docs/standards/testing-standard.md",
    "versions": {
      "0.1": "docs/standards/versions/testing-standard/0.1.md",
      "0.2": "docs/standards/testing-standard.md"
    }
  }
}
```

Consumers can request a specific version:

```text
trellis_get_standard { "name": "testing-standard", "version": "0.1" }
```

When the source file is unavailable, Trellis falls back to the local offline cache at
`.trellis_cache/standards/` (populate it with `python -m trellis_mcp --sync-cache`).
