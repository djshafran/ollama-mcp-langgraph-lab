import os
import sys
import asyncio

from langchain_ollama import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent


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


async def run_once(prompt: str) -> None:
    model_name = os.getenv("MODEL", "qwen3:8b")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    mcp_url = os.getenv("MCP_URL", "http://mcp:8000/mcp")
    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")
    temperature = float(os.getenv("TEMPERATURE", "0.2"))
    num_ctx = int(os.getenv("NUM_CTX", "2048"))

    reasoning = _env_reasoning()

    show_reasoning = _env_bool("SHOW_REASONING", False)

    # 1) MCP tools (HTTP transport)
    servers = {
        "lab": {
            "transport": "http",
            "url": mcp_url,
        }
    }
    l0_url = os.getenv("L0_MCP_URL", "").strip()
    if l0_url:
        servers["l0"] = {"transport": "http", "url": l0_url}

    client = MultiServerMCPClient(servers)
    tools = await client.get_tools()

    # 2) LLM via Ollama
    llm = ChatOllama(
        model=model_name,
        base_url=ollama_base_url,
        temperature=temperature,
        num_ctx=num_ctx,
        reasoning=reasoning,
    )

    # 3) Agent (LangChain create_agent)
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})

    # Print final answer
    messages = result.get("messages", [])
    if not messages:
        print("(no messages)")
        return

    last = messages[-1]
    print(getattr(last, "content", str(last)))

    # If reasoning=True, ChatOllama may return reasoning in additional_kwargs.reasoning_content
    if show_reasoning and hasattr(last, "additional_kwargs"):
        rc = last.additional_kwargs.get("reasoning_content")
        if rc:
            print("\n--- reasoning_content ---\n")
            print(rc)


async def main() -> None:
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        await run_once(prompt)
        return

    # interactive mode
    print("Interactive mode. Ctrl+C to exit.")
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
