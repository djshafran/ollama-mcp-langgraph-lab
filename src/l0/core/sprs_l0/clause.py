from __future__ import annotations

from typing import Any


PUNCT_MARKERS = {"।", "॥", ".", "?", "!"}
COORD_MARKERS = {"ca", "वा", "and", "or"}
CAUSE_MARKERS = {"because", "yataḥ", "yatas", "यतः"}
CONDITION_MARKERS = {"if", "yadi", "यदि"}
PURPOSE_MARKERS = {"for", "artham", "अर्थम्", "तथा"}
CONTRAST_MARKERS = {"but", "tu", "परन्तु"}


def _norm_surface(token: dict[str, Any]) -> str:
    surface = token.get("surface")
    if isinstance(surface, str):
        return surface.strip().lower()
    return ""


def _pick_clause_type(span_tokens: list[str]) -> str:
    if any(t in CONDITION_MARKERS for t in span_tokens):
        return "subordinate"
    if any(t in CAUSE_MARKERS for t in span_tokens):
        return "subordinate"
    if any(t in PURPOSE_MARKERS for t in span_tokens):
        return "subordinate"
    if any(t in COORD_MARKERS for t in span_tokens):
        return "coordinated"
    return "main"


def _pick_discourse_rel(span_tokens: list[str]) -> str:
    if any(t in CONDITION_MARKERS for t in span_tokens):
        return "condition"
    if any(t in CAUSE_MARKERS for t in span_tokens):
        return "cause"
    if any(t in PURPOSE_MARKERS for t in span_tokens):
        return "purpose"
    if any(t in CONTRAST_MARKERS for t in span_tokens):
        return "contrast"
    if any(t in COORD_MARKERS for t in span_tokens):
        return "coord"
    return "elaboration"


def build_clause_graph(
    tokens: list[dict[str, Any]], basic_edges: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not tokens:
        return [], []

    root_dep = next(
        (
            int(edge["dep"])
            for edge in basic_edges
            if edge.get("head") is None and (edge.get("rel") == "root" or edge.get("relation") == "root")
        ),
        0,
    )

    # Segment by punctuation markers and explicit clause markers.
    spans: list[tuple[int, int]] = []
    start = 0
    for i, tok in enumerate(tokens):
        text = _norm_surface(tok)
        if text in PUNCT_MARKERS and start <= i:
            end = i
            if end > start:
                spans.append((start, end))
            start = i + 1
    if start < len(tokens):
        spans.append((start, len(tokens)))

    # Fallback to one clause when punctuation split gives nothing.
    if not spans:
        spans = [(0, len(tokens))]

    clauses: list[dict[str, Any]] = []
    for idx, (span_start, span_end) in enumerate(spans, start=1):
        span_token_texts = [_norm_surface(tokens[i]) for i in range(span_start, span_end)]
        clause_type = _pick_clause_type(span_token_texts)
        if not any(text for text in span_token_texts if text and text not in PUNCT_MARKERS):
            clause_type = "elliptic"
        clause_root = root_dep
        if not (span_start <= clause_root < span_end):
            clause_root = span_start
        clauses.append(
            {
                "clause_id": f"c{idx}",
                "root_token_id": clause_root,
                "token_span": [span_start, span_end],
                "clause_type": clause_type,
            }
        )

    discourse_links: list[dict[str, Any]] = []
    for i in range(len(clauses) - 1):
        curr = clauses[i]
        nxt = clauses[i + 1]
        span_start, span_end = nxt["token_span"]
        token_slice = [_norm_surface(tokens[j]) for j in range(span_start, span_end)]
        discourse_links.append(
            {
                "src_clause": curr["clause_id"],
                "dst_clause": nxt["clause_id"],
                "rel": _pick_discourse_rel(token_slice),
            }
        )

    return clauses, discourse_links
