from __future__ import annotations

from typing import Any


def extract_keys(query_spir: dict[str, Any], max_terms: int = 12) -> dict[str, Any]:
    tokens = query_spir.get("tokens", [])
    terms: list[str] = []
    for token in tokens:
        term = token.get("lemma") or token.get("surface")
        if not term:
            continue
        if term not in terms:
            terms.append(term)
        if len(terms) >= max_terms:
            break
    return {
        "keywords": terms,
        "query": " ".join(terms),
        "lemma_terms": terms,
    }
