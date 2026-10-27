"""Local hybrid retrieval over approved BrandGate rules and facts.

Semantic embeddings are generated locally by Sentence Transformers. If that model
is not installed/cached or cannot be loaded, search falls back to keyword ranking
and reports that fallback explicitly; it never reports a failed embedding step as
successful semantic retrieval.
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
from datetime import date
from typing import Any, Iterable

import numpy as np

LOGGER = logging.getLogger(__name__)
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_MODEL: Any = None
_MODEL_LOCK = threading.Lock()
_CACHE_LOCK = threading.Lock()
_EMBEDDING_CACHE: dict[str, np.ndarray] = {}

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOP_WORDS = {
    "a", "an", "and", "or", "the", "of", "to", "for", "in", "on", "at",
    "by", "is", "are", "was", "were", "be", "with", "from", "your", "our",
    "their", "this", "that", "it", "as", "do", "not", "use", "using", "when",
    "what", "which", "can", "could", "should", "would", "has", "have", "had",
}


def _get(record: Any, key: str, default: Any = None) -> Any:
    return record.get(key, default) if isinstance(record, dict) else getattr(record, key, default)


def _as_date_string(value: Any) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else (str(value) if value else None)


def _is_rule_current(rule: Any, today: date) -> bool:
    if _get(rule, "status", "active") != "active":
        return False
    effective = _get(rule, "effective_date")
    return effective is None or effective <= today


def _is_fact_current(fact: Any, today: date) -> bool:
    if _get(fact, "status", "active") != "active":
        return False
    valid_from, valid_until = _get(fact, "valid_from"), _get(fact, "valid_until")
    return (valid_from is None or valid_from <= today) and (valid_until is None or valid_until >= today)


def build_candidates(
    rules: Iterable[Any],
    facts: Iterable[Any] = (),
    include_facts: bool = True,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Convert ORM records into provenance-preserving retrieval candidates."""
    today = today or date.today()
    candidates: list[dict[str, Any]] = []
    for rule in rules:
        if not _is_rule_current(rule, today):
            continue
        rule_code = str(_get(rule, "rule_code", ""))
        title = str(_get(rule, "title", rule_code))
        rule_text = str(_get(rule, "rule_text", ""))
        category = str(_get(rule, "category", "brand_rule"))
        section = _get(rule, "source_section")
        source = str(_get(rule, "source", "Unknown source"))
        retrieval_text = " ".join(part for part in (title, category, rule_text, str(section or "")) if part)
        candidates.append({
            "source_type": "rule",
            "source_id": rule_code,
            "title": title,
            "text": rule_text,
            "retrieval_text": retrieval_text,
            "source": source,
            "source_section": section,
            "category": category,
            "severity": str(_get(rule, "severity", "warning")),
            "status": str(_get(rule, "status", "active")),
            "effective_date": _as_date_string(_get(rule, "effective_date")),
            "valid_from": None,
            "valid_until": None,
        })

    if include_facts:
        for fact in facts:
            if not _is_fact_current(fact, today):
                continue
            code = str(_get(fact, "fact_code", ""))
            name = str(_get(fact, "name", code))
            value = str(_get(fact, "value", ""))
            unit = str(_get(fact, "unit", "") or "")
            title = name
            fact_text = f"Approved fact: {name} = {value} {unit}".strip()
            source = str(_get(fact, "source", "Unknown source"))
            section = _get(fact, "source_section")
            retrieval_text = " ".join(part for part in (title, fact_text, str(section or "")) if part)
            candidates.append({
                "source_type": "fact",
                "source_id": code,
                "title": title,
                "text": fact_text,
                "retrieval_text": retrieval_text,
                "source": source,
                "source_section": section,
                "category": "approved_fact",
                "severity": None,
                "status": str(_get(fact, "status", "active")),
                "effective_date": None,
                "valid_from": _as_date_string(_get(fact, "valid_from")),
                "valid_until": _as_date_string(_get(fact, "valid_until")),
            })
    return candidates


def _tokens(text: str) -> set[str]:
    return {
        token for token in _TOKEN_RE.findall(text.casefold())
        if token not in _STOP_WORDS and len(token) > 1
    }


def keyword_score(query: str, document: str) -> float:
    """Simple, dependency-light lexical overlap score in the range 0..1."""
    query_tokens = _tokens(query)
    doc_tokens = _tokens(document)
    if not query_tokens:
        return 0.0
    overlap = len(query_tokens & doc_tokens) / len(query_tokens)
    # A small boost if the whole query or a useful portion appears literally.
    query_clean = " ".join(_TOKEN_RE.findall(query.casefold()))
    doc_clean = " ".join(_TOKEN_RE.findall(document.casefold()))
    phrase_boost = 0.15 if len(query_clean) >= 8 and query_clean in doc_clean else 0.0
    return float(min(1.0, overlap + phrase_boost))


def rank_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    semantic_scores: dict[str, float] | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Pure ranking function, kept separate so ranking can be tested without a model download."""
    ranked: list[dict[str, Any]] = []
    use_semantic = semantic_scores is not None
    for candidate in candidates:
        key = f"{candidate['source_type']}:{candidate['source_id']}"
        lexical = keyword_score(query, candidate.get("retrieval_text", candidate.get("text", "")))
        semantic = None
        if use_semantic:
            # Sentence Transformer vectors are normalised; dot product is cosine similarity.
            raw_semantic = float(semantic_scores.get(key, 0.0))
            semantic = max(0.0, min(1.0, raw_semantic))
            combined = 0.45 * lexical + 0.55 * semantic
        else:
            combined = lexical
        item = {key_: value for key_, value in candidate.items() if key_ != "retrieval_text"}
        item["keyword_score"] = round(lexical, 4)
        item["semantic_score"] = round(semantic, 4) if semantic is not None else None
        item["combined_score"] = round(float(combined), 4)
        ranked.append(item)

    ranked.sort(key=lambda item: (item["combined_score"], item["keyword_score"]), reverse=True)
    return ranked[:top_k]


def _get_model() -> Any:
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL
        # Import lazily so API startup and keyword-only use do not require a model load.
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(MODEL_NAME)
        return _MODEL


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_model_status() -> dict[str, Any]:
    with _CACHE_LOCK:
        cache_count = len(_EMBEDDING_CACHE)
    return {
        "model_name": MODEL_NAME,
        "model_loaded": _MODEL is not None,
        "cached_embedding_count": cache_count,
    }


def clear_embedding_cache() -> None:
    """Utility for tests or an explicit reindex; not called for every request."""
    with _CACHE_LOCK:
        _EMBEDDING_CACHE.clear()


def _semantic_scores(query: str, candidates: list[dict[str, Any]]) -> dict[str, float]:
    model = _get_model()
    keyed_documents: list[tuple[str, str]] = []
    for candidate in candidates:
        key = f"{candidate['source_type']}:{candidate['source_id']}"
        document_text = candidate.get("retrieval_text", candidate.get("text", ""))
        keyed_documents.append((key, document_text))

    missing_by_hash: dict[str, str] = {}
    for _, document_text in keyed_documents:
        digest = _hash_text(document_text)
        with _CACHE_LOCK:
            is_cached = digest in _EMBEDDING_CACHE
        if not is_cached:
            missing_by_hash[digest] = document_text

    if missing_by_hash:
        texts = list(missing_by_hash.values())
        vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        with _CACHE_LOCK:
            for digest, vector in zip(missing_by_hash.keys(), vectors):
                _EMBEDDING_CACHE[digest] = np.asarray(vector, dtype=np.float32)

    query_vector = model.encode([query], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0]
    score_map: dict[str, float] = {}
    with _CACHE_LOCK:
        for key, document_text in keyed_documents:
            vector = _EMBEDDING_CACHE[_hash_text(document_text)]
            score_map[key] = float(np.dot(vector, query_vector))
    return score_map


def search_sources(
    query: str,
    rules: Iterable[Any],
    facts: Iterable[Any] = (),
    top_k: int = 5,
    include_facts: bool = True,
    use_semantic: bool = True,
    today: date | None = None,
) -> dict[str, Any]:
    """Retrieve approved rule/fact sources using hybrid search with explicit fallback status."""
    candidates = build_candidates(rules, facts, include_facts=include_facts, today=today)
    if not candidates:
        return {
            "retrieval_mode": "keyword_only" if not use_semantic else "keyword_fallback",
            "model_name": None,
            "results": [],
            "warnings": ["No active, currently valid rules or facts were available for retrieval."],
        }

    warnings: list[str] = []
    semantic_scores: dict[str, float] | None = None
    model_name: str | None = None
    retrieval_mode = "keyword_only"
    if use_semantic:
        try:
            semantic_scores = _semantic_scores(query, candidates)
            model_name = MODEL_NAME
            retrieval_mode = "hybrid"
        except Exception as exc:  # Quota-free fallback if a local model cannot load or encode.
            LOGGER.warning("Local semantic retrieval unavailable (%s); using keyword fallback.", type(exc).__name__)
            retrieval_mode = "keyword_fallback"
            warnings.append(
                "The local embedding model could not be loaded or used for this request. "
                "Results use keyword retrieval only. Install the Phase 2 dependencies and allow the model to download once."
            )

    results = rank_candidates(query, candidates, semantic_scores=semantic_scores, top_k=top_k)
    return {
        "retrieval_mode": retrieval_mode,
        "model_name": model_name,
        "results": results,
        "warnings": warnings,
    }
