from __future__ import annotations

from pathlib import Path
from typing import Any
import os

from .clause import build_clause_graph
from .contracts_v05 import make_semantics, make_syntax
from .eud import build_enhanced_ud
from .kag import build_kag_from_syntax
from .normalize import normalize_text
from .overrides import apply_overrides, load_overrides
from .spir import DEFAULT_CAPABILITIES, hash_artifacts_dir, hash_text, make_spir
from .syntax import analyze_syntax
from .ud import (
    build_basic_ud,
    load_head_rules,
    load_karaka_ud_mapping,
    validate_basic_ud_tree,
)


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
        words = sol.get("words", []) if isinstance(sol, dict) else []
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
                    "feats": {"heritage": {"solution_id": sol_id, "analyses": analyses}},
                    "conf": 1.0,
                }
            )

    meta = {"backend": "heritage", "solution_id": sol_id}
    return tokens, meta


def _resolve_syntax_overrides_path(artifacts_dir: str | Path | None) -> str | None:
    env_path = os.getenv("SYNTAX_OVERRIDES_PATH", "").strip()
    if env_path:
        return env_path
    if artifacts_dir:
        candidate = Path(artifacts_dir) / "syntax" / "overrides.jsonl"
        if candidate.exists():
            return str(candidate)
    return None


def analyze(
    text: str,
    input_format: str = "auto",
    k_best: int = 5,
    return_lattice: bool = True,
    artifacts_dir: str | None = None,
    syntax_backend: str | None = None,
    return_ud: bool = True,
    return_syntax: bool = True,
    ud_mode: str = "head_rules",
    include_enhanced: bool = True,
    kag_mode: str = "full",
    include_provenance: bool = True,
    doc: str | None = None,
    ref: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_text(text)

    backend = os.getenv("L0_BACKEND", "simple").strip().lower() or "simple"
    extra_meta: dict[str, Any] = {}
    if backend == "heritage":
        try:
            tokens, extra_meta = _heritage_tokenize(normalized)
            if normalized and not tokens:
                tokens = _simple_tokenize(normalized)
                extra_meta = {
                    "backend": "simple",
                    "fallback_from": "heritage",
                    "warning": "heritage returned empty tokenization",
                }
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
        segments = [{"tokens": list(range(len(tokens))), "conf": 1.0}]

    syntax_backend_value = (
        (syntax_backend or os.getenv("SYNTAX_BACKEND", "rules")).strip().lower()
    )
    if syntax_backend_value == "hydra":
        syntax_backend_value = "hyderabad"

    paninian_edges: list[dict[str, Any]] = []
    syntax_meta: dict[str, Any] = {
        "errors": [],
        "warnings": [],
        "overrides_applied": False,
    }
    if return_syntax:
        paninian_edges, _, syntax_meta_backend = analyze_syntax(
            text=normalized,
            tokens=tokens,
            backend=syntax_backend_value,
        )
        syntax_meta.update(syntax_meta_backend)

    map_path = os.getenv("KARAKA_UD_MAP_PATH", "").strip() or None
    ud_mapping, mapping_version = load_karaka_ud_mapping(
        artifacts_dir=artifacts_dir,
        mapping_path=map_path,
    )
    syntax_meta["mapping_version"] = mapping_version

    head_rules_path = os.getenv("UD_HEAD_RULES_PATH", "").strip() or None
    head_rules, head_rules_version = load_head_rules(
        artifacts_dir=artifacts_dir,
        head_rules_path=head_rules_path,
    )
    syntax_meta["head_rules_version"] = head_rules_version

    provisional = {
        "meta": {"input_hash": hash_text(normalized)},
        "syntax": {
            "paninian_edges": paninian_edges,
            "ud": {"basic_edges": []},
            "meta": {"overrides_applied": False},
        },
    }

    # Pipeline ordering v0.5: overrides before UD/clause/EUD/KAG.
    overrides_path = _resolve_syntax_overrides_path(artifacts_dir)
    overrides_index = load_overrides(overrides_path)
    applied = False
    needs_ud_recompute = False
    if overrides_index:
        provisional, applied, needs_ud_recompute, override_warnings = apply_overrides(
            provisional, overrides_index, doc=doc, ref=ref
        )
        syntax_meta["warnings"].extend(override_warnings)
        syntax_meta["overrides_applied"] = bool(applied)

    paninian_edges = (
        (provisional.get("syntax") or {}).get("paninian_edges") or paninian_edges
    )
    override_meta = ((provisional.get("syntax") or {}).get("meta")) or {}
    override_ud_explicit = bool(override_meta.get("override_ud_explicit"))

    basic_ud: list[dict[str, Any]] = []
    if return_ud:
        if ud_mode == "none":
            basic_ud = []
        elif override_ud_explicit and not needs_ud_recompute:
            basic_ud = ((provisional.get("syntax") or {}).get("ud") or {}).get("basic_edges") or []
            syntax_meta["warnings"].append("Using explicit ud_patch from syntax overrides")
        else:
            basic_ud, ud_meta = build_basic_ud(
                tokens=tokens,
                paninian_edges=paninian_edges,
                mapping=ud_mapping,
                ud_mode=ud_mode,
                head_rules=head_rules,
            )
            syntax_meta["warnings"].extend(ud_meta.get("warnings") or [])
            syntax_meta["errors"].extend(ud_meta.get("errors") or [])

    if basic_ud:
        ok_ud, ud_errors, ud_warnings = validate_basic_ud_tree(tokens=tokens, basic_edges=basic_ud)
        if not ok_ud:
            syntax_meta["errors"].extend(ud_errors)
        syntax_meta["warnings"].extend(ud_warnings)

    clauses: list[dict[str, Any]] = []
    discourse_links: list[dict[str, Any]] = []
    if return_syntax:
        if basic_ud:
            clauses, discourse_links = build_clause_graph(tokens=tokens, basic_edges=basic_ud)
        elif tokens:
            clauses = [
                {
                    "clause_id": "c1",
                    "root_token_id": 0,
                    "token_span": [0, len(tokens)],
                    "clause_type": "main",
                }
            ]
            discourse_links = []

    enhanced_ud: list[dict[str, Any]] = []
    empty_nodes: list[dict[str, Any]] = []
    if return_ud and include_enhanced and basic_ud:
        enhanced_ud, empty_nodes, eud_meta = build_enhanced_ud(
            tokens=tokens,
            basic_edges=basic_ud,
            clauses=clauses,
        )
        syntax_meta["warnings"].extend(eud_meta.get("warnings") or [])

    syntax = make_syntax(
        backend=str(syntax_meta.get("syntax_backend") or syntax_backend_value or "none"),
        paninian_edges=paninian_edges,
        ud_basic_edges=basic_ud,
        ud_enhanced_edges=enhanced_ud,
        ud_empty_nodes=empty_nodes,
        clauses=clauses,
        discourse_links=discourse_links,
        meta={
            "mapping_version": syntax_meta.get("mapping_version") or "builtin",
            "head_rules_version": syntax_meta.get("head_rules_version") or "builtin",
            "overrides_applied": bool(syntax_meta.get("overrides_applied")),
            "errors": syntax_meta.get("errors") or [],
            "warnings": syntax_meta.get("warnings") or [],
            "fallback_from": syntax_meta.get("syntax_fallback_from"),
            "error": syntax_meta.get("syntax_error"),
            "ud_mode": ud_mode,
        },
    )

    artifacts_hash = hash_artifacts_dir(artifacts_dir)
    input_hash = hash_text(normalized)
    provenance: dict[str, Any] = {}
    if include_provenance:
        provenance = {
            "source_ref": input_hash,
            "token_count": len(tokens),
            "layers": ["raw", "normalize", "syntax", "kag"],
        }

    spir = make_spir(
        normalized_text=normalized,
        tokens=tokens,
        segments=segments,
        artifacts_hash=artifacts_hash,
        input_hash=input_hash,
        syntax=syntax,
        semantics=make_semantics(),
        input_format=input_format,
        capabilities=list(DEFAULT_CAPABILITIES),
        provenance=provenance,
    )
    spir["meta"]["k_best"] = k_best
    spir["meta"]["return_lattice"] = return_lattice
    spir["meta"]["ud_mode"] = ud_mode
    spir["meta"]["include_enhanced"] = include_enhanced
    spir["meta"]["kag_mode"] = kag_mode
    spir["meta"].update(extra_meta)

    if extra_meta.get("backend") == "heritage":
        if "heritage_morphology" not in spir["capabilities"]:
            spir["capabilities"].append("heritage_morphology")
    if paninian_edges and "paninian_syntax" not in spir["capabilities"]:
        spir["capabilities"].append("paninian_syntax")
    if basic_ud and "ud_syntax" not in spir["capabilities"]:
        spir["capabilities"].append("ud_syntax")
    if clauses and "clause_graph" not in spir["capabilities"]:
        spir["capabilities"].append("clause_graph")
    if enhanced_ud and "enhanced_ud" not in spir["capabilities"]:
        spir["capabilities"].append("enhanced_ud")

    if kag_mode.lower() == "full":
        kag = build_kag_from_syntax(spir, artifacts_dir=artifacts_dir)
        spir["semantics"] = make_semantics(kag=kag)
        if "kag_full" not in spir["capabilities"]:
            spir["capabilities"].append("kag_full")

    return spir
