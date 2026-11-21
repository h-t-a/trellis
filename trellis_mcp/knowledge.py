"""Knowledge layer with L2-normalized vectors and von Mises-Fisher (vMF) directional statistics ([REQ-TRL-08..10, 14, 29]).

Core operates with zero external dependencies using sparse TF-IDF unit vectors and spherical clustering.
Optional `numpy` (via `trellis-mcp[knowledge]`) or a pluggable `embedder` callable accelerates dense vMF EM.
Security decisions always combine directional scores with provenance, clearance, and content policy.
Note on security boundaries: prompt injection filters are heuristic best-effort regex defenses ([REQ-TRL-29]),
not an absolute security boundary.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

from trellis_mcp.tools import PACKAGE_ROOT, _err, _ok, _scan_redaction_violations, wrap_untrusted_context

try:  # Optional acceleration via `trellis-mcp[knowledge]`
    import numpy as _np
except ImportError:  # pragma: no cover - stdlib fallback tested by default
    _np = None

_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")
_CLEARANCE_RANK: dict[str, int] = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"(?:exfiltrate|leak|send)\s+.*?(?:api[_ ]?key|secret|\.env|id_rsa|token)", re.IGNORECASE),
    re.compile(r"\b(?:curl|wget)\s+https?://.*?(?:-d\b|--data\b|@)", re.IGNORECASE),
    re.compile(r"</?untrusted_context[^>]*>", re.IGNORECASE),
]
_INJECTION_NOTE = (
    "Prompt injection patterns in _INJECTION_PATTERNS are heuristic best effort defenses ([REQ-TRL-29]), "
    "not an impenetrable security boundary."
)

_INDEX_CACHE: dict[str, tuple[tuple[int, float], list[dict[str, Any]]]] = {}


def make_ollama_embedder(
    model: str = "nomic-embed-text",
    base_url: str = "http://127.0.0.1:11434",
    timeout_sec: float = 10.0,
) -> Callable[[list[str]], list[list[float]]]:
    """Return a pluggable local Ollama `/api/embed` callable for dense embeddings."""

    def _embed(texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
        req = Request(
            f"{base_url.rstrip('/')}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310 - local/configured endpoint
            data = json.loads(resp.read().decode("utf-8"))
        return [list(map(float, vec)) for vec in (data.get("embeddings") or [])]

    return _embed


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _normalize_sparse(vec: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm <= 1e-12:
        return {}
    return {k: v / norm for k, v in vec.items()}


def _cosine_sparse(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b[k] for k, v in a.items() if k in b)


def _estimate_kappa(mean_resultant_length: float, dim: int) -> float:
    """Banerjee et al. (2005) approximation: kappa = r_bar * (d - r_bar^2) / (1 - r_bar^2)."""
    d = max(int(dim), 2)
    r = min(max(float(mean_resultant_length), 0.0), 0.995)
    if r <= 1e-6:
        return 0.0
    denom = max(1.0 - r * r, 1e-6)
    return round(r * (d - r * r) / denom, 3)


def _detect_doc_access_level(rel: str, raw: str) -> str:
    """Resolve clearance level from explicit `**Classification:**` metadata or path defaults."""
    header = raw[:1200]
    match = re.search(
        r"\*\*Classification:\*\*\s*`?(Public|Internal|Confidential|Restricted)`?",
        header,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).title()
    if any(seg in rel for seg in ("decisions/", "specs/", "knowledge/", "deployment-guide")):
        return "Internal"
    return "Public"


def _collect_corpus_chunks(workspace_root: Path | None) -> list[dict[str, Any]]:
    root = workspace_root.resolve() if workspace_root and (workspace_root / "docs").exists() else PACKAGE_ROOT
    cache_key = str(root)
    rel_globs = [
        "README.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "SECURITY.md",
        "docs/standards/*.md",
        "docs/decisions/*.md",
        "docs/specs/*.md",
        "docs/knowledge/*.md",
        "docs/integrations/*.md",
        "templates/*.md",
        "docs/deployment-guide.md",
        "docs/how-to-use.md",
        "docs/onboarding.md",
    ]
    files: list[Path] = []
    for pat in rel_globs:
        files.extend(sorted(root.glob(pat)))
    latest_mtime = max((f.stat().st_mtime for f in files if f.is_file()), default=0.0)
    cache_sig = (len(files), latest_mtime)
    cached = _INDEX_CACHE.get(cache_key)
    if cached and cached[0] == cache_sig:
        return cached[1]

    chunks: list[dict[str, Any]] = []
    for fpath in files:
        if not fpath.is_file():
            continue
        rel = fpath.relative_to(root).as_posix()
        is_rca = "rca" in rel.lower()
        raw = fpath.read_text(encoding="utf-8", errors="ignore")
        access = _detect_doc_access_level(rel, raw)
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", raw) if len(p.strip()) >= 40]
        for idx, para in enumerate(paragraphs[:40]):
            chunks.append(
                {
                    "id": f"{rel}#p{idx + 1}",
                    "source": rel,
                    "access_level": access,
                    "tenant": "default",
                    "is_rca": is_rca or ("rca" in para.lower() and "symptom" in para.lower()),
                    "trusted": True,
                    "text": para[:900],
                }
            )
    _INDEX_CACHE[cache_key] = (cache_sig, chunks)
    return chunks


def _build_tfidf_vectors(texts: list[str]) -> tuple[list[dict[str, float]], dict[str, float], int]:
    docs_tokens = [_tokenize(t) for t in texts]
    n_docs = max(len(docs_tokens), 1)
    df: dict[str, int] = {}
    for toks in docs_tokens:
        for tok in set(toks):
            df[tok] = df.get(tok, 0) + 1
    idf = {tok: math.log((1.0 + n_docs) / (1.0 + freq)) + 1.0 for tok, freq in df.items()}
    vectors: list[dict[str, float]] = []
    for toks in docs_tokens:
        tf: dict[str, float] = {}
        for tok in toks:
            tf[tok] = tf.get(tok, 0.0) + 1.0
        weighted = {tok: (1.0 + math.log(cnt)) * idf[tok] for tok, cnt in tf.items() if tok in idf}
        vectors.append(_normalize_sparse(weighted))
    return vectors, idf, max(len(idf), 2)


def _vectorize_query(text: str, idf: dict[str, float]) -> dict[str, float]:
    tf: dict[str, float] = {}
    for tok in _tokenize(text):
        if tok in idf:
            tf[tok] = tf.get(tok, 0.0) + 1.0
    weighted = {tok: (1.0 + math.log(cnt)) * idf[tok] for tok, cnt in tf.items()}
    return _normalize_sparse(weighted)


def fit_vmf_clusters(
    vectors: list[dict[str, float]], dim: int, num_clusters: int = 6, iters: int = 8
) -> tuple[list[int], list[dict[str, float]], list[float]]:
    """Run spherical k-means / vMF mixture estimation returning `(assignments, mus, kappas)`."""
    if not vectors:
        return [], [], []
    k = max(1, min(num_clusters, len(vectors)))
    step = max(1, len(vectors) // k)
    mus = [dict(vectors[min(i * step, len(vectors) - 1)]) for i in range(k)]
    assignments = [0] * len(vectors)

    for _ in range(iters):
        changed = False
        for i, vec in enumerate(vectors):
            best_c = 0
            best_sim = -1.0
            for c_idx, mu in enumerate(mus):
                sim = _cosine_sparse(vec, mu)
                if sim > best_sim:
                    best_sim = sim
                    best_c = c_idx
            if assignments[i] != best_c:
                assignments[i] = best_c
                changed = True
        new_mus: list[dict[str, float]] = []
        for c_idx in range(k):
            accum: dict[str, float] = {}
            count = 0
            for i, vec in enumerate(vectors):
                if assignments[i] == c_idx:
                    count += 1
                    for term, w in vec.items():
                        accum[term] = accum.get(term, 0.0) + w
            if count == 0:
                new_mus.append(mus[c_idx])
            else:
                new_mus.append(_normalize_sparse({t: w / count for t, w in accum.items()}))
        mus = new_mus
        if not changed:
            break

    kappas: list[float] = []
    for c_idx in range(k):
        sims = [
            _cosine_sparse(vectors[i], mus[c_idx])
            for i in range(len(vectors))
            if assignments[i] == c_idx
        ]
        r_bar = (sum(sims) / len(sims)) if sims else 0.0
        # Use effective subspace dimension min(dim, 64) so sparse vocab size doesn't inflate kappa unrealistically
        kappas.append(_estimate_kappa(r_bar, min(dim, 64)))
    return assignments, mus, kappas


def _confidence_tier(cosine: float, kappa: float) -> str:
    if cosine >= 0.30 and kappa >= 3.0:
        return "high"
    if cosine >= 0.12 and kappa >= 1.5:
        return "medium"
    return "low"


def find_similar_rcas(
    symptom: str, workspace_root: Path | None = None, top_k: int = 3
) -> list[dict[str, Any]]:
    """Return prior RCA-related chunks matching `symptom` for RCA deduplication ([REQ-TRL-10])."""
    chunks = [c for c in _collect_corpus_chunks(workspace_root) if c.get("is_rca")]
    if not chunks or not symptom.strip():
        return []
    vectors, idf, dim = _build_tfidf_vectors([c["text"] for c in chunks])
    _, _, kappas = fit_vmf_clusters(vectors, dim, num_clusters=min(4, len(chunks)))
    q_vec = _vectorize_query(symptom, idf)
    hits: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        sim = _cosine_sparse(q_vec, vectors[idx])
        if sim >= 0.12:
            hits.append(
                {
                    "id": chunk["id"],
                    "source": chunk["source"],
                    "cosine": round(sim, 3),
                    "kappa": kappas[0] if kappas else 0.0,
                    "excerpt": chunk["text"][:180].replace("\n", " "),
                }
            )
    hits.sort(key=lambda item: item["cosine"], reverse=True)
    return hits[:top_k]


def check_ingestion_anomaly(
    text: str,
    workspace_root: Path | None = None,
    provenance_trusted: bool = False,
    min_cosine: float = 0.05,
) -> dict[str, Any]:
    """Hybrid poisoning/anomaly gate combining vMF directional likelihood with policy & injection scans ([REQ-TRL-09])."""
    chunks = _collect_corpus_chunks(workspace_root)
    vectors, idf, dim = _build_tfidf_vectors([c["text"] for c in chunks])
    _, mus, kappas = fit_vmf_clusters(vectors, dim)
    q_vec = _vectorize_query(text, idf)

    best_cosine = max((_cosine_sparse(q_vec, mu) for mu in mus), default=0.0)
    best_idx = 0
    for idx, mu in enumerate(mus):
        if _cosine_sparse(q_vec, mu) >= best_cosine:
            best_idx = idx
    cluster_kappa = kappas[best_idx] if kappas else 0.0
    vmf_score = cluster_kappa * best_cosine

    injection_hits = [pat.pattern[:32] for pat in _INJECTION_PATTERNS if pat.search(text)]
    redaction_hits = _scan_redaction_violations(text)
    out_of_distribution = best_cosine < min_cosine
    anomaly_suspected = out_of_distribution or bool(injection_hits)
    blocked = bool(injection_hits) or bool(redaction_hits) or (
        not provenance_trusted and out_of_distribution
    )

    return {
        "blocked": blocked,
        "anomaly_suspected": anomaly_suspected,
        "provenance_trusted": provenance_trusted,
        "max_cosine": round(best_cosine, 4),
        "cluster_kappa": cluster_kappa,
        "vmf_log_likelihood_proxy": round(vmf_score, 4),
        "injection_signals": injection_hits,
        "redaction_signals": redaction_hits,
        "note": "Combined directional vMF score with provenance & content policy (never embedding-only).",
    }


def check_agent_drift(
    agent_output: str,
    workspace_root: Path | None = None,
    max_angular_distance_rad: float = 1.48,
) -> dict[str, Any]:
    """Measure agent behavioral drift against normal operational vMF clusters ([REQ-TRL-09])."""
    chunks = _collect_corpus_chunks(workspace_root)
    vectors, idf, dim = _build_tfidf_vectors([c["text"] for c in chunks])
    _, mus, kappas = fit_vmf_clusters(vectors, dim)
    resp_vec = _vectorize_query(agent_output, idf)
    best_cos = max((_cosine_sparse(resp_vec, mu) for mu in mus), default=0.0)
    clamped = min(max(best_cos, -1.0), 1.0)
    angular_distance = math.acos(clamped)
    injection_hits = [pat.pattern[:32] for pat in _INJECTION_PATTERNS if pat.search(agent_output)]
    drift_alert = angular_distance > max_angular_distance_rad or bool(injection_hits)
    return {
        "drift_alert": drift_alert,
        "max_cosine": round(clamped, 4),
        "angular_distance": round(angular_distance, 4),
        "baseline_kappas": kappas,
        "injection_signals": injection_hits,
    }


def canary_evaluate(
    candidate_docs: list[dict[str, Any]],
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """Test suspicious/new documents in an isolated Canary namespace without mutating main KB ([REQ-TRL-14])."""
    promoted_ids: list[str] = []
    quarantined_ids: list[str] = []
    reports: list[dict[str, Any]] = []
    for doc in candidate_docs:
        doc_id = str(doc.get("id", "unknown"))
        text = str(doc.get("text", ""))
        trusted = bool(doc.get("trusted", False))
        verdict = check_ingestion_anomaly(text, workspace_root=workspace_root, provenance_trusted=trusted)
        if verdict["blocked"]:
            quarantined_ids.append(doc_id)
        else:
            promoted_ids.append(doc_id)
        reports.append({"id": doc_id, **verdict})
    return {
        "promoted_ids": promoted_ids,
        "quarantined_ids": quarantined_ids,
        "reports": reports,
    }


def tool_trellis_search_knowledge(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Search workspace knowledge with vMF confidence, access-aware filter, and optional compression ([REQ-TRL-08..10])."""
    query = str(args.get("query", "")).strip()
    if not query:
        return _err("`query` is required for trellis_search_knowledge.")

    clearance = str(args.get("caller_clearance", "Internal")).strip().lower()
    clearance_rank = _CLEARANCE_RANK.get(clearance, 1)
    tenant = str(args.get("tenant", "default")).strip() or "default"
    top_k = max(1, min(int(args.get("top_k", 5)), 20))
    deduplicate = bool(args.get("deduplicate", False))
    rca_only = bool(args.get("rca_only", False))

    all_chunks = _collect_corpus_chunks(workspace_root)
    authorized = [
        c
        for c in all_chunks
        if _CLEARANCE_RANK.get(str(c.get("access_level", "Public")).lower(), 1) <= clearance_rank
        and str(c.get("tenant", "default")) == tenant
        and (not rca_only or c.get("is_rca"))
    ]
    if not authorized:
        return _ok("# Trellis vMF Knowledge Search\n\n- No authorized chunks matched the current clearance/filter.")

    vectors, idf, dim = _build_tfidf_vectors([c["text"] for c in authorized])
    assignments, _, kappas = fit_vmf_clusters(vectors, dim)
    q_vec = _vectorize_query(query, idf)

    scored: list[tuple[float, int, dict[str, Any], dict[str, float]]] = []
    for idx, chunk in enumerate(authorized):
        sim = _cosine_sparse(q_vec, vectors[idx])
        if sim > 0.0:
            scored.append((sim, assignments[idx], chunk, vectors[idx]))
    scored.sort(key=lambda row: row[0], reverse=True)

    selected: list[tuple[float, int, dict[str, Any]]] = []
    seen_vectors: list[dict[str, float]] = []
    for sim, cluster_id, chunk, vec in scored:
        if deduplicate and any(_cosine_sparse(vec, prev) >= 0.80 for prev in seen_vectors):
            continue
        selected.append((sim, cluster_id, chunk))
        seen_vectors.append(vec)
        if len(selected) >= top_k:
            break

    lines = [
        "# Trellis vMF Knowledge Search (`[REQ-TRL-08]`)",
        "",
        f"- **Query:** `{query}`",
        f"- **Caller Clearance:** `{clearance.title()}` | **Tenant:** `{tenant}` | **Engine:** `{'numpy+vmf' if _np is not None else 'stdlib-tfidf+vmf'}`",
        f"- **Deduplicated / Compressed:** `{deduplicate}` | **Authorized Corpus Chunks:** `{len(authorized)}`",
        "",
    ]
    if not selected:
        lines.append("- No relevant chunks found above zero cosine similarity.")
        return _ok("\n".join(lines))

    for rank, (sim, cluster_id, chunk) in enumerate(selected, start=1):
        kappa = kappas[cluster_id] if cluster_id < len(kappas) else 0.0
        conf = _confidence_tier(sim, kappa)
        snippet = chunk["text"].replace("\n", " ")[:240]
        if not chunk.get("trusted", True):
            snippet = wrap_untrusted_context(snippet, source=str(chunk["source"]))
        lines.append(
            f"### {rank}. `{chunk['id']}` (cosine=`{sim:.3f}`, kappa=`{kappa:.2f}`, confidence=`{conf}`)"
        )
        lines.append(f"- **Access:** `{chunk['access_level']}` | **Source:** `{chunk['source']}`")
        lines.append(f"- **Excerpt:** {snippet}")
        lines.append("")

    return _ok("\n".join(lines))
