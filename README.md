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

**L0 Syntax + Semantics Layer (SPIR v0.5.0)**
L0 now produces a structured syntax+semantics package:
1. `syntax.paninian_edges`: list of `{head, dep, role}` (karaka graph).
2. `syntax.ud.basic_edges`: basic UD tree (`rel` labels, exactly one root).
3. `syntax.ud.enhanced_edges` + `syntax.ud.empty_nodes`: UD-compatible enhanced layer (`i.j` empty nodes + DEPS).
4. `syntax.clauses` + `syntax.discourse_links`: clause/discourse layer.
5. `semantics.kag`: Event+Deontic KAG with provenance.
6. Clause spans use half-open policy: `token_span = [start, end)`.

Backend selection:
1. `SYNTAX_BACKEND=rules` (default) uses internal rule-based attachment.
2. `SYNTAX_BACKEND=hydra` / `hyderabad` uses the external Hyderabad/Samsaadhanii parser.
3. `SYNTAX_BACKEND=none` disables syntax.

UD mode:
1. `ud_mode=head_rules` (default) uses runtime `head_rules.yaml`.
2. `ud_mode=projected` uses direct Paninian->UD projection (debug/compat inside v0.5 only).
3. `ud_mode=none` disables UD.

Hyderabad parser wiring:
1. `HYD_PARSER_URL` to call a running HTTP/CGI service.
2. `HYD_PARSER_CMD` to execute a local CLI command (use `{text}` placeholder or stdin).
3. `KARAKA_UD_MAP_PATH` to override karaka->UD mapping JSON.
4. `UD_HEAD_RULES_PATH` to override active UD head rules YAML.
5. `SYNTAX_OVERRIDES_PATH` to apply deterministic per-input graph patches.
6. `RETRIEVAL_BACKEND=baseline|hybrid_prod` to choose retrieval tier.

New L0 MCP tools:
1. `l0_analyze` (SPIR v0.5 output).
2. `l0_query_understand` (NL|SPIR -> KAG query + retrieval plan).
3. `l0_retrieve` (`baseline|hybrid_prod` tiered retrieval with fallback metadata).
4. `l0_export` (sidecars: CoNLL-U basic/enhanced, KAG JSONL, align JSON).

CLI example:
```bash
SYNTAX_BACKEND=rules python -m sprs_l0.cli analyze --in src/l0/data/prepared/corpus.jsonl --out workspace/spir_samples_v05.jsonl
python -m sprs_l0.cli validate --in workspace/spir_samples_v05.jsonl
python -m sprs_l0.cli export --in workspace/spir_samples_v05.jsonl --out-dir workspace/exports
```
