import os
import sys
import json
import asyncio
from typing import Any, TypedDict

from langchain_ollama import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, END


def _env_reasoning() -> bool | None:
    v = os.getenv("THINKING_TRACE", "").strip().lower()
    if not v:
        v = os.getenv("REASONING", "").strip().lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    return None


class FlowState(TypedDict, total=False):
    query: str
    spir: dict
    query_bundle: dict
    retrieved: dict
    evidence_pack: dict
    facts: dict
    answer: str


def _llm_from_env() -> ChatOllama:
    model_name = os.getenv("MODEL", "qwen3:8b")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    temperature = float(os.getenv("TEMPERATURE", "0.2"))
    num_ctx = int(os.getenv("NUM_CTX", "2048"))
    reasoning = _env_reasoning()
    return ChatOllama(
        model=model_name,
        base_url=ollama_base_url,
        temperature=temperature,
        num_ctx=num_ctx,
        reasoning=reasoning,
    )


async def _tool_map() -> dict[str, Any]:
    mcp_url = os.getenv("MCP_URL", "http://mcp:8000/mcp")
    servers = {"lab": {"transport": "http", "url": mcp_url}}

    l0_url = os.getenv("L0_MCP_URL", "http://l0:8000/mcp").strip()
    if l0_url:
        servers["l0"] = {"transport": "http", "url": l0_url}

    client = MultiServerMCPClient(servers)
    tools = await client.get_tools()
    tool_map: dict[str, Any] = {}
    for tool in tools:
        tool_map[tool.name] = tool
        for sep in ("__", ".", ":"):
            if sep in tool.name:
                short = tool.name.split(sep)[-1]
                if short not in tool_map:
                    tool_map[short] = tool
    return tool_map


async def _call_tool(tool_map: dict[str, Any], name: str, payload: dict) -> Any:
    tool = tool_map.get(name)
    if not tool:
        raise RuntimeError(f"tool not found: {name}")
    return await tool.ainvoke(payload)


async def _analyze(tool_map: dict[str, Any], state: FlowState) -> FlowState:
    spir = await _call_tool(
        tool_map,
        "l0_analyze",
        {
            "text": state["query"],
            "include_kag": True,
            "include_provenance": True,
            "include_enhanced": True,
        },
    )
    return {"spir": spir}


async def _query_understand(tool_map: dict[str, Any], state: FlowState) -> FlowState:
    query_bundle = await _call_tool(
        tool_map,
        "l0_query_understand",
        {"spir": state["spir"], "max_terms": 12},
    )
    return {"query_bundle": query_bundle}


async def _retrieve(tool_map: dict[str, Any], state: FlowState) -> FlowState:
    bundle = state.get("query_bundle", {})
    kag_query = bundle.get("kag_query", {})
    plan = bundle.get("retrieval_plan", {})
    retrieved = await _call_tool(
        tool_map,
        "l0_retrieve",
        {
            "kag_query": kag_query,
            "top_k": 5,
            "filters": plan.get("filters") or {},
        },
    )
    return {"retrieved": retrieved}


async def _evidence_pack(tool_map: dict[str, Any], state: FlowState) -> FlowState:
    candidates = (state.get("retrieved") or {}).get("candidates", [])
    passages = [{"id": c.get("id"), "text": c.get("text", "")} for c in candidates]
    compact = await _call_tool(
        tool_map,
        "l0_compress",
        {
            "query_spir": state["spir"],
            "passages": passages,
            "max_chars": 2500,
        },
    )
    return {"evidence_pack": compact}


async def _reconcile(llm: ChatOllama, state: FlowState) -> FlowState:
    backend = os.getenv("RECONCILE_BACKEND", "llm").strip().lower()
    if backend == "rules":
        return {"facts": {"facts": []}}

    prompt = "Extract key facts as strict JSON with field 'facts' (array) and include provenance when possible."
    payload = {
        "query": state.get("query"),
        "spir_meta": (state.get("spir") or {}).get("meta"),
        "kag_norms": ((((state.get("spir") or {}).get("semantics") or {}).get("kag") or {}).get("norms"))
        or [],
        "retrieved": state.get("retrieved"),
        "evidence_pack": state.get("evidence_pack"),
    }
    response = await llm.ainvoke(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    )
    text = getattr(response, "content", str(response))
    try:
        facts = json.loads(text)
    except json.JSONDecodeError:
        facts = {"raw": text}
    return {"facts": facts}


async def _answer(llm: ChatOllama, state: FlowState) -> FlowState:
    prompt = (
        "Answer the user concisely using facts and evidence. "
        "Always mention provenance references when available."
    )
    payload = {
        "query": state["query"],
        "facts": state.get("facts"),
        "provenance": (state.get("retrieved") or {}).get("provenance"),
    }
    response = await llm.ainvoke(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    )
    return {"answer": getattr(response, "content", str(response))}


async def run_once(prompt: str) -> None:
    llm = _llm_from_env()
    tools = await _tool_map()

    graph = StateGraph(FlowState)

    async def analyze_node(state: FlowState) -> FlowState:
        return await _analyze(tools, state)

    async def query_node(state: FlowState) -> FlowState:
        return await _query_understand(tools, state)

    async def retrieve_node(state: FlowState) -> FlowState:
        return await _retrieve(tools, state)

    async def evidence_node(state: FlowState) -> FlowState:
        return await _evidence_pack(tools, state)

    async def reconcile_node(state: FlowState) -> FlowState:
        return await _reconcile(llm, state)

    async def answer_node(state: FlowState) -> FlowState:
        return await _answer(llm, state)

    graph.add_node("analyze", analyze_node)
    graph.add_node("query_understand", query_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("evidence_pack", evidence_node)
    graph.add_node("reconcile", reconcile_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "query_understand")
    graph.add_edge("query_understand", "retrieve")
    graph.add_edge("retrieve", "evidence_pack")
    graph.add_edge("evidence_pack", "reconcile")
    graph.add_edge("reconcile", "answer")
    graph.add_edge("answer", END)

    app = graph.compile()
    result = await app.ainvoke({"query": prompt})
    print(result.get("answer", "(no answer)"))


async def main() -> None:
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        await run_once(prompt)
        return

    print("Flow mode. Ctrl+C to exit.")
    while True:
        try:
            prompt = input("\nYou> ").strip()
        except KeyboardInterrupt:
            print("\nBye.")
            return
        if not prompt:
            continue
        await run_once(prompt)


if __name__ == "__main__":
    asyncio.run(main())

