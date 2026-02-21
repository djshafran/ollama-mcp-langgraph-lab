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

DEFAULT_HEAD_RULES = {
    "version": "builtin",
    "rules": [
        {
            "id": "finite_verb_root",
            "priority": 100,
            "description": "Select finite verb as root when present",
        },
        {
            "id": "nominal_predication_root",
            "priority": 80,
            "description": "Select nominal head as root in nonverbal predicates",
        },
        {
            "id": "fallback_first_content",
            "priority": 10,
            "description": "Use first content token as deterministic fallback",
        },
    ],
}


def _parse_head_rules_fallback(raw: str) -> tuple[list[dict[str, Any]], str] | None:
    version = "custom"
    rules: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("version:"):
            version = stripped.split(":", 1)[1].strip() or version
            continue
        if stripped.startswith("- "):
            if current:
                rules.append(current)
            current = {}
            stripped = stripped[2:].strip()
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                current[key.strip()] = value.strip()
            continue
        if current is None:
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            value = value.strip()
            if key.strip() == "priority":
                try:
                    current["priority"] = int(value)
                except ValueError:
                    current["priority"] = 0
            else:
                current[key.strip()] = value
    if current:
        rules.append(current)
    normalized = [rule for rule in rules if isinstance(rule.get("id"), str)]
    if normalized:
        return normalized, version
    return None


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


def load_head_rules(
    artifacts_dir: str | Path | None = None,
    head_rules_path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], str]:
    candidate_paths: list[Path] = []
    if head_rules_path:
        candidate_paths.append(Path(head_rules_path))
    if artifacts_dir:
        candidate_paths.append(Path(artifacts_dir) / "syntax" / "head_rules.yaml")

    for path in candidate_paths:
        if not path.exists():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            try:
                import yaml

                data = yaml.safe_load(raw)
                if isinstance(data, dict) and isinstance(data.get("rules"), list):
                    rules = [r for r in data["rules"] if isinstance(r, dict)]
                    if rules:
                        version = str(data.get("version") or path.parent.name or "custom")
                        return rules, version
            except Exception:
                parsed = _parse_head_rules_fallback(raw)
                if parsed:
                    return parsed
        except Exception:
            continue

    return list(DEFAULT_HEAD_RULES["rules"]), str(DEFAULT_HEAD_RULES["version"])


def _token_text(token: dict[str, Any]) -> str:
    value = token.get("surface")
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def _token_lemma(token: dict[str, Any]) -> str:
    value = token.get("lemma")
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def _token_case(token: dict[str, Any]) -> str | None:
    feats = token.get("feats")
    if not isinstance(feats, dict):
        return None
    case = feats.get("case")
    if isinstance(case, str):
        c = case.strip().lower()
        if c:
            return c
    if isinstance(case, int):
        return str(case)
    return None


def _is_verb(token: dict[str, Any]) -> bool:
    pos = token.get("pos")
    if isinstance(pos, str) and pos.upper() in {"VERB", "AUX"}:
        return True
    feats = token.get("feats")
    if isinstance(feats, dict):
        for key in ("verbform", "lakara", "tense", "person", "v_voice"):
            if key in feats:
                return True
        heritage = feats.get("heritage")
        if isinstance(heritage, dict):
            analyses = heritage.get("analyses")
            if isinstance(analyses, (list, tuple)):
                raw = " ".join(str(x).lower() for x in analyses)
                if any(mark in raw for mark in ("lak", "verb", "tiṅ", "tin")):
                    return True
    text = _token_text(token)
    if text.endswith(("ति", "न्ति", "ते", "न्ते")):
        return True
    return False


def _pick_root_from_head_rules(tokens: list[dict[str, Any]], rules: list[dict[str, Any]]) -> int:
    if not tokens:
        return 0

    ordered = sorted(
        rules,
        key=lambda r: int(r.get("priority") or 0),
        reverse=True,
    )
    for rule in ordered:
        rule_id = str(rule.get("id") or "").strip().lower()
        if rule_id == "finite_verb_root":
            for idx, token in enumerate(tokens):
                if _is_verb(token):
                    return idx
        elif rule_id == "nominal_predication_root":
            for idx, token in enumerate(tokens):
                case = _token_case(token)
                if case in {"nom", "nominative", "1", "v1"}:
                    return idx
                if _token_text(token).endswith("ः"):
                    return idx
        elif rule_id == "fallback_first_content":
            for idx, token in enumerate(tokens):
                if _token_text(token):
                    return idx

    return 0


def _ensure_tree_shape(
    edges: list[dict[str, Any]],
    *,
    root_dep: int,
    token_count: int,
) -> list[dict[str, Any]]:
    by_dep = {int(edge["dep"]): dict(edge) for edge in edges if isinstance(edge.get("dep"), int)}
    normalized: list[dict[str, Any]] = []
    for dep in range(token_count):
        row = by_dep.get(dep) or {"head": root_dep if dep != root_dep else None, "dep": dep, "rel": "dep"}
        row["dep"] = dep
        if dep == root_dep:
            row["head"] = None
            row["rel"] = "root"
        elif row.get("head") is None or row.get("head") == dep:
            row["head"] = root_dep
            if row.get("rel") == "root":
                row["rel"] = "dep"
        normalized.append(row)

    parent = {int(row["dep"]): row.get("head") for row in normalized}

    def has_cycle(start: int) -> bool:
        seen: set[int] = set()
        node = start
        while True:
            head = parent.get(node)
            if head is None:
                return False
            if not isinstance(head, int):
                return True
            if head == root_dep:
                return False
            if head in seen:
                return True
            seen.add(head)
            node = head

    for row in normalized:
        dep = int(row["dep"])
        if dep == root_dep:
            continue
        if has_cycle(dep):
            row["head"] = root_dep
            if row.get("rel") == "root":
                row["rel"] = "dep"
            parent[dep] = root_dep

    return normalized


def map_karaka_to_ud(
    karaka_edges: list[dict[str, Any]],
    tokens: list[dict[str, Any]],
    mapping: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    token_count = len(tokens)
    if token_count == 0:
        return [], {"errors": [], "warnings": [], "root_dep": None, "ud_mode": "projected"}

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
        warnings.append("No valid root in paninian edges; using dep=0 as root")

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
            warnings.append(f"Duplicate dep={dep} in paninian edges; first edge wins")
            continue
        seen_deps.add(dep)
        rel = role_map.get(role, "dep")
        conf = _coerce_conf(edge.get("conf"))
        row = {"head": head, "dep": dep, "rel": rel}
        if conf is not None:
            row["conf"] = conf
        ud_edges.append(row)

    basic_edges = _ensure_tree_shape(ud_edges, root_dep=root_dep, token_count=token_count)
    ok, tree_errors, tree_warnings = validate_basic_ud_tree(tokens, basic_edges)
    if not ok:
        errors.extend(tree_errors)
    warnings.extend(tree_warnings)

    return basic_edges, {"errors": errors, "warnings": warnings, "root_dep": root_dep, "ud_mode": "projected"}


def build_basic_ud(
    *,
    tokens: list[dict[str, Any]],
    paninian_edges: list[dict[str, Any]],
    mapping: dict[str, str],
    ud_mode: str = "head_rules",
    head_rules: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mode = (ud_mode or "head_rules").strip().lower()
    if mode == "projected":
        return map_karaka_to_ud(paninian_edges, tokens=tokens, mapping=mapping)

    token_count = len(tokens)
    if token_count == 0:
        return [], {"errors": [], "warnings": [], "root_dep": None, "ud_mode": "head_rules"}

    rules = head_rules or list(DEFAULT_HEAD_RULES["rules"])
    root_dep = _pick_root_from_head_rules(tokens, rules)
    warnings: list[str] = []
    errors: list[str] = []

    dep_to_paninian: dict[int, dict[str, Any]] = {}
    for edge in paninian_edges:
        dep = edge.get("dep")
        if isinstance(dep, int) and 0 <= dep < token_count and dep not in dep_to_paninian:
            dep_to_paninian[dep] = edge

    built: list[dict[str, Any]] = []
    for dep in range(token_count):
        if dep == root_dep:
            built.append({"head": None, "dep": dep, "rel": "root"})
            continue
        src = dep_to_paninian.get(dep)
        if isinstance(src, dict):
            role = normalize_role(src.get("role"))
            rel = mapping.get(role, "dep")
            head = src.get("head")
            if not isinstance(head, int) or head < 0 or head >= token_count or head == dep:
                head = root_dep
            if head == root_dep and rel == "root":
                rel = "dep"
            row = {"head": head, "dep": dep, "rel": rel}
            conf = _coerce_conf(src.get("conf"))
            if conf is not None:
                row["conf"] = conf
            built.append(row)
            continue
        built.append({"head": root_dep, "dep": dep, "rel": "dep"})

    basic_edges = _ensure_tree_shape(built, root_dep=root_dep, token_count=token_count)
    ok, tree_errors, tree_warnings = validate_basic_ud_tree(tokens=tokens, basic_edges=basic_edges)
    if not ok:
        errors.extend(tree_errors)
        fallback_edges, fallback_meta = map_karaka_to_ud(paninian_edges, tokens=tokens, mapping=mapping)
        fallback_meta.setdefault("warnings", []).append(
            "head_rules tree invalid; fallback to projected mode"
        )
        return fallback_edges, fallback_meta
    warnings.extend(tree_warnings)

    return basic_edges, {"errors": errors, "warnings": warnings, "root_dep": root_dep, "ud_mode": "head_rules"}


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


def _node_ref_to_conllu_id(node: int | str | None) -> str | None:
    if node is None:
        return "0"
    if isinstance(node, int):
        return str(node + 1)
    if isinstance(node, str):
        return node
    return None


def _empty_node_sort_key(node_id: str) -> tuple[int, int]:
    first, second = node_id.split(".", 1)
    return int(first), int(second)


def edges_to_conllu(
    tokens: list[dict[str, Any]],
    basic_edges: list[dict[str, Any]],
    enhanced_edges: list[dict[str, Any]] | None = None,
    empty_nodes: list[dict[str, Any]] | None = None,
) -> str:
    dep_map: dict[int, dict[str, Any]] = {}
    for edge in basic_edges:
        dep = edge.get("dep")
        if isinstance(dep, int):
            dep_map[dep] = edge

    deps_map: dict[str, set[str]] = {}
    for edge in enhanced_edges or []:
        dep = edge.get("dep")
        head = edge.get("head")
        rel = edge.get("rel") or edge.get("relation")
        dep_id = _node_ref_to_conllu_id(dep if isinstance(dep, (int, str)) else None)
        head_id = _node_ref_to_conllu_id(head if isinstance(head, (int, str)) else None)
        if not dep_id or not head_id or not rel:
            continue
        deps_map.setdefault(dep_id, set()).add(f"{head_id}:{rel}")

    empty_by_anchor: dict[int, list[dict[str, Any]]] = {}
    for node in empty_nodes or []:
        node_id = node.get("id")
        anchor = node.get("anchor_token_id")
        if not isinstance(node_id, str) or "." not in node_id:
            continue
        if not isinstance(anchor, int):
            continue
        empty_by_anchor.setdefault(anchor, []).append(node)

    for anchor_nodes in empty_by_anchor.values():
        anchor_nodes.sort(key=lambda n: _empty_node_sort_key(str(n["id"])))

    lines: list[str] = []
    for idx, tok in enumerate(tokens, start=1):
        edge = dep_map.get(idx - 1, {"head": None, "rel": "dep"})
        head = edge.get("head")
        rel = edge.get("rel") or edge.get("relation") or "dep"
        head_idx = 0 if head is None else int(head) + 1
        deps = deps_map.get(str(idx))
        deps_value = "|".join(sorted(deps)) if deps else "_"
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

        for node in empty_by_anchor.get(idx - 1, []):
            node_id = str(node.get("id"))
            form = str(node.get("predicate") or "_")
            deps = deps_map.get(node_id)
            deps_value = "|".join(sorted(deps)) if deps else "_"
            lines.append(
                "\t".join(
                    [
                        node_id,
                        form,
                        form,
                        "_",
                        "_",
                        "_",
                        "_",
                        "_",
                        deps_value,
                        "_",
                    ]
                )
            )

    return "\n".join(lines)
