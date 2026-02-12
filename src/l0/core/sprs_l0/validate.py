from __future__ import annotations

from typing import Any

from .spir import SPIR_VERSION
from .syntax import (
    ROLE_ADHIKARANA,
    ROLE_APADANA,
    ROLE_KARANA,
    ROLE_KARTR,
    ROLE_SAMPRADANA,
    normalize_role,
)


def _is_str(value: Any) -> bool:
    return isinstance(value, str)


def validate_spir(spir: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(spir, dict):
        return {
            "ok": False,
            "errors": ["SPIR is not a dict"],
            "warnings": [],
            "metrics": {},
        }

    meta = spir.get("meta")
    syntax_backend = None
    if not isinstance(meta, dict):
        errors.append("meta must be an object")
    else:
        if meta.get("version") != SPIR_VERSION:
            warnings.append("meta.version mismatch")
        if not _is_str(meta.get("artifacts_hash")):
            errors.append("meta.artifacts_hash missing or invalid")
        if not _is_str(meta.get("input_hash")):
            errors.append("meta.input_hash missing or invalid")
        syntax_backend = meta.get("syntax_backend")

    if not _is_str(spir.get("normalized_text")):
        errors.append("normalized_text missing or invalid")

    tokens = spir.get("tokens")
    if not isinstance(tokens, list):
        errors.append("tokens must be a list")
        tokens = []
    else:
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

    segments = spir.get("segments")
    if not isinstance(segments, list):
        errors.append("segments must be a list")
        segments = []

    dependencies = spir.get("dependencies")
    if not isinstance(dependencies, list):
        errors.append("dependencies must be a list")
        dependencies = []
    else:
        for i, dep in enumerate(dependencies):
            if not isinstance(dep, dict):
                errors.append(f"dependencies[{i}] must be object")
                continue
            head = dep.get("head")
            dep_idx = dep.get("dep")
            role = dep.get("role")
            if head is not None and not isinstance(head, int):
                errors.append(f"dependencies[{i}].head must be int or null")
            if not isinstance(dep_idx, int):
                errors.append(f"dependencies[{i}].dep must be int")
            if not _is_str(role) or not role.strip():
                errors.append(f"dependencies[{i}].role missing or invalid")
            if isinstance(dep_idx, int) and (dep_idx < 0 or dep_idx >= len(tokens)):
                errors.append(f"dependencies[{i}].dep out of range")
            if isinstance(head, int) and (head < 0 or head >= len(tokens)):
                errors.append(f"dependencies[{i}].head out of range")

    ud_dependencies = spir.get("ud_dependencies")
    if not isinstance(ud_dependencies, list):
        errors.append("ud_dependencies must be a list")
        ud_dependencies = []
    else:
        for i, dep in enumerate(ud_dependencies):
            if not isinstance(dep, dict):
                errors.append(f"ud_dependencies[{i}] must be object")
                continue
            head = dep.get("head")
            dep_idx = dep.get("dep")
            rel = dep.get("relation")
            if head is not None and not isinstance(head, int):
                errors.append(f"ud_dependencies[{i}].head must be int or null")
            if not isinstance(dep_idx, int):
                errors.append(f"ud_dependencies[{i}].dep must be int")
            if not _is_str(rel) or not rel.strip():
                errors.append(f"ud_dependencies[{i}].relation missing or invalid")
            if isinstance(dep_idx, int) and (dep_idx < 0 or dep_idx >= len(tokens)):
                errors.append(f"ud_dependencies[{i}].dep out of range")
            if isinstance(head, int) and (head < 0 or head >= len(tokens)):
                errors.append(f"ud_dependencies[{i}].head out of range")

    capabilities = spir.get("capabilities")
    if not isinstance(capabilities, list):
        errors.append("capabilities must be a list")

    if tokens and not dependencies and str(syntax_backend).lower() not in {"none", "off"}:
        errors.append("dependencies missing for non-empty tokens")

    if dependencies:
        root_entries = [
            dep
            for dep in dependencies
            if dep.get("head") is None and normalize_role(dep.get("role")) == "root"
        ]
        if len(root_entries) != 1:
            errors.append("dependencies must contain exactly one root")

        dep_indices = [dep.get("dep") for dep in dependencies if isinstance(dep.get("dep"), int)]
        if len(dep_indices) != len(set(dep_indices)):
            errors.append("dependencies contain duplicate dep indices")

        if tokens and len(dependencies) != len(tokens):
            errors.append("dependencies must cover all tokens")

        if tokens:
            root_dep = root_entries[0].get("dep") if len(root_entries) == 1 else None
            if isinstance(root_dep, int):
                adjacency: dict[int, list[int]] = {i: [] for i in range(len(tokens))}
                for dep in dependencies:
                    head = dep.get("head")
                    dep_idx = dep.get("dep")
                    if isinstance(head, int) and isinstance(dep_idx, int):
                        adjacency[head].append(dep_idx)

                visited: set[int] = set()
                stack = [root_dep]
                while stack:
                    node = stack.pop()
                    if node in visited:
                        continue
                    visited.add(node)
                    stack.extend(adjacency.get(node, []))

                if len(visited) != len(tokens):
                    errors.append("dependencies are not connected to root")

        core_roles = {
            ROLE_KARTR,
            "karman",
            ROLE_KARANA,
            ROLE_SAMPRADANA,
            ROLE_APADANA,
            ROLE_ADHIKARANA,
        }
        roles_by_head: dict[int, set[str]] = {}
        for dep in dependencies:
            head = dep.get("head")
            role = normalize_role(dep.get("role"))
            if role not in core_roles:
                continue
            if not isinstance(head, int):
                continue
            roles = roles_by_head.setdefault(head, set())
            if role in roles:
                warnings.append(f"duplicate role '{role}' for head {head}")
            roles.add(role)

    if dependencies and not ud_dependencies:
        warnings.append("ud_dependencies missing while dependencies present")
    if ud_dependencies and not dependencies:
        warnings.append("ud_dependencies present without dependencies")

    metrics = {
        "token_count": len(tokens),
        "segment_count": len(segments),
        "dependency_count": len(dependencies),
        "ud_dependency_count": len(ud_dependencies),
        "capability_count": len(capabilities) if isinstance(capabilities, list) else 0,
    }

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }
