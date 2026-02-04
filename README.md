# ollama-mcp-langgraph-lab
Docker Compose lab‑stack: Ollama + MCP (FastMCP) + LangChain/LangGraph агент. Всё настраивается через `.env`.

**Overview**
Four services in one Compose:
1. Ollama LLM server (pulls and runs models).
2. FastMCP server exposes tools over HTTP at `/mcp`.
3. L0 FastMCP server exposes deterministic SPIR tools at `/mcp`.
4. LangChain/LangGraph agent CLI that uses ChatOllama + MCP tools.

**Requirements**
1. Docker + Docker Compose.
2. For GPU mode: NVIDIA driver + `nvidia-container-toolkit` (Linux/WSL2). macOS has no GPU passthrough.

**Quickstart**
```bash
cp .env.example .env
mkdir -p workspace

# default is GPU now; use "cpu" explicitly if needed
./lab.sh up
./lab.sh pull qwen3:8b
./lab.sh ask "Сделай файл report.txt с текущим временем UTC и перечисли файлы в workspace"
```

**Common Commands**
```bash
./lab.sh up [gpu|cpu]
./lab.sh down [gpu|cpu]
./lab.sh pull <model>
./lab.sh list
./lab.sh ask "your prompt"
./lab.sh logs
```

**Important Notes**
1. Default profile is `gpu` (see `lab.sh`). Use `./lab.sh up cpu` if you do not have GPU support.
2. Ollama is exposed on `http://localhost:11434`.
3. MCP server is exposed on `http://localhost:8000/mcp`.
4. L0 MCP server is exposed on `http://localhost:8001/mcp`.
5. Model, context size, and reasoning mode are controlled in `.env`.
6. Flow mode runs the explicit graph: `python /app/flow.py "<prompt>"`.
