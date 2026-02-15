from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

SPIR_VERSION = "0.4.0"
DEFAULT_CAPABILITIES = [
    "normalize",
    "segment_lattice",
    "lemma",
    "morph_stub",
    "syntax_v04",
    "kag_event_deontic",
]


def hash_text(text: str) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def hash_artifacts_dir(artifacts_dir: str | Path | None) -> str:
    if artifacts_dir is None:
        return "none"
    p = Path(artifacts_dir)
    if not p.exists():
        return "none"
    h = hashlib.sha256()
    files = sorted([f for f in p.rglob("*") if f.is_file()])
    for f in files:
        rel = str(f.relative_to(p)).replace("\\", "/")
        h.update(rel.encode("utf-8"))
        h.update(str(f.stat().st_size).encode("utf-8"))
    return h.hexdigest()


def spir_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "meta",
            "normalized_text",
            "tokens",
            "segments",
            "capabilities",
            "syntax",
            "semantics",
        ],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["version", "artifacts_hash", "input_hash"],
            },
            "normalized_text": {"type": "string"},
            "tokens": {"type": "array"},
            "segments": {"type": "array"},
            "capabilities": {"type": "array"},
            "syntax": {"type": "object"},
            "semantics": {"type": "object"},
            "provenance": {"type": "object"},
        },
    }


def make_spir(
    normalized_text: str,
    tokens: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    artifacts_hash: str,
    input_hash: str,
    syntax: dict[str, Any] | None = None,
    semantics: dict[str, Any] | None = None,
    capabilities: list[str] | None = None,
    input_format: str | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "meta": {
            "version": SPIR_VERSION,
            "artifacts_hash": artifacts_hash,
            "input_hash": input_hash,
            "input_format": input_format or "auto",
        },
        "normalized_text": normalized_text,
        "tokens": tokens,
        "segments": segments,
        "syntax": syntax or {},
        "semantics": semantics or {},
        "provenance": provenance or {},
        "capabilities": capabilities or list(DEFAULT_CAPABILITIES),
    }
