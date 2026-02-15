from __future__ import annotations

from typing import Any, Iterable
import re
import unicodedata


ROLE_ROOT = "root"
ROLE_DEP = "dep"
ROLE_VOCATIVE = "vocative"
ROLE_KARTR = "kart\u1e5b"
ROLE_KARANA = "kara\u1e47a"
ROLE_SAMPRADANA = "sa\u1e43prad\u0101na"
ROLE_APADANA = "ap\u0101d\u0101na"
ROLE_ADHIKARANA = "adhikara\u1e47a"

CASE_TO_ROLE = {
    "nom": ROLE_KARTR,
    "acc": "karman",
    "ins": ROLE_KARANA,
    "dat": ROLE_SAMPRADANA,
    "abl": ROLE_APADANA,
    "loc": ROLE_ADHIKARANA,
    "gen": "sambandha",
    "voc": ROLE_VOCATIVE,
}

ROLE_ALIASES = {
    ROLE_KARTR: {ROLE_KARTR, "kartr", "kart", "karta", "k1", "agent", "subject"},
    "karman": {"karman", "k2", "object", "obj"},
    ROLE_KARANA: {ROLE_KARANA, "karana", "k3", "instrument", "inst"},
    ROLE_SAMPRADANA: {ROLE_SAMPRADANA, "sampradana", "k4", "iobj", "recipient", "dative"},
    ROLE_APADANA: {ROLE_APADANA, "apadana", "k5", "ablative"},
    "sambandha": {"sambandha", "k6", "genitive", "poss", "nmod"},
    ROLE_ADHIKARANA: {ROLE_ADHIKARANA, "adhikarana", "k7", "locative"},
    ROLE_VOCATIVE: {ROLE_VOCATIVE, "voc", "vocative"},
    ROLE_ROOT: {ROLE_ROOT},
    ROLE_DEP: {ROLE_DEP},
}

UD_ROLE_MAP = {
    ROLE_KARTR: "nsubj",
    "karman": "obj",
    ROLE_KARANA: "obl:inst",
    ROLE_SAMPRADANA: "iobj",
    ROLE_APADANA: "obl:abl",
    ROLE_ADHIKARANA: "obl:loc",
    "sambandha": "nmod:poss",
    ROLE_VOCATIVE: "vocative",
    ROLE_ROOT: "root",
    ROLE_DEP: "dep",
}

CASE_NUMBER = {
    1: "nom",
    2: "acc",
    3: "ins",
    4: "dat",
    5: "abl",
    6: "gen",
    7: "loc",
    8: "voc",
}

CASE_ALIASES = {
    "nom": {"nom", "nominative", "prathama", "prathamaa", "v1", "vibhakti1", "case1"},
    "acc": {"acc", "accusative", "dvitiya", "dvitiiya", "v2", "vibhakti2", "case2"},
    "ins": {
        "ins",
        "inst",
        "instrumental",
        "trtiya",
        "tritiya",
        "tritiiya",
        "v3",
        "vibhakti3",
        "case3",
    },
    "dat": {
        "dat",
        "dative",
        "caturthi",
        "caturthii",
        "v4",
        "vibhakti4",
        "case4",
    },
    "abl": {"abl", "ablative", "pancami", "panchami", "v5", "vibhakti5", "case5"},
    "gen": {"gen", "genitive", "sasthi", "sasthee", "v6", "vibhakti6", "case6"},
    "loc": {
        "loc",
        "locative",
        "saptami",
        "sapthami",
        "v7",
        "vibhakti7",
        "case7",
    },
    "voc": {"voc", "vocative", "sambodhana", "v8", "vibhakti8", "case8"},
}

VERB_MARKERS = {
    "verb",
    "finite",
    "lakara",
    "lakaara",
    "lakara",
    "present",
    "past",
    "future",
    "imperative",
    "optative",
    "aorist",
    "perfect",
    "imperfect",
    "injunctive",
    "parasmai",
    "atmane",
    "atmanepada",
    "pada",
    "tin",
    "tinanta",
    "ti",
    "tini",
}

INDECL_MARKERS = {"avyaya", "indeclinable", "indecl", "adv", "particle"}


def _normalize_backend(backend: str | None) -> str:
    norm = (backend or "rules").strip().lower()
    if norm == "hydra":
        norm = "hyderabad"
    return norm


def _strip_diacritics(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _iter_feature_values(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str):
                yield k
            yield from _iter_feature_values(v)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_feature_values(item)
    elif isinstance(value, str):
        yield value
    elif isinstance(value, (int, float)):
        yield str(value)


def _tokenize_feature_text(text: str) -> list[str]:
    if not text:
        return []
    cleaned = _strip_diacritics(text).lower()
    parts = re.split(r"[^a-z0-9]+", cleaned)
    return [p for p in parts if p]


def _collect_feature_tokens(token: dict[str, Any]) -> list[str]:
    feats = token.get("feats") or {}
    tags: list[str] = []

    pos = token.get("pos")
    if isinstance(pos, str):
        tags.extend(_tokenize_feature_text(pos))

    for value in _iter_feature_values(feats):
        tags.extend(_tokenize_feature_text(value))

    return tags


def _case_from_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, int):
        return CASE_NUMBER.get(value)
    if isinstance(value, float):
        if value.is_integer():
            return CASE_NUMBER.get(int(value))
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return CASE_NUMBER.get(int(stripped))
        tokens = _tokenize_feature_text(stripped)
        for case_name, aliases in CASE_ALIASES.items():
            if any(alias in tokens for alias in aliases):
                return case_name
        # Try to detect vibhakti numbers in the raw string.
        m = re.search(r"(?:vibhakti|case|vib|v)\s*[:=]?\s*([1-8])", stripped, re.IGNORECASE)
        if m:
            return CASE_NUMBER.get(int(m.group(1)))
    if isinstance(value, dict):
        for v in value.values():
            found = _case_from_value(v)
            if found:
                return found
    if isinstance(value, (list, tuple, set)):
        for item in value:
            found = _case_from_value(item)
            if found:
                return found
    return None


def _detect_case(token: dict[str, Any]) -> str | None:
    feats = token.get("feats") or {}
    if isinstance(feats, dict):
        for key in (
            "case",
            "vibhakti",
            "vibhakti_no",
            "vibhakti_number",
            "vibhakti_id",
            "case_number",
        ):
            if key in feats:
                found = _case_from_value(feats.get(key))
                if found:
                    return found

        heritage = feats.get("heritage")
        if isinstance(heritage, dict):
            analyses = heritage.get("analyses")
            found = _case_from_value(analyses)
            if found:
                return found

    # Fallback: scan all feature tokens for case aliases.
    tokens = _collect_feature_tokens(token)
    for case_name, aliases in CASE_ALIASES.items():
        if any(alias in tokens for alias in aliases):
            return case_name
    return None


def _is_verb(token: dict[str, Any]) -> bool:
    pos = token.get("pos")
    if isinstance(pos, str) and pos.upper() in {"VERB", "AUX"}:
        return True

    tokens = _collect_feature_tokens(token)
    if any(marker in tokens for marker in VERB_MARKERS):
        return True

    # Heuristic: presence of person/number tags like 3sg/3pl.
    blob = " ".join(tokens)
    if re.search(r"\b[123](sg|pl|s|p)\b", blob):
        return True

    return False


def _is_indeclinable(token: dict[str, Any]) -> bool:
    tokens = _collect_feature_tokens(token)
    return any(marker in tokens for marker in INDECL_MARKERS)


def _pick_root(tokens: list[dict[str, Any]]) -> int | None:
    if not tokens:
        return None

    for idx, token in enumerate(tokens):
        if _is_verb(token):
            return idx

    for idx, token in enumerate(tokens):
        case = _detect_case(token)
        if case == "nom":
            return idx

    for idx, token in enumerate(tokens):
        if not _is_indeclinable(token):
            return idx

    return 0


def _rules_dependencies(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    root_idx = _pick_root(tokens)
    if root_idx is None:
        return []

    deps: list[dict[str, Any]] = [{"head": None, "dep": root_idx, "role": ROLE_ROOT}]
    for i, token in enumerate(tokens):
        if i == root_idx:
            continue

        role = ROLE_DEP
        case = _detect_case(token)
        if case:
            role = CASE_TO_ROLE.get(case, role)

        deps.append({"head": root_idx, "dep": i, "role": role})

    return deps


def normalize_role(role: str | None) -> str:
    if not role:
        return ROLE_DEP
    raw = _strip_diacritics(str(role)).lower().strip()
    for canonical, aliases in ROLE_ALIASES.items():
        for alias in aliases:
            if _strip_diacritics(alias).lower() == raw:
                return canonical
    if raw in {ROLE_ROOT, ROLE_DEP, ROLE_VOCATIVE}:
        return raw
    return str(role).strip()


def normalize_dependencies(
    dependencies: list[Any], token_count: int
) -> list[dict[str, Any]]:
    one_based = _infer_one_based(dependencies, token_count)
    out: list[dict[str, Any]] = []
    for item in dependencies:
        if isinstance(item, dict):
            head = item.get("head")
            dep_idx = item.get("dep")
            role = item.get("role") or item.get("relation")
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            head, dep_idx, role = item[:3]
        else:
            continue

        head_idx = _normalize_index(head, token_count, one_based=one_based)
        dep_idx = _normalize_index(dep_idx, token_count, one_based=one_based)
        if dep_idx is None:
            continue

        out.append({"head": head_idx, "dep": dep_idx, "role": normalize_role(role)})

    return out


def _infer_one_based(dependencies: list[Any], token_count: int) -> bool:
    values: list[int] = []
    for item in dependencies:
        if isinstance(item, dict):
            raw_values = [item.get("head"), item.get("dep")]
        elif isinstance(item, (list, tuple)):
            raw_values = list(item[:2])
        else:
            continue
        for value in raw_values:
            idx = _coerce_int(value)
            if idx is not None:
                values.append(idx)

    if not values:
        return True

    min_val = min(values)
    max_val = max(values)
    if max_val == token_count:
        return True
    if min_val >= 1:
        return True
    if max_val <= max(token_count - 1, 0):
        return False
    return True


def _normalize_index(value: Any, token_count: int, *, one_based: bool) -> int | None:
    idx = _coerce_int(value)
    if idx is None:
        return None

    if idx == -1:
        return None

    if one_based:
        if idx == 0:
            return None
        if 1 <= idx <= token_count:
            return idx - 1
        if 0 <= idx < token_count:
            return idx
    else:
        if 0 <= idx < token_count:
            return idx
        if 1 <= idx <= token_count:
            return idx - 1

    return idx


def _coerce_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            return int(stripped)
    return None


def to_ud_dependencies(dependencies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ud_deps: list[dict[str, Any]] = []
    for dep in dependencies:
        role = normalize_role(dep.get("role"))
        relation = UD_ROLE_MAP.get(role, "dep")
        ud_deps.append({"head": dep.get("head"), "dep": dep.get("dep"), "rel": relation})
    return ud_deps


def build_karaka_rules(
    tokens: list[dict[str, Any]],
    text: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    del text  # not used in the rules implementation yet
    deps = _rules_dependencies(tokens)
    return deps, {"syntax_backend": "rules"}


def parse_karaka_hyderabad(
    text: str,
    tokens: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from .backends.hyderabad_backend import parse_dependencies

    raw_deps = parse_dependencies(text=text, tokens=tokens)
    deps = normalize_dependencies(raw_deps, token_count=len(tokens))
    return deps, {"syntax_backend": "hyderabad"}


def analyze_syntax(
    text: str,
    tokens: list[dict[str, Any]],
    backend: str = "rules",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    backend = _normalize_backend(backend)

    if backend in {"none", "off"}:
        return [], [], {"syntax_backend": "none"}

    if backend == "hyderabad":
        try:
            deps, meta = parse_karaka_hyderabad(text=text, tokens=tokens)
            return deps, to_ud_dependencies(deps), meta
        except Exception as exc:  # pragma: no cover - fallback path
            deps, meta = build_karaka_rules(tokens=tokens, text=text)
            return (
                deps,
                to_ud_dependencies(deps),
                {
                    **meta,
                    "syntax_fallback_from": "hyderabad",
                    "syntax_error": str(exc),
                },
            )

    deps, meta = build_karaka_rules(tokens=tokens, text=text)
    return deps, to_ud_dependencies(deps), meta


def build_dependencies(
    tokens: list[dict[str, Any]],
    text: str,
    backend: str = "rules",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    return analyze_syntax(text=text, tokens=tokens, backend=backend)


def ud_to_conllu(tokens: list[dict[str, Any]], ud_deps: list[dict[str, Any]]) -> str:
    dep_map: dict[int, dict[str, Any]] = {}
    for dep in ud_deps:
        dep_idx = dep.get("dep")
        if isinstance(dep_idx, int) and dep_idx not in dep_map:
            dep_map[dep_idx] = dep

    lines: list[str] = []
    for idx, tok in enumerate(tokens, start=1):
        surface = tok.get("surface") or "_"
        lemma = tok.get("lemma") or "_"
        pos = tok.get("pos") or "_"
        if not isinstance(pos, str):
            pos = "_"
        dep = dep_map.get(idx - 1, {})
        head = dep.get("head")
        rel = dep.get("rel") or dep.get("relation") or "dep"
        head_idx = 0
        if isinstance(head, int):
            head_idx = head + 1
        fields = [
            str(idx),
            str(surface),
            str(lemma),
            pos,
            "_",
            "_",
            str(head_idx),
            str(rel),
            "_",
            "_",
        ]
        lines.append("\t".join(fields))
    return "\n".join(lines)
