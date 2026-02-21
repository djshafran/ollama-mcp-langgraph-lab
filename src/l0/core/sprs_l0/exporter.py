from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ud import edges_to_conllu


SUPPORTED_FORMATS = {"conllu_basic", "conllu_enhanced", "kag_jsonl", "align_json"}


def _safe_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def export_artifacts(
    spir: dict[str, Any],
    *,
    formats: list[str] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    requested = formats or ["conllu_basic", "conllu_enhanced", "kag_jsonl", "align_json"]
    requested = [fmt for fmt in requested if fmt in SUPPORTED_FORMATS]

    syntax = spir.get("syntax") or {}
    ud = syntax.get("ud") or {}
    basic_edges = ud.get("basic_edges") or []
    enhanced_edges = ud.get("enhanced_edges") or []
    empty_nodes = ud.get("empty_nodes") or []
    tokens = spir.get("tokens") or []

    kag = ((spir.get("semantics") or {}).get("kag")) or {}
    nodes = kag.get("nodes") or []
    edges = kag.get("edges") or []
    norms = kag.get("norms") or []

    outputs: dict[str, Any] = {}
    out_dir = Path(output_dir) if output_dir else None

    if "conllu_basic" in requested:
        text = edges_to_conllu(tokens, basic_edges, enhanced_edges=None, empty_nodes=None)
        outputs["conllu_basic"] = text
        if out_dir:
            _safe_write(out_dir / "work.ud.basic.conllu", text)

    if "conllu_enhanced" in requested:
        text = edges_to_conllu(
            tokens,
            basic_edges,
            enhanced_edges=enhanced_edges,
            empty_nodes=empty_nodes,
        )
        outputs["conllu_enhanced"] = text
        if out_dir:
            _safe_write(out_dir / "work.ud.enhanced.conllu", text)
            _safe_write(out_dir / "work.ud.conllu", text)

    if "kag_jsonl" in requested:
        lines: list[str] = []
        for node in nodes:
            lines.append(json.dumps({"kind": "node", **node}, ensure_ascii=False))
        for edge in edges:
            lines.append(json.dumps({"kind": "edge", **edge}, ensure_ascii=False))
        for norm in norms:
            lines.append(json.dumps({"kind": "norm", **norm}, ensure_ascii=False))
        text = "\n".join(lines)
        outputs["kag_jsonl"] = text
        if out_dir:
            _safe_write(out_dir / "work.kag.jsonl", text)

    if "align_json" in requested:
        align = {
            "input_hash": (spir.get("meta") or {}).get("input_hash"),
            "nodes": [
                {
                    "id": node.get("id"),
                    "token_ids": ((node.get("provenance") or {}).get("token_ids")) or [],
                    "source_ref": ((node.get("provenance") or {}).get("source_ref")),
                }
                for node in nodes
            ],
            "edges": [
                {
                    "id": edge.get("id"),
                    "token_ids": ((edge.get("provenance") or {}).get("token_ids")) or [],
                    "source_ref": ((edge.get("provenance") or {}).get("source_ref")),
                }
                for edge in edges
            ],
        }
        text = json.dumps(align, ensure_ascii=False, indent=2)
        outputs["align_json"] = align
        if out_dir:
            _safe_write(out_dir / "work.align.json", text)

    return {"formats": requested, "outputs": outputs}
