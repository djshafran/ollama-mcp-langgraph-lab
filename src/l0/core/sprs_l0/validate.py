from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .contracts_v05 import (
    CLAUSE_TYPES,
    DISCOURSE_RELATIONS,
    KAG_DEONTIC_MODALITIES,
    KAG_EDGE_TYPES,
    KAG_NODE_TYPES,
)
from .spir import SPIR_VERSION
from .syntax import normalize_role
from .ud import validate_basic_ud_tree


EMPTY_NODE_RE = re.compile(r"^[0-9]+\.[0-9]+$")


def _is_str(value: Any) -> bool:
    return isinstance(value, str)


def _schema_dir() -> Path:
    return Path(__file__).resolve().parent / "schemas"


@lru_cache(maxsize=8)
def _schema_validator(filename: str) -> Draft202012Validator:
    schema_path = _schema_dir() / filename
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _schema_errors(prefix: str, filename: str, instance: Any, errors: list[str]) -> None:
    validator = _schema_validator(filename)
    for err in validator.iter_errors(instance):
        path = ".".join(str(p) for p in err.path)
        if path:
            errors.append(f"{prefix}.{path}: {err.message}")
        else:
            errors.append(f"{prefix}: {err.message}")


def _is_empty_node_id(value: Any) -> bool:
    return isinstance(value, str) and bool(EMPTY_NODE_RE.fullmatch(value))


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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    if not isinstance(ud, dict):
        errors.append("syntax.ud must be an object")
        return [], [], [], set()

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

    _schema_errors("schema.ud.basic", "ud_basic.schema.json", {"basic_edges": basic}, errors)
    _schema_errors(
        "schema.ud.enhanced",
        "ud_enhanced.schema.json",
        {"enhanced_edges": enhanced, "empty_nodes": empty_nodes},
        errors,
    )

    token_count = len(tokens)
    if token_count and backend not in {"none", "off"}:
        ok_ud, ud_errors, ud_warnings = validate_basic_ud_tree(tokens=tokens, basic_edges=basic)
        if not ok_ud:
            errors.extend([f"syntax.ud.basic_edges: {msg}" for msg in ud_errors])
        warnings.extend([f"syntax.ud.basic_edges: {msg}" for msg in ud_warnings])

    empty_ids: set[str] = set()
    for i, node in enumerate(empty_nodes):
        if not isinstance(node, dict):
            errors.append(f"syntax.ud.empty_nodes[{i}] must be object")
            continue
        empty_id = node.get("id")
        if not _is_empty_node_id(empty_id):
            errors.append(f"syntax.ud.empty_nodes[{i}].id must match i.j format")
            continue
        if empty_id in empty_ids:
            errors.append(f"syntax.ud.empty_nodes duplicate id: {empty_id}")
            continue
        empty_ids.add(empty_id)
        anchor = node.get("anchor_token_id")
        if not isinstance(anchor, int) or anchor < 0 or anchor >= token_count:
            errors.append(f"syntax.ud.empty_nodes[{i}].anchor_token_id out of range")

    known_refs: set[int | str] = set(range(token_count))
    known_refs.update(empty_ids)
    for i, edge in enumerate(enhanced):
        if not isinstance(edge, dict):
            errors.append(f"syntax.ud.enhanced_edges[{i}] must be object")
            continue
        dep = edge.get("dep")
        head = edge.get("head")
        rel = edge.get("rel") or edge.get("relation")
        if dep not in known_refs:
            errors.append(f"syntax.ud.enhanced_edges[{i}].dep unknown node ref")
        if head is not None and head not in known_refs:
            errors.append(f"syntax.ud.enhanced_edges[{i}].head unknown node ref")
        if not _is_str(rel):
            errors.append(f"syntax.ud.enhanced_edges[{i}].rel missing")

    return basic, enhanced, empty_nodes, empty_ids


def _validate_clauses_and_discourse(
    clauses: Any,
    discourse_links: Any,
    *,
    token_count: int,
    empty_node_ids: set[str],
    errors: list[str],
    warnings: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    if not isinstance(clauses, list):
        errors.append("syntax.clauses must be a list")
        clauses = []
    if not isinstance(discourse_links, list):
        errors.append("syntax.discourse_links must be a list")
        discourse_links = []

    _schema_errors(
        "schema.clauses",
        "clauses.schema.json",
        {"clauses": clauses, "discourse_links": discourse_links},
        errors,
    )

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
            errors.append(f"syntax.clauses[{i}].token_span must be [start,end)")
            continue
        start, end = token_span
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or end < start
        ):
            errors.append(f"syntax.clauses[{i}].token_span invalid")
            continue
        if token_count == 0:
            if start != 0 or end != 0:
                errors.append(f"syntax.clauses[{i}].token_span out of range")
        else:
            if start >= token_count or end > token_count or end <= start:
                errors.append(f"syntax.clauses[{i}].token_span out of range")

        root_token_id = row.get("root_token_id")
        empty_node_id = row.get("empty_node_id")
        has_root = isinstance(root_token_id, int)
        has_empty = _is_empty_node_id(empty_node_id)
        if not has_root and not has_empty:
            errors.append(f"syntax.clauses[{i}] must define root_token_id or empty_node_id")
        if has_root and (root_token_id < 0 or root_token_id >= token_count):
            errors.append(f"syntax.clauses[{i}].root_token_id out of range")
        if has_empty and empty_node_id not in empty_node_ids:
            errors.append(f"syntax.clauses[{i}].empty_node_id unknown")

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

    return clauses, discourse_links, clause_ids


def _validate_provenance(
    provenance: Any,
    *,
    path: str,
    token_count: int,
    clause_ids: set[str],
    errors: list[str],
) -> dict[str, Any] | None:
    if not isinstance(provenance, dict):
        errors.append(f"{path}.provenance must be object")
        return None

    token_ids = provenance.get("token_ids")
    if not isinstance(token_ids, list):
        errors.append(f"{path}.provenance.token_ids must be list")
    else:
        for idx, token_id in enumerate(token_ids):
            if not isinstance(token_id, int) or token_id < 0 or token_id >= token_count:
                errors.append(f"{path}.provenance.token_ids[{idx}] out of range")

    clause_id = provenance.get("clause_id")
    if clause_id is not None and (not _is_str(clause_id) or clause_id not in clause_ids):
        errors.append(f"{path}.provenance.clause_id unknown")

    source_ref = provenance.get("source_ref")
    if not _is_str(source_ref) or not source_ref:
        errors.append(f"{path}.provenance.source_ref missing")
    return provenance


def _validate_kag(
    kag: Any,
    *,
    token_count: int,
    clause_ids: set[str],
    errors: list[str],
    warnings: list[str],
) -> tuple[int, int, int]:
    _schema_errors("schema.kag", "kag.schema.json", kag, errors)

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
    node_types: dict[str, str] = {}
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"semantics.kag.nodes[{i}] must be object")
            continue
        node_id = node.get("id")
        ntype = node.get("type")
        if not _is_str(node_id):
            errors.append(f"semantics.kag.nodes[{i}].id missing")
            continue
        if node_id in node_ids:
            errors.append(f"semantics.kag.nodes duplicate id: {node_id}")
            continue
        node_ids.add(node_id)
        if not _is_str(ntype):
            errors.append(f"semantics.kag.nodes[{i}].type missing")
        else:
            node_types[node_id] = ntype
            if ntype not in KAG_NODE_TYPES:
                warnings.append(f"semantics.kag.nodes[{i}].type not in fixed set")
        _validate_provenance(
            node.get("provenance"),
            path=f"semantics.kag.nodes[{i}]",
            token_count=token_count,
            clause_ids=clause_ids,
            errors=errors,
        )

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
        _validate_provenance(
            edge.get("provenance"),
            path=f"semantics.kag.edges[{i}]",
            token_count=token_count,
            clause_ids=clause_ids,
            errors=errors,
        )

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
        target_event_id = norm.get("target_event_id")
        if target_event_id is not None:
            if not _is_str(target_event_id) or target_event_id not in node_ids:
                errors.append(f"semantics.kag.norms[{i}].target_event_id invalid")
            elif node_types.get(target_event_id) != "Event":
                errors.append(f"semantics.kag.norms[{i}].target_event_id must reference Event")
        _validate_provenance(
            norm.get("provenance"),
            path=f"semantics.kag.norms[{i}]",
            token_count=token_count,
            clause_ids=clause_ids,
            errors=errors,
        )

    return len(nodes), len(edges), len(norms)


def validate_spir(spir: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(spir, dict):
        return {"ok": False, "errors": ["SPIR is not a dict"], "warnings": [], "metrics": {}}

    for legacy_key in ("dependencies", "ud_dependencies"):
        if legacy_key in spir:
            errors.append(f"legacy field '{legacy_key}' is not allowed in SPIR v0.5")

    _schema_errors("schema.spir", "spir_v0_5.schema.json", spir, errors)

    meta = spir.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta must be an object")
        meta = {}
    else:
        if meta.get("version") != SPIR_VERSION:
            errors.append("meta.version mismatch")
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
    basic_edges, enhanced_edges, empty_nodes, empty_node_ids = _validate_ud(
        syntax.get("ud"),
        tokens=tokens,
        backend=backend,
        errors=errors,
        warnings=warnings,
    )
    clauses, discourse_links, clause_ids = _validate_clauses_and_discourse(
        syntax.get("clauses"),
        syntax.get("discourse_links"),
        token_count=token_count,
        empty_node_ids=empty_node_ids,
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
    kag_nodes, kag_edges, kag_norms = _validate_kag(
        kag,
        token_count=token_count,
        clause_ids=clause_ids,
        errors=errors,
        warnings=warnings,
    )

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
