from __future__ import annotations

from typing import Any


COORD_MARKERS = {"ca", "वा", "व", "and", "or", "yā", "वा", "athavā"}
ELLIPSIS_MARKERS = {"ca", "वा", "or", "and", "tu"}


def _token_text(token: dict[str, Any]) -> str:
    surface = token.get("surface")
    if isinstance(surface, str):
        return surface.strip().lower()
    return ""


def build_enhanced_ud(
    tokens: list[dict[str, Any]],
    basic_edges: list[dict[str, Any]],
    clauses: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    enhanced_edges: list[dict[str, Any]] = []
    empty_nodes: list[dict[str, Any]] = []
    warnings: list[str] = []

    # Base layer: include basic UD as explicit enhanced graph base.
    for edge in basic_edges:
        enhanced_edges.append(
            {
                "head": edge.get("head"),
                "dep": edge.get("dep"),
                "rel": edge.get("rel") or edge.get("relation") or "dep",
            }
        )

    root_dep = next(
        (
            int(edge.get("dep"))
            for edge in basic_edges
            if edge.get("head") is None and (edge.get("rel") == "root" or edge.get("relation") == "root")
        ),
        0,
    )

    # Shared argument heuristic for coordination.
    subject_dep = next(
        (int(e.get("dep")) for e in basic_edges if (e.get("rel") or e.get("relation")) == "nsubj"),
        None,
    )
    for edge in basic_edges:
        rel = edge.get("rel") or edge.get("relation")
        dep = edge.get("dep")
        if rel == "conj" and isinstance(dep, int) and isinstance(subject_dep, int):
            enhanced_edges.append(
                {"head": dep, "dep": subject_dep, "rel": "nsubj:xsubj"}
            )

    # Ellipsis heuristic: clause tagged as elliptic or marker tokens.
    clause_rows = clauses or []
    empty_idx = 0
    for clause in clause_rows:
        clause_type = str(clause.get("clause_type") or "").strip().lower()
        if clause_type not in {"elliptic", "gapping"}:
            continue
        empty_idx += 1
        empty_id = f"E{empty_idx}"
        empty_nodes.append(
            {
                "id": empty_id,
                "predicate": "ELIDED_PREDICATE",
                "source_clause": clause.get("clause_id"),
                "conf": 0.5,
            }
        )
        token_span = clause.get("token_span") or [0, 0]
        dep = token_span[0] if isinstance(token_span, list) and token_span else root_dep
        if not isinstance(dep, int):
            dep = root_dep
        enhanced_edges.append({"head": root_dep, "dep": dep, "rel": "orphan"})

    # Marker-based fallback empty nodes.
    if not empty_nodes:
        for idx, token in enumerate(tokens):
            text = _token_text(token)
            if text in ELLIPSIS_MARKERS and idx != root_dep:
                empty_nodes.append(
                    {
                        "id": "E1",
                        "predicate": "ELIDED_PREDICATE",
                        "source_clause": "c1",
                        "conf": 0.3,
                    }
                )
                enhanced_edges.append({"head": root_dep, "dep": idx, "rel": "orphan"})
                warnings.append("Ellipsis marker detected; inserted one empty node")
                break

    return enhanced_edges, empty_nodes, {"warnings": warnings}

