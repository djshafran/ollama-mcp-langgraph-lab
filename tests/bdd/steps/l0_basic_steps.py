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
