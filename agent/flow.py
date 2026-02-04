import os
import sys
import json
import asyncio
from typing import Any, TypedDict

from langchain_ollama import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, END


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


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
    query_spir: dict
    plan: dict
    passages: list
    compact: dict
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


async def _pivot(tool_map: dict[str, Any], state: FlowState) -> FlowState:
    query = state["query"]
    spir = await _call_tool(tool_map, "l0_analyze", {"text": query})
    return {"query_spir": spir}


async def _plan(llm: ChatOllama, tool_map: dict[str, Any], state: FlowState) -> FlowState:
    backend = os.getenv("PLAN_BACKEND", "llm").strip().lower()
    if backend == "l0":
        keys = await _call_tool(
            tool_map,
            "l0_keys",
            {"query_spir": state["query_spir"], "max_terms": 12},
        )
        plan = {
            "backend": "l0",
            "keywords": keys.get("keywords", []),
            "steps": ["retrieve", "compress", "reconcile", "answer"],
        }
        return {"plan": plan}
    if backend == "rules":
        plan = {
            "backend": "rules",
            "steps": ["retrieve", "compress", "reconcile", "answer"],
        }
        return {"plan": plan}

    prompt = (
        "Create a strict JSON plan with fields: steps (array of strings), rationale."
    )
    response = await llm.ainvoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": state["query"]},
    ])
    text = getattr(response, "content", str(response))
    try:
        plan = json.loads(text)
    except json.JSONDecodeError:
        plan = {"backend": "llm", "raw": text}
    return {"plan": plan}


async def _retrieve(tool_map: dict[str, Any], state: FlowState) -> FlowState:
    passages = []
    try:
        files = await _call_tool(tool_map, "list_files", {"rel_dir": "kb"})
    except Exception:
        files = []

    txt_files = [f for f in files if str(f).endswith(".txt")]
    for fp in txt_files[:5]:
        try:
            text = await _call_tool(tool_map, "read_text", {"rel_path": fp})
            passages.append({"id": fp, "text": text})
        except Exception:
            continue
    return {"passages": passages}


async def _compress(tool_map: dict[str, Any], state: FlowState) -> FlowState:
    compact = await _call_tool(
        tool_map,
        "l0_compress",
        {
            "query_spir": state["query_spir"],
            "passages": state.get("passages", []),
            "max_chars": 2000,
        },
    )
    return {"compact": compact}


async def _reconcile(llm: ChatOllama, state: FlowState) -> FlowState:
    backend = os.getenv("RECONCILE_BACKEND", "llm").strip().lower()
    if backend == "rules":
        return {"facts": {"facts": []}}

    prompt = "Extract key facts as strict JSON with field 'facts' (array)."
    response = await llm.ainvoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(state.get("compact", {}))},
    ])
    text = getattr(response, "content", str(response))
    try:
        facts = json.loads(text)
    except json.JSONDecodeError:
        facts = {"raw": text}
    return {"facts": facts}


async def _answer(llm: ChatOllama, state: FlowState) -> FlowState:
    prompt = "Answer the user using the provided evidence. Be concise."
    payload = {
        "query": state["query"],
        "plan": state.get("plan"),
        "compact": state.get("compact"),
        "facts": state.get("facts"),
    }
    response = await llm.ainvoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload)},
    ])
    text = getattr(response, "content", str(response))
    return {"answer": text}


async def run_once(prompt: str) -> None:
    llm = _llm_from_env()
    tools = await _tool_map()

    graph = StateGraph(FlowState)

    async def pivot(state: FlowState) -> FlowState:
        return await _pivot(tools, state)

    async def plan(state: FlowState) -> FlowState:
        return await _plan(llm, tools, state)

    async def retrieve(state: FlowState) -> FlowState:
        return await _retrieve(tools, state)

    async def compress(state: FlowState) -> FlowState:
        return await _compress(tools, state)

    async def reconcile(state: FlowState) -> FlowState:
        return await _reconcile(llm, state)

    async def answer(state: FlowState) -> FlowState:
        return await _answer(llm, state)

    graph.add_node("pivot", pivot)
    graph.add_node("plan", plan)
    graph.add_node("retrieve", retrieve)
    graph.add_node("compress", compress)
    graph.add_node("reconcile", reconcile)
    graph.add_node("answer", answer)

    graph.set_entry_point("pivot")
    graph.add_edge("pivot", "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "compress")
    graph.add_edge("compress", "reconcile")
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
