from __future__ import annotations

import json

import allure
from behave import given, when, then

from tests.bdd.support.mcp_http import extract_json_from_tool_call


@given('input text "{text}"')
def step_given_input_text(context, text: str):
    context.input_text = text


def _pick_tool(tools: dict, preferred: list[str]) -> str:
    tool_names: list[str] = []
    try:
        tool_names = [t.get("name") for t in tools.get("result", {}).get("tools", []) if isinstance(t, dict)]
    except Exception:
        tool_names = []

    for name in preferred:
        if name in tool_names:
            return name
    raise AssertionError(f"Required tool not found. Available: {tool_names}")


@when("I analyze input text via L0 MCP")
def step_when_analyze_text(context):
    text = getattr(context, "input_text", "").strip()
    assert text, "Input text is missing"

    tools = context.mcp.tools_list()
    allure.attach(
        json.dumps(tools, ensure_ascii=False, indent=2),
        name="tools/list response",
        attachment_type=allure.attachment_type.JSON,
    )

    tool_name = _pick_tool(tools, ["l0_analyze", "analyze"])
    resp = context.mcp.tools_call(
        tool_name,
        {
            "text": text,
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


@then('SPIR normalized_text equals "{expected}"')
def step_then_normalized_text(context, expected: str):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    actual = spir.get("normalized_text")
    assert actual == expected, f"normalized_text mismatch: {actual!r} != {expected!r}"


@then("SPIR validates via L0 MCP")
def step_then_validate_spir(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"

    tools = context.mcp.tools_list()
    tool_name = _pick_tool(tools, ["l0_validate", "validate"])
    resp = context.mcp.tools_call(tool_name, {"spir": spir})

    allure.attach(
        json.dumps(resp, ensure_ascii=False, indent=2),
        name="tools/call validate response",
        attachment_type=allure.attachment_type.JSON,
    )

    try:
        result = extract_json_from_tool_call(resp)
    except Exception:
        result = resp.get("result") if isinstance(resp, dict) else None

    assert isinstance(result, dict), f"Validate response invalid: {result!r}"
    assert result.get("ok") is True, f"SPIR validation failed: {result}"


@then("SPIR syntax paninian edges are present")
def step_then_paninian_edges_present(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    syntax = spir.get("syntax", {})
    assert isinstance(syntax, dict), "SPIR.syntax must be object"
    edges = syntax.get("paninian_edges", [])
    assert isinstance(edges, list), "SPIR.syntax.paninian_edges must be list"
    assert len(edges) > 0, "SPIR.syntax.paninian_edges is empty"


@then('SPIR version equals "{expected}"')
def step_then_spir_version(context, expected: str):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    meta = spir.get("meta", {})
    assert isinstance(meta, dict), "SPIR.meta must be object"
    assert meta.get("version") == expected, f"Unexpected SPIR version: {meta.get('version')}"


@then("SPIR tokens are present")
def step_then_tokens_present(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    tokens = spir.get("tokens", [])
    assert isinstance(tokens, list), "SPIR.tokens must be list"
    assert len(tokens) > 0, "SPIR.tokens is empty"


@then("SPIR UD basic edges are present")
def step_then_ud_basic_edges_present(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    syntax = spir.get("syntax", {})
    ud = syntax.get("ud", {}) if isinstance(syntax, dict) else {}
    basic = ud.get("basic_edges", []) if isinstance(ud, dict) else []
    assert isinstance(basic, list), "SPIR.syntax.ud.basic_edges must be list"
    assert len(basic) > 0, "SPIR.syntax.ud.basic_edges is empty"


@then("SPIR has KAG graph")
def step_then_has_kag(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"
    semantics = spir.get("semantics", {})
    assert isinstance(semantics, dict), "SPIR.semantics must be object"
    kag = semantics.get("kag", {})
    assert isinstance(kag, dict), "SPIR.semantics.kag must be object"
    nodes = kag.get("nodes", [])
    edges = kag.get("edges", [])
    assert isinstance(nodes, list), "KAG nodes must be list"
    assert isinstance(edges, list), "KAG edges must be list"
    assert len(nodes) > 0, "KAG nodes are empty"
