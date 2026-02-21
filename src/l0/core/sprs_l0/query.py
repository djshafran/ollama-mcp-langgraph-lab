from __future__ import annotations

import os
from typing import Any, Callable


def _unique_terms(tokens: list[dict[str, Any]], max_terms: int) -> list[str]:
    terms: list[str] = []
    for token in tokens:
        candidates = [token.get("lemma"), token.get("surface")]
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            term = candidate.strip()
            if not term or term in terms:
                continue
            terms.append(term)
            if len(terms) >= max_terms:
                return terms
    return terms


def build_kag_query(
    *,
    text: str | None = None,
    spir: dict[str, Any] | None = None,
    analyzer: Callable[[str], dict[str, Any]] | None = None,
    max_terms: int = 12,
) -> dict[str, Any]:
    working_spir = spir
    if working_spir is None and text and analyzer:
        working_spir = analyzer(text)
    if working_spir is None:
        raise ValueError("Either spir or (text + analyzer) must be provided")

    tokens = working_spir.get("tokens") or []
    terms = _unique_terms(tokens, max_terms=max_terms)

    norms = (((working_spir.get("semantics") or {}).get("kag") or {}).get("norms")) or []
    modalities = sorted({str(norm.get("modality")) for norm in norms if norm.get("modality")})

    filters = {
        "version": (working_spir.get("meta") or {}).get("version"),
        "artifacts_hash": (working_spir.get("meta") or {}).get("artifacts_hash"),
        "layers": ["paninian", "ud", "kag"],
    }
    kag_query = {
        "terms": terms,
        "modalities": modalities,
        "target": "event_deontic",
        "raw": text or (working_spir.get("normalized_text") or ""),
    }
    retrieval_plan = {
        "bm25_terms": terms,
        "vector_query": " ".join(terms),
        "fusion": "rrf",
        "rerank": "lexical_cross",
        "backend": os.getenv("RETRIEVAL_BACKEND", "baseline"),
        "filters": filters,
    }
    return {
        "kag_query": kag_query,
        "retrieval_plan": retrieval_plan,
        "query_hash": (working_spir.get("meta") or {}).get("input_hash"),
    }


def query_understand(
    *,
    text: str | None = None,
    spir: dict[str, Any] | None = None,
    analyzer: Callable[[str], dict[str, Any]] | None = None,
    max_terms: int = 12,
) -> dict[str, Any]:
    return build_kag_query(
        text=text,
        spir=spir,
        analyzer=analyzer,
        max_terms=max_terms,
    )
