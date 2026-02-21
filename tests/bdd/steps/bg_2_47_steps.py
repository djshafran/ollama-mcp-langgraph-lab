from __future__ import annotations

import json
import re
from pathlib import Path

import allure
from behave import given, when, then

from tests.bdd.support.mcp_http import extract_json_from_tool_call

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
NON_DEVANAGARI_RE = re.compile(r"[^\u0900-\u097F\s]")
DIGITS_RE = re.compile(r"[0-9\u0966-\u096F]")
DANDA_RE = re.compile(r"[\u0964\u0965]")


def extract_text_47_block(md_text: str) -> list[str]:
    lines = md_text.splitlines()
    in_47 = False
    out: list[str] = []
    for line in lines:
        if re.match(r"^\s*TEXT\s+47\b", line):
            in_47 = True
            continue
        if in_47:
            if re.match(r"^\s*TEXT\s+\d+\b", line):
                break
            s = line.strip()
            if not s:
                continue
            if DEVANAGARI_RE.search(s):
                out.append(s)
    return out


def clean_devanagari(text: str) -> str:
    text = DIGITS_RE.sub(" ", text)
    text = DANDA_RE.sub(" ", text)
    text = NON_DEVANAGARI_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@given('raw file "{rel_path}" contains BG TEXT 47')
def step_given_file_contains_text_47(context, rel_path: str):
    project_root = Path(__file__).resolve().parents[3]
    fp = project_root / rel_path
    assert fp.exists(), f"File not found: {fp}"

    md = fp.read_text(encoding="utf-8")
    block = extract_text_47_block(md)

    allure.attach(
        "\n".join(block) if block else "(not found)",
        name="BG TEXT 47 excerpt (raw)",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert block, "TEXT 47 block not found in markdown"

    context.bg_2_47_lines = block
    cleaned_all = [clean_devanagari(line) for line in block]
    cleaned_all = [line for line in cleaned_all if line]
    adhikara_lines = [line for line in cleaned_all if ("अधिकार" in line or "धिकार" in line)]
    source_lines = adhikara_lines or cleaned_all
    context.bg_2_47_text = " ".join(source_lines)


@when("I analyze BG TEXT 47 via L0 MCP")
def step_when_analyze(context):
    verse = getattr(context, "bg_2_47_text", "").strip()
    assert verse, "No verse text in context"

    tools = context.mcp.tools_list()
    tool_names = []
    try:
        tool_names = [t.get("name") for t in tools.get("result", {}).get("tools", []) if isinstance(t, dict)]
    except Exception:
        tool_names = []

    allure.attach(
        json.dumps(tools, ensure_ascii=False, indent=2),
        name="tools/list response",
        attachment_type=allure.attachment_type.JSON,
    )

    preferred = ["l0_analyze", "analyze"]
    tool_name = next((n for n in preferred if n in tool_names), None)
    assert tool_name, f"Analyze tool not found. Available: {tool_names}"

    resp = context.mcp.tools_call(
        tool_name,
        {
            "text": verse,
            "input_format": "auto",
            "k_best": 5,
            "return_lattice": True,
            "return_ud": True,
            "return_syntax": True,
            "include_enhanced": True,
            "include_kag": True,
            "include_provenance": True,
        },
    )

    allure.attach(
        json.dumps(resp, ensure_ascii=False, indent=2),
        name="tools/call raw response",
        attachment_type=allure.attachment_type.JSON,
    )

    spir = extract_json_from_tool_call(resp)

    allure.attach(
        json.dumps(spir, ensure_ascii=False, indent=2),
        name="SPIR (parsed)",
        attachment_type=allure.attachment_type.JSON,
    )

    context.spir = spir


@then('SPIR tokens contain lemma "{lemma}"')
def step_then_contains_lemma(context, lemma: str):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"

    tokens = spir.get("tokens", [])
    assert isinstance(tokens, list), "SPIR.tokens must be list"

    lemmas = []
    for t in tokens:
        if isinstance(t, dict) and isinstance(t.get("lemma"), str):
            lemmas.append(t["lemma"])

    allure.attach("\n".join(lemmas), name="lemmas list", attachment_type=allure.attachment_type.TEXT)
    assert lemma in lemmas, f'Lemma "{lemma}" not found. Got: {lemmas}'


@then("SPIR has heritage morphology details")
def step_then_has_heritage_details(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"

    tokens = spir.get("tokens", [])
    assert isinstance(tokens, list), "SPIR.tokens must be list"

    found = False
    for t in tokens:
        if not isinstance(t, dict):
            continue
        feats = t.get("feats")
        if not isinstance(feats, dict):
            continue
        heritage = feats.get("heritage")
        if isinstance(heritage, dict) and heritage.get("analyses"):
            found = True
            break

    assert found, "No token contains feats.heritage.analyses"


@then('SPIR capabilities include "{capability}"')
def step_then_capability_includes(context, capability: str):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"

    caps = spir.get("capabilities", [])
    assert isinstance(caps, list), "SPIR.capabilities must be list"
    assert capability in caps, f'Capability "{capability}" not found. Got: {caps}'


@then("SPIR paninian edges have roles")
def step_then_paninian_roles(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    syntax = spir.get("syntax", {})
    edges = syntax.get("paninian_edges", []) if isinstance(syntax, dict) else []
    assert isinstance(edges, list), "SPIR.syntax.paninian_edges must be list"
    missing = []
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            missing.append(i)
            continue
        role = edge.get("role")
        if not isinstance(role, str) or not role.strip():
            missing.append(i)
    assert not missing, f"Paninian edges missing role at indices: {missing}"


@then('SPIR UD includes relation "{relation}"')
def step_then_ud_has_relation(context, relation: str):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    syntax = spir.get("syntax", {})
    ud = syntax.get("ud", {}) if isinstance(syntax, dict) else {}
    basic = ud.get("basic_edges", []) if isinstance(ud, dict) else []
    rels = []
    for edge in basic:
        if isinstance(edge, dict):
            rel = edge.get("rel") or edge.get("relation")
            if isinstance(rel, str):
                rels.append(rel)
    assert relation in rels, f'UD relation "{relation}" not found. Got: {rels}'


@then("SPIR has enhanced UD layer")
def step_then_has_enhanced_ud(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    syntax = spir.get("syntax", {})
    ud = syntax.get("ud", {}) if isinstance(syntax, dict) else {}
    enhanced = ud.get("enhanced_edges", []) if isinstance(ud, dict) else []
    empty_nodes = ud.get("empty_nodes", []) if isinstance(ud, dict) else []
    assert isinstance(enhanced, list), "enhanced_edges must be list"
    assert isinstance(empty_nodes, list), "empty_nodes must be list"
    assert len(enhanced) > 0 or len(empty_nodes) > 0, "Enhanced UD layer is empty"


@then("SPIR has deontic norms")
def step_then_has_deontic_norms(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    semantics = spir.get("semantics", {})
    kag = semantics.get("kag", {}) if isinstance(semantics, dict) else {}
    norms = kag.get("norms", []) if isinstance(kag, dict) else []
    assert isinstance(norms, list), "KAG norms must be list"
    assert len(norms) > 0, "No deontic norms found in KAG"


@then("SPIR enhanced UD empty node ids are UD-compatible")
def step_then_ud_empty_ids_are_compatible(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    empty_nodes = ((spir.get("syntax", {}) or {}).get("ud", {}) or {}).get("empty_nodes", [])
    assert isinstance(empty_nodes, list), "SPIR.syntax.ud.empty_nodes must be list"
    for node in empty_nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        assert isinstance(node_id, str), "empty node id must be string"
        if node_id:
            parts = node_id.split(".")
            assert len(parts) == 2 and all(p.isdigit() for p in parts), f"invalid empty id: {node_id}"


@then("SPIR KAG norms have clause-aware provenance")
def step_then_norms_have_clause_provenance(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    clauses = ((spir.get("syntax") or {}).get("clauses")) or []
    clause_ids = {c.get("clause_id") for c in clauses if isinstance(c, dict)}
    norms = ((((spir.get("semantics") or {}).get("kag") or {}).get("norms")) or [])
    assert isinstance(norms, list), "KAG norms must be list"
    assert norms, "No norms to validate provenance"
    for norm in norms:
        if not isinstance(norm, dict):
            continue
        prov = norm.get("provenance") or {}
        clause_id = prov.get("clause_id")
        assert isinstance(clause_id, str), "norm provenance.clause_id must be string"
        assert clause_id in clause_ids, f"norm clause_id not found: {clause_id}"
