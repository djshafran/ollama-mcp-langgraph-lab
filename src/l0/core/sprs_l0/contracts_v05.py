from __future__ import annotations

from typing import Any


CLAUSE_TYPES = {
    "main",
    "subordinate",
    "coordinated",
    "elliptic",
    "nonverbal",
}

DISCOURSE_RELATIONS = {
    "coord",
    "subord",
    "cause",
    "condition",
    "purpose",
    "contrast",
    "elaboration",
}

KAG_NODE_TYPES = {"Event", "Entity", "Norm", "State", "Source"}
KAG_EDGE_TYPES = {
    "ARG",
    "MODAL",
    "CAUSE",
    "CONDITION",
    "PURPOSE",
    "TEMPORAL",
    "SUPPORTS",
    "CONFLICTS",
    "GROUNDED_IN",
}
KAG_DEONTIC_MODALITIES = {"obligation", "prohibition", "permission", "right"}


def make_syntax(
    *,
    backend: str,
    paninian_edges: list[dict[str, Any]] | None = None,
    ud_basic_edges: list[dict[str, Any]] | None = None,
    ud_enhanced_edges: list[dict[str, Any]] | None = None,
    ud_empty_nodes: list[dict[str, Any]] | None = None,
    clauses: list[dict[str, Any]] | None = None,
    discourse_links: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "backend": backend,
        "paninian_edges": paninian_edges or [],
        "ud": {
            "basic_edges": ud_basic_edges or [],
            "enhanced_edges": ud_enhanced_edges or [],
            "empty_nodes": ud_empty_nodes or [],
        },
        "clauses": clauses or [],
        "discourse_links": discourse_links or [],
        "meta": meta
        or {
            "mapping_version": "builtin",
            "overrides_applied": False,
            "errors": [],
            "warnings": [],
        },
    }


def make_kag(
    *,
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    norms: list[dict[str, Any]] | None = None,
    version: str = "0.5.0",
) -> dict[str, Any]:
    return {
        "version": version,
        "nodes": nodes or [],
        "edges": edges or [],
        "norms": norms or [],
    }


def make_semantics(*, kag: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"kag": kag or make_kag()}
