from __future__ import annotations

from typing import Any
import os

from .normalize import normalize_text
from .spir import DEFAULT_CAPABILITIES, hash_artifacts_dir, hash_text, make_spir
from .syntax import build_dependencies


def _simple_tokenize(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    tokens = []
    for raw in text.split():
        tokens.append(
            {
                "surface": raw,
                "lemma": raw.lower(),
                "pos": None,
                "feats": {},
                "conf": 1.0,
            }
        )
    return tokens


def _heritage_tokenize(text: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from .backends.heritage_backend import analyze_sentence

    sol_id, sol = analyze_sentence(text)
    tokens: list[dict[str, Any]] = []
    if hasattr(sol, "words"):
        words = getattr(sol, "words") or []
        for w in words:
            surface = getattr(w, "text", "") or ""
            candidates = getattr(w, "candidates", []) or []
            best = candidates[0] if candidates else None
            root = getattr(best, "root", None) or surface
            analyses = getattr(best, "analyses", None) or []
            lexicon_reference = getattr(best, "lexicon_reference", None)
            tokens.append(
                {
                    "surface": surface,
                    "lemma": root,
                    "pos": None,
                    "feats": {
                        "heritage": {
                            "solution_id": sol_id,
                            "analyses": analyses,
                            "category": getattr(w, "category", None),
                            "classes": getattr(w, "classes", None),
                            "lexicon_reference": lexicon_reference,
                        }
                    },
                    "conf": 1.0,
                }
            )
    else:
        words = sol.get("words", [])
        for variants in words:
            if not variants:
                continue
            best = variants[0]
            surface = best.get("text") or ""
            root = best.get("root") or surface
            analyses = best.get("analyses") or []

            tokens.append(
                {
                    "surface": surface,
                    "lemma": root,
                    "pos": None,
                    "feats": {
                        "heritage": {
                            "solution_id": sol_id,
                            "analyses": analyses,
                        }
                    },
                    "conf": 1.0,
                }
            )

    meta = {"backend": "heritage", "solution_id": sol_id}
    return tokens, meta


def analyze(
    text: str,
    input_format: str = "auto",
    k_best: int = 5,
    return_lattice: bool = True,
    artifacts_dir: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_text(text)
    backend = os.getenv("L0_BACKEND", "simple").strip().lower() or "simple"
    extra_meta: dict[str, Any] = {}
    if backend == "heritage":
        try:
            tokens, extra_meta = _heritage_tokenize(normalized)
        except Exception as exc:
            tokens = _simple_tokenize(normalized)
            extra_meta = {
                "backend": "simple",
                "fallback_from": "heritage",
                "error": str(exc),
            }
    else:
        tokens = _simple_tokenize(normalized)
        extra_meta = {"backend": "simple"}

    segments: list[dict[str, Any]] = []
    if return_lattice and tokens:
        segments = [
            {
                "tokens": list(range(len(tokens))),
                "conf": 1.0,
            }
        ]

    syntax_backend = os.getenv("SYNTAX_BACKEND", "rules")
    syntax_backend = (syntax_backend or "rules").strip().lower()
    if syntax_backend == "hydra":
        syntax_backend = "hyderabad"
    dependencies, ud_dependencies, syntax_meta = build_dependencies(
        tokens=tokens, text=normalized, backend=syntax_backend
    )
    extra_meta.update(syntax_meta)
    artifacts_hash = hash_artifacts_dir(artifacts_dir)
    input_hash = hash_text(normalized)
    spir = make_spir(
        normalized_text=normalized,
        tokens=tokens,
        segments=segments,
        artifacts_hash=artifacts_hash,
        input_hash=input_hash,
        dependencies=dependencies,
        ud_dependencies=ud_dependencies,
        input_format=input_format,
        capabilities=list(DEFAULT_CAPABILITIES),
    )
    spir["meta"]["k_best"] = k_best
    spir["meta"]["return_lattice"] = return_lattice
    spir["meta"].update(extra_meta)
    if extra_meta.get("backend") == "heritage":
        spir["capabilities"] = [
            "normalize",
            "segment_lattice",
            "lemma",
            "heritage_morphology",
        ]
    if dependencies or extra_meta.get("syntax_backend") in {"rules", "hyderabad"}:
        if "paninian_syntax" not in spir["capabilities"]:
            spir["capabilities"].append("paninian_syntax")
    if ud_dependencies and "ud_syntax" not in spir["capabilities"]:
        spir["capabilities"].append("ud_syntax")
    return spir
