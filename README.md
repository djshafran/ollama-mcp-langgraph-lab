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

**BDD + Allure**
```bash
behave -f allure_behave.formatter:AllureFormatter -o allure-results
allure serve allure-results
```
Default testcontainers compose file: `tests/compose/docker-compose.test.yml` (L0 + hydra_mock).

**Important Notes**
1. Default profile is `gpu` (see `lab.sh`). Use `./lab.sh up cpu` if you do not have GPU support.
2. Ollama is exposed on `http://localhost:11434`.
3. MCP server is exposed on `http://localhost:8000/mcp`.
4. L0 MCP server is exposed on `http://localhost:8001/mcp`.
5. Model, context size, and reasoning mode are controlled in `.env`.
6. Flow mode runs the explicit graph: `python /app/flow.py "<prompt>"`.

**L0 Syntax + Semantics Layer (SPIR v0.4.0)**
L0 now produces a structured syntax+semantics package:
1. `syntax.paninian_edges`: list of `{head, dep, role}` (karaka graph).
2. `syntax.ud.basic_edges`: basic UD tree (`rel` labels, exactly one root).
3. `syntax.ud.enhanced_edges` + `syntax.ud.empty_nodes`: enhanced UD layer for shared args/ellipsis.
4. `syntax.clauses` + `syntax.discourse_links`: clause/discourse layer.
5. `semantics.kag`: Event+Deontic KAG with provenance.

Backend selection:
1. `SYNTAX_BACKEND=rules` (default) uses internal rule-based attachment.
2. `SYNTAX_BACKEND=hydra` / `hyderabad` uses the external Hyderabad/Samsaadhanii parser.
3. `SYNTAX_BACKEND=none` disables syntax.

Hyderabad parser wiring:
1. `HYD_PARSER_URL` to call a running HTTP/CGI service.
2. `HYD_PARSER_CMD` to execute a local CLI command (use `{text}` placeholder or stdin).
3. `KARAKA_UD_MAP_PATH` to override karaka->UD mapping JSON.
4. `SYNTAX_OVERRIDES_PATH` to apply deterministic per-input graph patches.

New L0 MCP tools:
1. `l0_analyze` (SPIR v0.4 output).
2. `l0_query_understand` (NL|SPIR -> KAG query + retrieval plan).
3. `l0_retrieve` (hybrid BM25+vector+RRF+rereank retrieval).
4. `l0_export` (sidecars: CoNLL-U basic/enhanced, KAG JSONL, align JSON).

CLI example:
```bash
SYNTAX_BACKEND=rules python -m sprs_l0.cli analyze --in src/l0/data/prepared/corpus.jsonl --out workspace/spir_samples_v04.jsonl
python -m sprs_l0.cli validate --in workspace/spir_samples_v04.jsonl
python -m sprs_l0.cli export --in workspace/spir_samples_v04.jsonl --out-dir workspace/exports
```
