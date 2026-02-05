from __future__ import annotations

from typing import Any


def _pick_root(tokens: list[dict[str, Any]]) -> int | None:
    if not tokens:
        return None
    return 0


def _rules_dependencies(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    root_idx = _pick_root(tokens)
    if root_idx is None:
        return []
    deps: list[dict[str, Any]] = [{"head": None, "dep": root_idx, "role": "root"}]
    for i in range(len(tokens)):
        if i == root_idx:
            continue
        deps.append({"head": root_idx, "dep": i, "role": "dep"})
    return deps


def build_dependencies(
    tokens: list[dict[str, Any]],
    text: str,
    backend: str = "rules",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    backend = (backend or "rules").strip().lower()

    if backend == "hyderabad":
        try:
            from .backends.hyderabad_backend import parse_dependencies

            deps = parse_dependencies(text=text, tokens=tokens)
            return deps, {"syntax_backend": "hyderabad"}
        except Exception as exc:  # pragma: no cover - fallback path
            deps = _rules_dependencies(tokens)
            return (
                deps,
                {
                    "syntax_backend": "rules",
                    "syntax_fallback_from": "hyderabad",
                    "syntax_error": str(exc),
                },
            )

    if backend in {"none", "off"}:
        return [], {"syntax_backend": "none"}

    deps = _rules_dependencies(tokens)
    return deps, {"syntax_backend": "rules"}
