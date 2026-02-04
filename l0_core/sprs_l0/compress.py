from __future__ import annotations

from typing import Any


def _as_passage_list(passages: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, p in enumerate(passages):
        if isinstance(p, dict):
            text = p.get("text", "")
            pid = p.get("id", str(i))
        else:
            text = str(p)
            pid = str(i)
        out.append({"id": pid, "text": text})
    return out


def compress_passages(
    query_spir: dict[str, Any],
    passages: list[Any],
    policy: str | None = None,
    max_chars: int = 2000,
) -> dict[str, Any]:
    items = _as_passage_list(passages)
    combined = "\n\n".join([p["text"] for p in items]).strip()
    if max_chars and len(combined) > max_chars:
        combined = combined[: max_chars].rstrip()
    return {
        "query_hash": query_spir.get("meta", {}).get("input_hash"),
        "policy": policy or "truncate",
        "max_chars": max_chars,
        "compact_passages": [
            {
                "id": "combined",
                "text": combined,
                "score": 1.0,
            }
        ],
    }
