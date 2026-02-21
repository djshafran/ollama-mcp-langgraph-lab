from __future__ import annotations

from typing import Any


ELLIPSIS_MARKERS = {"ca", "वा", "or", "and", "tu"}


def _token_text(token: dict[str, Any]) -> str:
    surface = token.get("surface")
    if isinstance(surface, str):
        return surface.strip().lower()
    return ""


def _dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[int | str | None, int | str, str]] = set()
    out: list[dict[str, Any]] = []
    for edge in edges:
        head = edge.get("head")
        dep = edge.get("dep")
        rel = edge.get("rel") or edge.get("relation") or "dep"
        if not isinstance(dep, (int, str)):
            continue
        key = (head if isinstance(head, (int, str)) or head is None else None, dep, str(rel))
        if key in seen:
            continue
        seen.add(key)
        out.append({"head": key[0], "dep": key[1], "rel": key[2]})
    return out


def _next_empty_id(anchor_token_id: int, per_anchor_counts: dict[int, int]) -> str:
    count = per_anchor_counts.get(anchor_token_id, 0) + 1
    per_anchor_counts[anchor_token_id] = count
    return f"{anchor_token_id + 1}.{count}"


def build_enhanced_ud(
    tokens: list[dict[str, Any]],
    basic_edges: list[dict[str, Any]],
    clauses: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    enhanced_edges: list[dict[str, Any]] = []
    empty_nodes: list[dict[str, Any]] = []
    warnings: list[str] = []

    for edge in basic_edges:
        dep = edge.get("dep")
        if not isinstance(dep, int):
            continue
        enhanced_edges.append(
            {
                "head": edge.get("head"),
                "dep": dep,
                "rel": edge.get("rel") or edge.get("relation") or "dep",
            }
        )

    root_dep = next(
        (
            int(edge.get("dep"))
            for edge in basic_edges
            if edge.get("head") is None
            and (edge.get("rel") == "root" or edge.get("relation") == "root")
        ),
        0,
    )

    subject_dep = next(
        (int(e.get("dep")) for e in basic_edges if (e.get("rel") or e.get("relation")) == "nsubj"),
        None,
    )
    for edge in basic_edges:
        rel = edge.get("rel") or edge.get("relation")
        dep = edge.get("dep")
        if rel == "conj" and isinstance(dep, int) and isinstance(subject_dep, int):
            enhanced_edges.append({"head": dep, "dep": subject_dep, "rel": "nsubj:xsubj"})

    per_anchor_counts: dict[int, int] = {}
    clause_rows = clauses or []
    for clause in clause_rows:
        clause_type = str(clause.get("clause_type") or "").strip().lower()
        if clause_type not in {"elliptic", "gapping"}:
            continue
        token_span = clause.get("token_span") or [0, 0]
        if not (isinstance(token_span, list) and len(token_span) == 2):
            continue
        span_start, span_end = token_span
        if not isinstance(span_start, int) or not isinstance(span_end, int):
            continue
        if span_start < 0 or span_start >= len(tokens):
            continue
        if span_end <= span_start:
            continue

        clause_root = clause.get("root_token_id")
        if not isinstance(clause_root, int):
            clause_root = span_start
        if clause_root < 0 or clause_root >= len(tokens):
            clause_root = root_dep

        empty_id = _next_empty_id(clause_root, per_anchor_counts)
        empty_nodes.append(
            {
                "id": empty_id,
                "anchor_token_id": clause_root,
                "predicate": "ELIDED_PREDICATE",
                "source_clause": clause.get("clause_id"),
                "conf": 0.5,
            }
        )
        enhanced_edges.append({"head": clause_root, "dep": empty_id, "rel": "conj"})

        orphan_dep = span_start
        if orphan_dep == clause_root and span_start + 1 < span_end:
            orphan_dep = span_start + 1
        if 0 <= orphan_dep < len(tokens):
            enhanced_edges.append({"head": empty_id, "dep": orphan_dep, "rel": "orphan"})

    if not empty_nodes:
        for idx, token in enumerate(tokens):
            text = _token_text(token)
            if text in ELLIPSIS_MARKERS and idx != root_dep:
                empty_id = _next_empty_id(idx, per_anchor_counts)
                empty_nodes.append(
                    {
                        "id": empty_id,
                        "anchor_token_id": idx,
                        "predicate": "ELIDED_PREDICATE",
                        "source_clause": "c1",
                        "conf": 0.3,
                    }
                )
                enhanced_edges.append({"head": root_dep, "dep": empty_id, "rel": "dep"})
                enhanced_edges.append({"head": empty_id, "dep": idx, "rel": "orphan"})
                warnings.append("Ellipsis marker detected; inserted one empty node")
                break

    enhanced_edges = _dedupe_edges(enhanced_edges)
    return enhanced_edges, empty_nodes, {"warnings": warnings}
