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

**L0 Syntax Layer (Karaka + UD)**
L0 now produces a Paninian dependency graph and a UD-style dependency list.
SPIR v0.3.0 adds:
1. `dependencies`: list of `{head, dep, role}` where `role` is a karaka label (e.g. `kartṛ`, `karman`, `karaṇa`, `saṃpradāna`, `apādāna`, `adhikaraṇa`, `sambandha`, `root`).
2. `ud_dependencies`: list of `{head, dep, relation}` mapped to Universal Dependencies (`nsubj`, `obj`, `obl:inst`, `iobj`, `obl:abl`, `obl:loc`, `nmod:poss`, `root`, `dep`).

Backend selection:
1. `SYNTAX_BACKEND=rules` (default) uses internal rule-based attachment.
2. `SYNTAX_BACKEND=hydra` / `hyderabad` uses the external Hyderabad/Samsaadhanii parser.
3. `SYNTAX_BACKEND=none` disables syntax (dependencies empty).

Hyderabad parser wiring:
1. `HYD_PARSER_URL` to call a running HTTP/CGI service.
2. `HYD_PARSER_CMD` to execute a local CLI command (use `{text}` placeholder or stdin).

CLI example:
```bash
SYNTAX_BACKEND=rules python -m sprs_l0.cli analyze --in src/l0/data/prepared/corpus.jsonl --out workspace/spir_samples.jsonl
python -m sprs_l0.cli analyze --in src/l0/data/prepared/corpus.jsonl --out workspace/spir_samples.jsonl --syntax-backend hydra
```
