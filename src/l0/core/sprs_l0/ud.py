from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .syntax import normalize_role


DEFAULT_KARAKA_UD_MAP = {
    "kartṛ": "nsubj",
    "karman": "obj",
    "karaṇa": "obl:inst",
    "saṃpradāna": "iobj",
    "apādāna": "obl:abl",
    "adhikaraṇa": "obl:loc",
    "sambandha": "nmod:poss",
    "vocative": "vocative",
    "root": "root",
    "dep": "dep",
}


def _coerce_conf(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _normalize_ud_edge(
    edge: dict[str, Any], token_count: int, *, default_rel: str = "dep"
) -> dict[str, Any] | None:
    head = edge.get("head")
    dep = edge.get("dep")
    rel = edge.get("rel") or edge.get("relation") or default_rel
    conf = _coerce_conf(edge.get("conf"))

    if not isinstance(dep, int) or dep < 0 or dep >= token_count:
        return None
    if head is not None and (not isinstance(head, int) or head < 0 or head >= token_count):
        return None

    out = {"head": head, "dep": dep, "rel": str(rel)}
    if conf is not None:
        out["conf"] = conf
    return out


def load_karaka_ud_mapping(
    artifacts_dir: str | Path | None = None,
    mapping_path: str | Path | None = None,
) -> tuple[dict[str, str], str]:
    candidate_paths: list[Path] = []
    if mapping_path:
        candidate_paths.append(Path(mapping_path))

    if artifacts_dir:
        base = Path(artifacts_dir)
        candidate_paths.append(base / "syntax" / "karaka_to_ud.json")

    for path in candidate_paths:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            mapping = data.get("mapping")
            if isinstance(mapping, dict):
                normalized = {normalize_role(k): str(v) for k, v in mapping.items()}
                version = str(data.get("version") or path.parent.name or "custom")
                return normalized, version
        except Exception:
            continue

    return dict(DEFAULT_KARAKA_UD_MAP), "builtin"


def map_karaka_to_ud(
    karaka_edges: list[dict[str, Any]],
    tokens: list[dict[str, Any]],
    mapping: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    token_count = len(tokens)
    if token_count == 0:
        return [], {"errors": [], "warnings": [], "root_dep": None}

    role_map = mapping or DEFAULT_KARAKA_UD_MAP
    warnings: list[str] = []
    errors: list[str] = []

    root_dep: int | None = None
    first_root = next(
        (
            edge
            for edge in karaka_edges
            if edge.get("head") is None and normalize_role(edge.get("role")) == "root"
        ),
        None,
    )
    if isinstance(first_root, dict) and isinstance(first_root.get("dep"), int):
        root_dep = first_root["dep"]
    if root_dep is None or root_dep < 0 or root_dep >= token_count:
        root_dep = 0
        warnings.append("No valid root in karaka edges; using dep=0 as root")

    ud_edges: list[dict[str, Any]] = []
    seen_deps: set[int] = set()
    for edge in karaka_edges:
        dep = edge.get("dep")
        head = edge.get("head")
        role = normalize_role(edge.get("role"))
        if not isinstance(dep, int) or dep < 0 or dep >= token_count:
            continue
        if head is not None and (not isinstance(head, int) or head < 0 or head >= token_count):
            continue
        if dep in seen_deps:
            warnings.append(f"Duplicate dep={dep} in karaka edges; first edge wins")
            continue
        seen_deps.add(dep)
        rel = role_map.get(role, "dep")
        conf = _coerce_conf(edge.get("conf"))
        row = {"head": head, "dep": dep, "rel": rel}
        if conf is not None:
            row["conf"] = conf
        ud_edges.append(row)

    # Guarantee full coverage and exactly one root.
    dep_to_edge = {int(edge["dep"]): edge for edge in ud_edges if isinstance(edge.get("dep"), int)}
    dep_to_edge[root_dep] = {"head": None, "dep": root_dep, "rel": "root"}
    for dep in range(token_count):
        if dep in dep_to_edge:
            continue
        head = root_dep if dep != root_dep else None
        rel = "dep" if dep != root_dep else "root"
        dep_to_edge[dep] = {"head": head, "dep": dep, "rel": rel}

    basic_edges = [dep_to_edge[i] for i in range(token_count)]
    ok, tree_errors, tree_warnings = validate_basic_ud_tree(tokens, basic_edges)
    if not ok:
        errors.extend(tree_errors)
    warnings.extend(tree_warnings)

    return basic_edges, {"errors": errors, "warnings": warnings, "root_dep": root_dep}


def validate_basic_ud_tree(
    tokens: list[dict[str, Any]], basic_edges: list[dict[str, Any]]
) -> tuple[bool, list[str], list[str]]:
    token_count = len(tokens)
    errors: list[str] = []
    warnings: list[str] = []

    if token_count == 0:
        return True, [], []

    normalized: list[dict[str, Any]] = []
    for edge in basic_edges:
        row = _normalize_ud_edge(edge, token_count=token_count)
        if row is not None:
            normalized.append(row)

    if len(normalized) != token_count:
        errors.append("basic UD must contain exactly one edge per token")
        return False, errors, warnings

    roots = [e for e in normalized if e.get("head") is None and e.get("rel") == "root"]
    if len(roots) != 1:
        errors.append("basic UD must contain exactly one root")
        return False, errors, warnings

    dep_ids = [int(e["dep"]) for e in normalized]
    if len(dep_ids) != len(set(dep_ids)):
        errors.append("basic UD has duplicate dep indices")
        return False, errors, warnings

    root_dep = int(roots[0]["dep"])
    children: dict[int, list[int]] = {i: [] for i in range(token_count)}
    for edge in normalized:
        head = edge.get("head")
        dep = int(edge["dep"])
        if isinstance(head, int):
            children[head].append(dep)

    visited: set[int] = set()
    stack = [root_dep]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        stack.extend(children.get(node, []))

    if len(visited) != token_count:
        errors.append("basic UD must be connected to root")
        return False, errors, warnings

    # Detect directed cycles via DFS colors.
    color = [0] * token_count

    def dfs(node: int) -> bool:
        color[node] = 1
        for child in children.get(node, []):
            if color[child] == 1:
                return True
            if color[child] == 0 and dfs(child):
                return True
        color[node] = 2
        return False

    if dfs(root_dep):
        errors.append("basic UD contains a cycle")
        return False, errors, warnings

    if any(c == 0 for c in color):
        warnings.append("unvisited nodes remained after cycle check")

    return True, errors, warnings


def edges_to_conllu(
    tokens: list[dict[str, Any]],
    basic_edges: list[dict[str, Any]],
    enhanced_edges: list[dict[str, Any]] | None = None,
) -> str:
    dep_map: dict[int, dict[str, Any]] = {}
    for edge in basic_edges:
        dep = edge.get("dep")
        if isinstance(dep, int):
            dep_map[dep] = edge

    deps_map: dict[int, list[str]] = {}
    for edge in enhanced_edges or []:
        dep = edge.get("dep")
        head = edge.get("head")
        rel = edge.get("rel") or edge.get("relation")
        if not isinstance(dep, int) or not isinstance(head, int) or not rel:
            continue
        dep_list = deps_map.setdefault(dep, [])
        dep_list.append(f"{head + 1}:{rel}")

    lines: list[str] = []
    for idx, tok in enumerate(tokens, start=1):
        edge = dep_map.get(idx - 1, {"head": None, "rel": "dep"})
        head = edge.get("head")
        rel = edge.get("rel") or edge.get("relation") or "dep"
        head_idx = 0 if head is None else int(head) + 1
        deps = deps_map.get(idx - 1)
        deps_value = "|".join(sorted(set(deps))) if deps else "_"
        lines.append(
            "\t".join(
                [
                    str(idx),
                    str(tok.get("surface") or "_"),
                    str(tok.get("lemma") or "_"),
                    str(tok.get("pos") or "_"),
                    "_",
                    "_",
                    str(head_idx),
                    str(rel),
                    deps_value,
                    "_",
                ]
            )
        )
    return "\n".join(lines)

