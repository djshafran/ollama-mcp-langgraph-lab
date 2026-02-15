from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_overrides(path: str | Path | None) -> dict[str, Any]:
    index = {"by_input_hash": {}, "by_doc_ref": {}}
    if not path:
        return index
    p = Path(path)
    if not p.exists():
        return index

    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if not isinstance(row, dict):
                continue
            input_hash = row.get("input_hash")
            if isinstance(input_hash, str) and input_hash:
                index["by_input_hash"][input_hash] = row
                continue
            doc = row.get("doc")
            ref = row.get("ref")
            if isinstance(doc, str) and isinstance(ref, str):
                index["by_doc_ref"][(doc, ref)] = row
    return index


def _edge_matches(edge: dict[str, Any], matcher: dict[str, Any]) -> bool:
    for key, value in matcher.items():
        if key not in edge:
            return False
        if edge.get(key) != value:
            return False
    return True


def _apply_patch_ops(
    edges: list[dict[str, Any]], patch: dict[str, Any]
) -> tuple[list[dict[str, Any]], bool]:
    changed = False
    if "replace_all" in patch and isinstance(patch["replace_all"], list):
        repl = [edge for edge in patch["replace_all"] if isinstance(edge, dict)]
        return repl, True

    out = [dict(edge) for edge in edges]
    remove_ops = patch.get("remove")
    if isinstance(remove_ops, list) and remove_ops:
        filtered: list[dict[str, Any]] = []
        for edge in out:
            matched = any(
                _edge_matches(edge, matcher)
                for matcher in remove_ops
                if isinstance(matcher, dict)
            )
            if matched:
                changed = True
                continue
            filtered.append(edge)
        out = filtered

    add_ops = patch.get("add")
    if isinstance(add_ops, list):
        for row in add_ops:
            if isinstance(row, dict):
                out.append(dict(row))
                changed = True

    return out, changed


def apply_overrides(
    spir: dict[str, Any],
    overrides_index: dict[str, Any],
    *,
    doc: str | None = None,
    ref: str | None = None,
) -> tuple[dict[str, Any], bool, bool, list[str]]:
    warnings: list[str] = []
    meta = spir.get("meta") or {}
    input_hash = meta.get("input_hash")

    override = None
    if isinstance(input_hash, str):
        override = (overrides_index.get("by_input_hash") or {}).get(input_hash)
    if override is None and isinstance(doc, str) and isinstance(ref, str):
        override = (overrides_index.get("by_doc_ref") or {}).get((doc, ref))
    if not isinstance(override, dict):
        return spir, False, False, warnings

    syntax = spir.setdefault("syntax", {})
    paninian = syntax.get("paninian_edges") or []
    ud = (syntax.get("ud") or {}).get("basic_edges") or []
    changed_karaka = False
    changed_ud = False

    karaka_patch = override.get("karaka_patch")
    if isinstance(karaka_patch, dict):
        paninian, changed_karaka = _apply_patch_ops(paninian, karaka_patch)
        syntax["paninian_edges"] = paninian

    ud_patch = override.get("ud_patch")
    if isinstance(ud_patch, dict):
        ud, changed_ud = _apply_patch_ops(ud, ud_patch)
        syntax.setdefault("ud", {})["basic_edges"] = ud

    needs_ud_recompute = changed_karaka and not changed_ud
    if needs_ud_recompute:
        warnings.append("karaka_patch applied without ud_patch; basic UD must be recomputed")

    syntax_meta = syntax.setdefault("meta", {})
    syntax_meta["overrides_applied"] = changed_karaka or changed_ud
    return spir, bool(changed_karaka or changed_ud), needs_ud_recompute, warnings

