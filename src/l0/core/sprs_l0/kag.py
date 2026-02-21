from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts_v05 import make_kag


DEFAULT_LEXICON = {
    "obligation": ["must", "should", "kartavya", "कर्तव्य"],
    "prohibition": ["not", "never", "mā", "मा"],
    "permission": ["may", "allowed", "anumati", "अनुमति"],
    "right": ["right", "adhikara", "adhikāra", "अधिकार"],
}


def _norm_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def load_deontic_lexicon(
    artifacts_dir: str | Path | None = None,
    path: str | Path | None = None,
) -> dict[str, list[str]]:
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    if artifacts_dir:
        candidates.append(Path(artifacts_dir) / "kag" / "deontic_lexicon.json")

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            lexicon = payload.get("modality_markers")
            if isinstance(lexicon, dict):
                out: dict[str, list[str]] = {}
                for k, v in lexicon.items():
                    if isinstance(v, list):
                        out[str(k)] = [str(item) for item in v]
                if out:
                    return out
        except Exception:
            continue

    return {k: list(v) for k, v in DEFAULT_LEXICON.items()}


def _find_clause_for_token(token_id: int, clauses: list[dict[str, Any]]) -> str | None:
    for clause in clauses:
        span = clause.get("token_span")
        clause_id = clause.get("clause_id")
        if (
            isinstance(span, list)
            and len(span) == 2
            and isinstance(span[0], int)
            and isinstance(span[1], int)
            and isinstance(clause_id, str)
        ):
            start, end = span
            if start <= token_id < end:
                return clause_id
    return None


def _provenance(
    *,
    token_ids: list[int],
    clause_id: str | None,
    source_ref: str,
) -> dict[str, Any]:
    return {
        "token_ids": token_ids,
        "clause_id": clause_id,
        "source_ref": source_ref,
    }


def infer_deontic_norms(
    *,
    tokens: list[dict[str, Any]],
    clauses: list[dict[str, Any]],
    event_by_clause: dict[str, str],
    fallback_event: str | None,
    lexicon: dict[str, list[str]],
    source_ref: str,
) -> list[dict[str, Any]]:
    if not tokens:
        return []
    modality_by_marker: dict[str, str] = {}
    for modality, markers in lexicon.items():
        for marker in markers:
            modality_by_marker[_norm_text(marker)] = modality

    norms: list[dict[str, Any]] = []
    for idx, token in enumerate(tokens):
        candidates = [
            _norm_text(token.get("surface")),
            _norm_text(token.get("lemma")),
        ]
        modality = next((modality_by_marker[c] for c in candidates if c in modality_by_marker), None)
        if not modality:
            continue

        clause_id = _find_clause_for_token(idx, clauses)
        if clause_id is None and event_by_clause:
            clause_id = next(iter(event_by_clause.keys()))
        target_event = event_by_clause.get(clause_id) if clause_id else fallback_event
        norm_id = f"n{len(norms) + 1}"
        norms.append(
            {
                "id": norm_id,
                "modality": modality,
                "target_event_id": target_event,
                "evidence_text": token.get("surface") or token.get("lemma") or "",
                "provenance": _provenance(
                    token_ids=[idx],
                    clause_id=clause_id,
                    source_ref=source_ref,
                ),
            }
        )
    return norms


def attach_provenance(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    norms: list[dict[str, Any]],
    source_ref: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    for node in nodes:
        prov = node.get("provenance")
        if not isinstance(prov, dict):
            node["provenance"] = _provenance(token_ids=[], clause_id=None, source_ref=source_ref)
            continue
        prov.setdefault("token_ids", [])
        prov.setdefault("clause_id", None)
        prov.setdefault("source_ref", source_ref)

    for edge in edges:
        prov = edge.get("provenance")
        if not isinstance(prov, dict):
            edge["provenance"] = _provenance(token_ids=[], clause_id=None, source_ref=source_ref)
            continue
        prov.setdefault("token_ids", [])
        prov.setdefault("clause_id", None)
        prov.setdefault("source_ref", source_ref)

    for norm in norms:
        prov = norm.get("provenance")
        if not isinstance(prov, dict):
            norm["provenance"] = _provenance(token_ids=[], clause_id=None, source_ref=source_ref)
            continue
        prov.setdefault("token_ids", [])
        prov.setdefault("clause_id", None)
        prov.setdefault("source_ref", source_ref)

    return nodes, edges, norms


def build_kag_from_syntax(
    spir: dict[str, Any],
    *,
    artifacts_dir: str | Path | None = None,
) -> dict[str, Any]:
    tokens = spir.get("tokens") or []
    syntax = spir.get("syntax") or {}
    paninian_edges = syntax.get("paninian_edges") or []
    clauses = syntax.get("clauses") or []
    source_ref = str((spir.get("meta") or {}).get("input_hash") or "unknown")
    lexicon = load_deontic_lexicon(artifacts_dir=artifacts_dir)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    token_to_entity: dict[int, str] = {}
    event_by_clause: dict[str, str] = {}

    source_node_id = "src1"
    nodes.append(
        {
            "id": source_node_id,
            "type": "Source",
            "label": "InputText",
            "data": {"input_hash": source_ref},
            "provenance": _provenance(token_ids=[], clause_id=None, source_ref=source_ref),
        }
    )

    for idx, clause in enumerate(clauses, start=1):
        clause_id = clause.get("clause_id")
        if not isinstance(clause_id, str):
            continue
        root_token_id = clause.get("root_token_id")
        token_ids: list[int] = []
        label = f"event_{idx}"
        if isinstance(root_token_id, int) and 0 <= root_token_id < len(tokens):
            root_token = tokens[root_token_id]
            token_ids = [root_token_id]
            label = str(root_token.get("lemma") or root_token.get("surface") or label)

        event_id = f"ev{idx}"
        event_by_clause[clause_id] = event_id
        nodes.append(
            {
                "id": event_id,
                "type": "Event",
                "label": label,
                "data": {
                    "clause_id": clause_id,
                    "root_token_id": root_token_id if isinstance(root_token_id, int) else None,
                    "empty_node_id": clause.get("empty_node_id"),
                },
                "provenance": _provenance(
                    token_ids=token_ids,
                    clause_id=clause_id,
                    source_ref=source_ref,
                ),
            }
        )
        edges.append(
            {
                "id": f"e_src_{event_id}",
                "src": source_node_id,
                "dst": event_id,
                "type": "GROUNDED_IN",
                "provenance": _provenance(
                    token_ids=token_ids,
                    clause_id=clause_id,
                    source_ref=source_ref,
                ),
            }
        )

    fallback_event: str | None = None
    if not event_by_clause and tokens:
        nodes.append(
            {
                "id": "ev1",
                "type": "Event",
                "label": str(tokens[0].get("lemma") or tokens[0].get("surface") or "event"),
                "data": {"clause_id": None, "root_token_id": 0},
                "provenance": _provenance(token_ids=[0], clause_id=None, source_ref=source_ref),
            }
        )
        edges.append(
            {
                "id": "e_src_ev1",
                "src": source_node_id,
                "dst": "ev1",
                "type": "GROUNDED_IN",
                "provenance": _provenance(token_ids=[0], clause_id=None, source_ref=source_ref),
            }
        )
        fallback_event = "ev1"

    if fallback_event is None:
        fallback_event = next(iter(event_by_clause.values()), None)

    for idx, token in enumerate(tokens):
        entity_id = f"ent{idx + 1}"
        token_to_entity[idx] = entity_id
        clause_id = _find_clause_for_token(idx, clauses)
        nodes.append(
            {
                "id": entity_id,
                "type": "Entity",
                "label": str(token.get("lemma") or token.get("surface") or f"tok_{idx}"),
                "data": {"token_id": idx},
                "provenance": _provenance(token_ids=[idx], clause_id=clause_id, source_ref=source_ref),
            }
        )
        edges.append(
            {
                "id": f"e_src_{entity_id}",
                "src": source_node_id,
                "dst": entity_id,
                "type": "GROUNDED_IN",
                "provenance": _provenance(token_ids=[idx], clause_id=clause_id, source_ref=source_ref),
            }
        )

    for edge_idx, karaka in enumerate(paninian_edges, start=1):
        dep = karaka.get("dep")
        role = str(karaka.get("role") or "dep")
        if not isinstance(dep, int) or dep not in token_to_entity:
            continue
        clause_id = _find_clause_for_token(dep, clauses)
        source_event = event_by_clause.get(clause_id) if clause_id else fallback_event
        if source_event is None:
            continue
        target_entity = token_to_entity[dep]
        edges.append(
            {
                "id": f"arg{edge_idx}",
                "src": source_event,
                "dst": target_entity,
                "type": "ARG",
                "label": role,
                "data": {"role": role},
                "provenance": _provenance(token_ids=[dep], clause_id=clause_id, source_ref=source_ref),
            }
        )

    norms = infer_deontic_norms(
        tokens=tokens,
        clauses=clauses,
        event_by_clause=event_by_clause,
        fallback_event=fallback_event,
        lexicon=lexicon,
        source_ref=source_ref,
    )
    for idx, norm in enumerate(norms, start=1):
        norm_node_id = f"norm{idx}"
        nodes.append(
            {
                "id": norm_node_id,
                "type": "Norm",
                "label": norm["modality"],
                "data": {"modality": norm["modality"]},
                "provenance": norm.get("provenance", {}),
            }
        )
        target_event_id = norm.get("target_event_id")
        if isinstance(target_event_id, str):
            edges.append(
                {
                    "id": f"modal{idx}",
                    "src": norm_node_id,
                    "dst": target_event_id,
                    "type": "MODAL",
                    "label": norm["modality"],
                    "data": {"modality": norm["modality"]},
                    "provenance": norm.get("provenance", {}),
                }
            )
        norm["norm_node_id"] = norm_node_id

    nodes, edges, norms = attach_provenance(
        nodes=nodes,
        edges=edges,
        norms=norms,
        source_ref=source_ref,
    )
    return make_kag(nodes=nodes, edges=edges, norms=norms)
