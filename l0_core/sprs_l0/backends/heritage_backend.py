from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from heritage import HeritagePlatform
except Exception as exc:  # pragma: no cover - optional dependency
    HeritagePlatform = None  # type: ignore
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

_HP: HeritagePlatform | None = None


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw.isdigit() else default


def get_platform() -> HeritagePlatform:
    global _HP
    if _HP is not None:
        return _HP

    if HeritagePlatform is None:  # pragma: no cover - optional dependency
        raise RuntimeError("heritage package is not installed") from _IMPORT_ERROR

    method = os.getenv("HERITAGE_METHOD", "shell").strip() or "shell"
    base_dir = os.getenv("HERITAGE_BASE_DIR", "").strip()
    timeout = _env_int("HERITAGE_REQUEST_TIMEOUT", 5)
    attempts = _env_int("HERITAGE_REQUEST_ATTEMPTS", 4)

    kwargs: dict[str, Any] = {
        "method": method,
        "request_timeout": timeout,
        "request_attempts": attempts,
    }
    if base_dir:
        kwargs["base_dir"] = Path(base_dir)

    hp = HeritagePlatform(**kwargs)

    lexicon = os.getenv("HERITAGE_LEXICON", "").strip()
    if lexicon:
        hp.set_lexicon(lexicon)

    _HP = hp
    return hp


def analyze_sentence(text: str) -> tuple[int, Any]:
    hp = get_platform()
    analyses = hp.get_analysis(text, sentence=True)
    if isinstance(analyses, dict) and analyses:
        keys = sorted(analyses.keys(), key=lambda k: (str(k).isdigit() is False, str(k)))
        key = keys[0]
        try:
            sol_id = int(key)
        except Exception:
            sol_id = 0
        return sol_id, analyses[key]
    return 0, {"words": []}
