from __future__ import annotations

from typing import Any

from .spir import SPIR_VERSION


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
    if not isinstance(meta, dict):
        errors.append("meta must be an object")
    else:
        if meta.get("version") != SPIR_VERSION:
            warnings.append("meta.version mismatch")
        if not _is_str(meta.get("artifacts_hash")):
            errors.append("meta.artifacts_hash missing or invalid")
        if not _is_str(meta.get("input_hash")):
            errors.append("meta.input_hash missing or invalid")

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

    capabilities = spir.get("capabilities")
    if not isinstance(capabilities, list):
        errors.append("capabilities must be a list")

    metrics = {
        "token_count": len(tokens),
        "segment_count": len(segments),
        "dependency_count": len(dependencies),
        "capability_count": len(capabilities) if isinstance(capabilities, list) else 0,
    }

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }
