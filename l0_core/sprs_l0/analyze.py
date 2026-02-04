from __future__ import annotations

from typing import Any

from .normalize import normalize_text
from .spir import hash_artifacts_dir, hash_text, make_spir


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


def analyze(
    text: str,
    input_format: str = "auto",
    k_best: int = 5,
    return_lattice: bool = True,
    artifacts_dir: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_text(text)
    tokens = _simple_tokenize(normalized)
    segments: list[dict[str, Any]] = []
    if return_lattice and tokens:
        segments = [
            {
                "tokens": list(range(len(tokens))),
                "conf": 1.0,
            }
        ]
    artifacts_hash = hash_artifacts_dir(artifacts_dir)
    input_hash = hash_text(normalized)
    spir = make_spir(
        normalized_text=normalized,
        tokens=tokens,
        segments=segments,
        artifacts_hash=artifacts_hash,
        input_hash=input_hash,
        input_format=input_format,
    )
    spir["meta"]["k_best"] = k_best
    spir["meta"]["return_lattice"] = return_lattice
    return spir
