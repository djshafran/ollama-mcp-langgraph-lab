from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _resolve_corpus_path(
    *, corpus_path: str | Path | None = None, artifacts_dir: str | Path | None = None
) -> Path | None:
    if corpus_path:
        path = Path(corpus_path)
        if path.exists():
            return path

    if artifacts_dir:
        base = Path(artifacts_dir)
        candidates = [
            base / "corpus.jsonl",
            base / "spir_corpus.jsonl",
            base / "corpus_v0_2_0.jsonl",
        ]
        for c in candidates:
            if c.exists():
                return c
        parent = base.parent
        if parent.exists():
            for version_dir in sorted(parent.glob("v*"), reverse=True):
                for name in ("corpus.jsonl", "spir_corpus.jsonl", "corpus_v0_2_0.jsonl"):
                    candidate = version_dir / name
                    if candidate.exists():
                        return candidate
    return None


def _extract_doc_text(row: dict[str, Any]) -> str:
    for key in ("text", "text_norm", "text_iast", "text_deva"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    spir = row.get("spir")
    if isinstance(spir, dict):
        normalized = spir.get("normalized_text")
        if isinstance(normalized, str) and normalized.strip():
            return normalized.strip()
    return ""


def _doc_id(row: dict[str, Any], idx: int) -> str:
    for key in ("id", "ref", "doc"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return f"doc_{idx}"


def _tokenize(text: str) -> list[str]:
    return [tok for tok in text.lower().replace("\n", " ").split(" ") if tok]


def _char_trigrams(text: str) -> set[str]:
    s = f"  {text.lower()}  "
    if len(s) < 3:
        return {s}
    return {s[i : i + 3] for i in range(len(s) - 2)}


def _lexical_score(query_terms: list[str], doc_text: str) -> float:
    if not query_terms or not doc_text:
        return 0.0
    terms = _tokenize(doc_text)
    if not terms:
        return 0.0
    counts: dict[str, int] = {}
    for term in terms:
        counts[term] = counts.get(term, 0) + 1
    total = len(terms)
    score = 0.0
    for q in query_terms:
        qn = q.lower()
        tf = counts.get(qn, 0)
        if tf == 0:
            continue
        score += (1.0 + math.log(1.0 + tf)) / total
    return score


def _vector_score(query_text: str, doc_text: str) -> float:
    q = _char_trigrams(query_text)
    d = _char_trigrams(doc_text)
    if not q or not d:
        return 0.0
    inter = len(q & d)
    union = len(q | d)
    if union == 0:
        return 0.0
    return inter / union


def _rrf(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)


def retrieve_candidates(
    kag_query: dict[str, Any],
    *,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
    corpus_path: str | Path | None = None,
    artifacts_dir: str | Path | None = None,
) -> dict[str, Any]:
    resolved = _resolve_corpus_path(corpus_path=corpus_path, artifacts_dir=artifacts_dir)
    if resolved is None:
        return {
            "candidates": [],
            "provenance": [],
            "meta": {"errors": ["corpus file not found"], "warnings": []},
        }

    rows = _iter_jsonl(resolved)
    query_terms = [str(t) for t in (kag_query.get("terms") or []) if str(t).strip()]
    vector_query = str(kag_query.get("raw") or " ".join(query_terms))
    modalities = [str(m) for m in (kag_query.get("modalities") or []) if str(m).strip()]

    scored: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        text = _extract_doc_text(row)
        if not text:
            continue
        lex = _lexical_score(query_terms, text)
        vec = _vector_score(vector_query, text)
        scored.append(
            {
                "id": _doc_id(row, idx),
                "text": text,
                "ref": row.get("ref"),
                "doc": row.get("doc"),
                "bm25_score": lex,
                "vector_score": vec,
            }
        )

    bm25_ranked = sorted(scored, key=lambda x: x["bm25_score"], reverse=True)
    vec_ranked = sorted(scored, key=lambda x: x["vector_score"], reverse=True)

    bm25_pos = {item["id"]: idx + 1 for idx, item in enumerate(bm25_ranked)}
    vec_pos = {item["id"]: idx + 1 for idx, item in enumerate(vec_ranked)}

    fused: list[dict[str, Any]] = []
    for item in scored:
        item_id = item["id"]
        score = _rrf(bm25_pos.get(item_id, 10_000)) + _rrf(vec_pos.get(item_id, 10_000))
        rerank_bonus = 0.0
        text_l = item["text"].lower()
        if modalities:
            if any(mod in text_l for mod in modalities):
                rerank_bonus += 0.05
        rerank_score = score + (item["bm25_score"] * 0.2) + (item["vector_score"] * 0.2) + rerank_bonus
        out = dict(item)
        out["fused_score"] = score
        out["rerank_score"] = rerank_score
        out["provenance"] = {
            "source": "artifact_corpus",
            "path": str(resolved),
            "ref": item.get("ref"),
            "doc": item.get("doc"),
        }
        fused.append(out)

    fused.sort(key=lambda x: x["rerank_score"], reverse=True)
    limited = fused[: max(1, int(top_k))]
    return {
        "candidates": limited,
        "provenance": [item["provenance"] for item in limited],
        "meta": {"errors": [], "warnings": [], "filters": filters or {}},
    }
