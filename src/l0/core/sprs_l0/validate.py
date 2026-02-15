from __future__ import annotations

from typing import Any

from .contracts_v04 import (
    CLAUSE_TYPES,
    DISCOURSE_RELATIONS,
    KAG_DEONTIC_MODALITIES,
    KAG_EDGE_TYPES,
    KAG_NODE_TYPES,
)
from .spir import SPIR_VERSION
from .syntax import normalize_role
from .ud import validate_basic_ud_tree


def _is_str(value: Any) -> bool:
    return isinstance(value, str)


def _check_token_shape(tokens: Any, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(tokens, list):
        errors.append("tokens must be a list")
        return []
    out: list[dict[str, Any]] = []
    for i, tok in enumerate(tokens):
        if not isinstance(tok, dict):
            errors.append(f"tokens[{i}] must be object")
            continue
        if not _is_str(tok.get("surface")):
            errors.append(f"tokens[{i}].surface missing or invalid")
        if not _is_str(tok.get("lemma")):
            errors.append(f"tokens[{i}].lemma missing or invalid")
        if not isinstance(tok.get("feats", {}), dict):
            errors.append(f"tokens[{i}].feats must be object")
        out.append(tok)
    return out


def _validate_paninian_edges(
    edges: Any,
    *,
    token_count: int,
    backend: str,
    errors: list[str],
    warnings: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(edges, list):
        errors.append("syntax.paninian_edges must be a list")
        return []
    out: list[dict[str, Any]] = []
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"syntax.paninian_edges[{i}] must be object")
            continue
        head = edge.get("head")
        dep = edge.get("dep")
        role = edge.get("role")
        if head is not None and not isinstance(head, int):
            errors.append(f"syntax.paninian_edges[{i}].head must be int or null")
        if not isinstance(dep, int):
            errors.append(f"syntax.paninian_edges[{i}].dep must be int")
            continue
        if dep < 0 or dep >= token_count:
            errors.append(f"syntax.paninian_edges[{i}].dep out of range")
            continue
        if isinstance(head, int) and (head < 0 or head >= token_count):
            errors.append(f"syntax.paninian_edges[{i}].head out of range")
            continue
        if not _is_str(role) or not str(role).strip():
            errors.append(f"syntax.paninian_edges[{i}].role missing")
            continue
        out.append(edge)

    if token_count and backend not in {"none", "off"} and not out:
        errors.append("syntax.paninian_edges missing for non-empty tokens")

    if out:
        roots = [
            edge
            for edge in out
            if edge.get("head") is None and normalize_role(edge.get("role")) == "root"
        ]
        if len(roots) != 1:
            errors.append("syntax.paninian_edges must contain exactly one root")

        dep_indices = [edge["dep"] for edge in out if isinstance(edge.get("dep"), int)]
        if len(dep_indices) != len(set(dep_indices)):
            errors.append("syntax.paninian_edges have duplicate dep indices")
        if token_count and len(out) != token_count:
            warnings.append("syntax.paninian_edges do not cover all tokens")
    return out


def _validate_ud(
    ud: Any,
    *,
    tokens: list[dict[str, Any]],
    backend: str,
    errors: list[str],
    warnings: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(ud, dict):
        errors.append("syntax.ud must be an object")
        return [], [], []

    basic = ud.get("basic_edges")
    enhanced = ud.get("enhanced_edges")
    empty_nodes = ud.get("empty_nodes")

    if not isinstance(basic, list):
        errors.append("syntax.ud.basic_edges must be a list")
        basic = []
    if not isinstance(enhanced, list):
        errors.append("syntax.ud.enhanced_edges must be a list")
        enhanced = []
    if not isinstance(empty_nodes, list):
        errors.append("syntax.ud.empty_nodes must be a list")
        empty_nodes = []

    token_count = len(tokens)
    if token_count and backend not in {"none", "off"}:
        ok_ud, ud_errors, ud_warnings = validate_basic_ud_tree(tokens=tokens, basic_edges=basic)
        if not ok_ud:
            errors.extend([f"syntax.ud.basic_edges: {msg}" for msg in ud_errors])
        warnings.extend([f"syntax.ud.basic_edges: {msg}" for msg in ud_warnings])

    for i, edge in enumerate(enhanced):
        if not isinstance(edge, dict):
            errors.append(f"syntax.ud.enhanced_edges[{i}] must be object")
            continue
        dep = edge.get("dep")
        head = edge.get("head")
        rel = edge.get("rel") or edge.get("relation")
        if not isinstance(dep, int):
            errors.append(f"syntax.ud.enhanced_edges[{i}].dep must be int")
            continue
        if dep < 0 or dep >= token_count:
            errors.append(f"syntax.ud.enhanced_edges[{i}].dep out of range")
            continue
        if head is not None and (not isinstance(head, int) or head < 0 or head >= token_count):
            errors.append(f"syntax.ud.enhanced_edges[{i}].head out of range")
            continue
        if not _is_str(rel):
            errors.append(f"syntax.ud.enhanced_edges[{i}].rel missing")

    for i, node in enumerate(empty_nodes):
        if not isinstance(node, dict):
            errors.append(f"syntax.ud.empty_nodes[{i}] must be object")
            continue
        if not _is_str(node.get("id")):
            errors.append(f"syntax.ud.empty_nodes[{i}].id missing")
        if not _is_str(node.get("predicate")):
            warnings.append(f"syntax.ud.empty_nodes[{i}].predicate missing")

    return basic, enhanced, empty_nodes


def _validate_clauses_and_discourse(
    clauses: Any,
    discourse_links: Any,
    *,
    token_count: int,
    errors: list[str],
    warnings: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(clauses, list):
        errors.append("syntax.clauses must be a list")
        clauses = []
    if not isinstance(discourse_links, list):
        errors.append("syntax.discourse_links must be a list")
        discourse_links = []

    clause_ids: set[str] = set()
    for i, row in enumerate(clauses):
        if not isinstance(row, dict):
            errors.append(f"syntax.clauses[{i}] must be object")
            continue
        clause_id = row.get("clause_id")
        if not _is_str(clause_id):
            errors.append(f"syntax.clauses[{i}].clause_id missing")
            continue
        clause_ids.add(str(clause_id))
        clause_type = row.get("clause_type")
        if _is_str(clause_type) and clause_type not in CLAUSE_TYPES:
            warnings.append(f"syntax.clauses[{i}].clause_type not in fixed set")
        token_span = row.get("token_span")
        if not (isinstance(token_span, list) and len(token_span) == 2):
            errors.append(f"syntax.clauses[{i}].token_span must be [start,end]")
            continue
        start, end = token_span
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
            errors.append(f"syntax.clauses[{i}].token_span invalid")
            continue
        if end >= token_count:
            errors.append(f"syntax.clauses[{i}].token_span out of range")

    for i, row in enumerate(discourse_links):
        if not isinstance(row, dict):
            errors.append(f"syntax.discourse_links[{i}] must be object")
            continue
        src = row.get("src_clause")
        dst = row.get("dst_clause")
        rel = row.get("rel")
        if not _is_str(src) or src not in clause_ids:
            errors.append(f"syntax.discourse_links[{i}].src_clause invalid")
        if not _is_str(dst) or dst not in clause_ids:
            errors.append(f"syntax.discourse_links[{i}].dst_clause invalid")
        if not _is_str(rel):
            errors.append(f"syntax.discourse_links[{i}].rel missing")
        elif rel not in DISCOURSE_RELATIONS:
            warnings.append(f"syntax.discourse_links[{i}].rel not in fixed set")

    return clauses, discourse_links


def _validate_kag(kag: Any, errors: list[str], warnings: list[str]) -> tuple[int, int, int]:
    if not isinstance(kag, dict):
        errors.append("semantics.kag must be an object")
        return 0, 0, 0

    nodes = kag.get("nodes")
    edges = kag.get("edges")
    norms = kag.get("norms")
    if not isinstance(nodes, list):
        errors.append("semantics.kag.nodes must be list")
        nodes = []
    if not isinstance(edges, list):
        errors.append("semantics.kag.edges must be list")
        edges = []
    if not isinstance(norms, list):
        errors.append("semantics.kag.norms must be list")
        norms = []

    node_ids: set[str] = set()
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"semantics.kag.nodes[{i}] must be object")
            continue
        node_id = node.get("id")
        ntype = node.get("type")
        if not _is_str(node_id):
            errors.append(f"semantics.kag.nodes[{i}].id missing")
            continue
        node_ids.add(str(node_id))
        if not _is_str(ntype):
            errors.append(f"semantics.kag.nodes[{i}].type missing")
            continue
        if ntype not in KAG_NODE_TYPES:
            warnings.append(f"semantics.kag.nodes[{i}].type not in fixed set")
        prov = node.get("provenance")
        if not isinstance(prov, dict):
            errors.append(f"semantics.kag.nodes[{i}].provenance missing")
        else:
            if not isinstance(prov.get("token_ids"), list):
                errors.append(f"semantics.kag.nodes[{i}].provenance.token_ids missing")
            if not _is_str(prov.get("source_ref")):
                warnings.append(f"semantics.kag.nodes[{i}].provenance.source_ref missing")

    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"semantics.kag.edges[{i}] must be object")
            continue
        src = edge.get("src")
        dst = edge.get("dst")
        etype = edge.get("type")
        if not _is_str(src) or src not in node_ids:
            errors.append(f"semantics.kag.edges[{i}].src invalid")
        if not _is_str(dst) or dst not in node_ids:
            errors.append(f"semantics.kag.edges[{i}].dst invalid")
        if not _is_str(etype):
            errors.append(f"semantics.kag.edges[{i}].type missing")
        elif etype not in KAG_EDGE_TYPES:
            warnings.append(f"semantics.kag.edges[{i}].type not in fixed set")
        prov = edge.get("provenance")
        if not isinstance(prov, dict):
            errors.append(f"semantics.kag.edges[{i}].provenance missing")

    for i, norm in enumerate(norms):
        if not isinstance(norm, dict):
            errors.append(f"semantics.kag.norms[{i}] must be object")
            continue
        modality = norm.get("modality")
        if not _is_str(modality):
            errors.append(f"semantics.kag.norms[{i}].modality missing")
            continue
        if modality not in KAG_DEONTIC_MODALITIES:
            warnings.append(f"semantics.kag.norms[{i}].modality not in fixed set")
        prov = norm.get("provenance")
        if not isinstance(prov, dict):
            errors.append(f"semantics.kag.norms[{i}].provenance missing")

    return len(nodes), len(edges), len(norms)


def validate_spir(spir: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(spir, dict):
        return {"ok": False, "errors": ["SPIR is not a dict"], "warnings": [], "metrics": {}}

    meta = spir.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta must be an object")
        meta = {}
    else:
        if meta.get("version") != SPIR_VERSION:
            warnings.append("meta.version mismatch")
        if not _is_str(meta.get("artifacts_hash")):
            errors.append("meta.artifacts_hash missing or invalid")
        if not _is_str(meta.get("input_hash")):
            errors.append("meta.input_hash missing or invalid")

    if not _is_str(spir.get("normalized_text")):
        errors.append("normalized_text missing or invalid")

    tokens = _check_token_shape(spir.get("tokens"), errors)
    token_count = len(tokens)

    segments = spir.get("segments")
    if not isinstance(segments, list):
        errors.append("segments must be a list")
        segments = []

    capabilities = spir.get("capabilities")
    if not isinstance(capabilities, list):
        errors.append("capabilities must be a list")
        capabilities = []

    syntax = spir.get("syntax")
    if not isinstance(syntax, dict):
        errors.append("syntax must be an object")
        syntax = {}
    backend = str(syntax.get("backend") or "none")

    paninian_edges = _validate_paninian_edges(
        syntax.get("paninian_edges"),
        token_count=token_count,
        backend=backend,
        errors=errors,
        warnings=warnings,
    )
    basic_edges, enhanced_edges, empty_nodes = _validate_ud(
        syntax.get("ud"),
        tokens=tokens,
        backend=backend,
        errors=errors,
        warnings=warnings,
    )
    clauses, discourse_links = _validate_clauses_and_discourse(
        syntax.get("clauses"),
        syntax.get("discourse_links"),
        token_count=token_count,
        errors=errors,
        warnings=warnings,
    )

    syntax_meta = syntax.get("meta")
    if not isinstance(syntax_meta, dict):
        errors.append("syntax.meta must be object")
    else:
        if not isinstance(syntax_meta.get("errors", []), list):
            warnings.append("syntax.meta.errors should be list")
        if not isinstance(syntax_meta.get("warnings", []), list):
            warnings.append("syntax.meta.warnings should be list")

    semantics = spir.get("semantics")
    if not isinstance(semantics, dict):
        errors.append("semantics must be an object")
        semantics = {}
    kag = semantics.get("kag")
    kag_nodes, kag_edges, kag_norms = _validate_kag(kag, errors, warnings)

    provenance = spir.get("provenance")
    if provenance is not None and not isinstance(provenance, dict):
        errors.append("provenance must be object")

    metrics = {
        "token_count": token_count,
        "segment_count": len(segments),
        "paninian_edge_count": len(paninian_edges),
        "ud_basic_edge_count": len(basic_edges),
        "ud_enhanced_edge_count": len(enhanced_edges),
        "ud_empty_node_count": len(empty_nodes),
        "clause_count": len(clauses),
        "discourse_link_count": len(discourse_links),
        "kag_node_count": kag_nodes,
        "kag_edge_count": kag_edges,
        "kag_norm_count": kag_norms,
        "capability_count": len(capabilities),
    }

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings, "metrics": metrics}

