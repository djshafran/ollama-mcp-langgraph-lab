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

    capabilities = spir.get("capabilities")
    if not isinstance(capabilities, list):
        errors.append("capabilities must be a list")

    metrics = {
        "token_count": len(tokens),
        "segment_count": len(segments),
        "capability_count": len(capabilities) if isinstance(capabilities, list) else 0,
    }

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }
