Ниже — максимально “лабораторный” стек **из трёх компонентов** под один `docker compose`:

1. **Ollama** (сервер LLM) — тянет и запускает Qwen (и любые другие модели из Ollama Library). ([docs.ollama.com][1])
2. **MCP‑сервер** на **FastMCP** (HTTP endpoint `/mcp`) — отдаёт инструменты (tools) вашему агенту. ([gofastmcp.com][2])
3. Агент на **LangChain** / **LangGraph** — берёт LLM через `ChatOllama`, подключает MCP tools через `langchain-mcp-adapters`, запускается как CLI. ([docs.langchain.com][3])

---

## 0) Что получится “на выходе”

* `./lab.sh up` — поднимает всё (CPU-режим).
* `./lab.sh up gpu` — поднимает всё с GPU для Ollama (если настроен GPU в Docker). ([Docker Documentation][4])
* `./lab.sh pull qwen3:8b` — скачивает модель в volume Ollama. ([ollama.com][5])
* `./lab.sh ask "..."` — гоняет промпт через LangChain‑агента, который может вызывать MCP‑инструменты. ([docs.langchain.com][3])

---

## 1) Структура папки проекта

Создайте папку (например `lab-stack/`) и внутри так:

```
lab-stack/
  docker-compose.yml
  docker-compose.gpu.yml
  .env.example
  lab.sh
  agent/
    Dockerfile
    requirements.txt
    ask.py
  mcp_server/
    Dockerfile
    server.py
  workspace/
    (любые файлы для экспериментов)
```

---

## 2) Файлы (копипастой)

### `docker-compose.yml`

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 10s
      timeout: 5s
      retries: 10

  mcp:
    build: ./mcp_server
    environment:
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8000
      - ALLOWED_DIR=/workspace
    ports:
      - "8000:8000"
    volumes:
      - ./workspace:/workspace

  agent:
    build: ./agent
    depends_on:
      - ollama
      - mcp
    environment:
      - MODEL=${MODEL}
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL}
      - MCP_URL=${MCP_URL}
      - SYSTEM_PROMPT=${SYSTEM_PROMPT}
      - TEMPERATURE=${TEMPERATURE}
      - NUM_CTX=${NUM_CTX}
      - REASONING=${REASONING}
      - SHOW_REASONING=${SHOW_REASONING}
    volumes:
      - ./workspace:/workspace

volumes:
  ollama:
```

### `docker-compose.gpu.yml` (оверрайд только для GPU)

```yaml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

> Почему так: Docker Compose рекомендует описывать GPU через `deploy.resources.reservations.devices`. ([Docker Documentation][4])
> А для Ollama в Docker GPU обычно требует `nvidia-container-toolkit` (Linux/Windows WSL2; на macOS GPU passthrough нет). ([docs.ollama.com][6])

---

### `.env.example`

```dotenv
# модель Ollama (можно менять на qwen2.5:7b, qwen2.5-coder:7b и т.д.)
MODEL=qwen3:8b

# внутри docker-сети обращаемся по имени сервиса "ollama"
OLLAMA_BASE_URL=http://ollama:11434

# MCP сервер (FastMCP) внутри docker-сети
MCP_URL=http://mcp:8000/mcp

# системный промпт агента
SYSTEM_PROMPT=You are a lab assistant. Use tools when helpful. Be concise in final answers.

# параметры генерации
TEMPERATURE=0.2

# контекст (по умолчанию у Ollama часто 2048; можно поднять, но растёт память/VRAM)
NUM_CTX=8192

# режим thinking/reasoning для поддерживаемых моделей (true/false/empty)
# В langchain-ollama есть параметр reasoning, который может вернуть reasoning отдельно. 
REASONING=true

# показывать ли reasoning в консоли (обычно лучше 0)
SHOW_REASONING=0
```

---

### `mcp_server/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir fastmcp

COPY server.py /app/server.py

EXPOSE 8000
CMD ["python", "/app/server.py"]
```

### `mcp_server/server.py`

```python
import os
from pathlib import Path
from datetime import datetime, timezone

from fastmcp import FastMCP

mcp = FastMCP("LabMCP")

ALLOWED_DIR = Path(os.getenv("ALLOWED_DIR", "/workspace")).resolve()
ALLOWED_DIR.mkdir(parents=True, exist_ok=True)

def _safe_path(rel_path: str) -> Path:
    p = (ALLOWED_DIR / rel_path).resolve()
    # простая защита от выхода из разрешённой директории
    if not str(p).startswith(str(ALLOWED_DIR)):
        raise ValueError("Path escapes ALLOWED_DIR")
    return p

@mcp.tool()
def now_utc_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()

@mcp.tool()
def list_files(rel_dir: str = ".") -> list[str]:
    """List files under ALLOWED_DIR/rel_dir."""
    d = _safe_path(rel_dir)
    if not d.exists():
        return []
    return [str(p.relative_to(ALLOWED_DIR)) for p in d.rglob("*") if p.is_file()]

@mcp.tool()
def read_text(rel_path: str) -> str:
    """Read a UTF-8 text file under ALLOWED_DIR."""
    p = _safe_path(rel_path)
    return p.read_text(encoding="utf-8")

@mcp.tool()
def write_text(rel_path: str, content: str) -> str:
    """Write a UTF-8 text file under ALLOWED_DIR."""
    p = _safe_path(rel_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"OK: wrote {len(content)} chars to {rel_path}"

@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    # FastMCP HTTP transport -> endpoint /mcp
    mcp.run(transport="http", host=host, port=port)
```

> FastMCP: `mcp.run(transport="http"... )` поднимает HTTP MCP‑endpoint по адресу `http://localhost:8000/mcp`. ([gofastmcp.com][2])

---

### `agent/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -r /app/requirements.txt

COPY ask.py /app/ask.py

CMD ["python", "/app/ask.py"]
```

### `agent/requirements.txt`

```txt
langchain
langgraph
langchain-ollama
langchain-mcp-adapters
```

### `agent/ask.py`

```python
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

async def run_once(prompt: str) -> None:
    model_name = os.getenv("MODEL", "qwen3:8b")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    mcp_url = os.getenv("MCP_URL", "http://mcp:8000/mcp")
    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")
    temperature = float(os.getenv("TEMPERATURE", "0.2"))
    num_ctx = int(os.getenv("NUM_CTX", "2048"))

    reasoning_env = os.getenv("REASONING", "").strip().lower()
    reasoning = None
    if reasoning_env in ("1", "true", "yes", "y", "on"):
        reasoning = True
    elif reasoning_env in ("0", "false", "no", "n", "off"):
        reasoning = False

    show_reasoning = _env_bool("SHOW_REASONING", False)

    # 1) Подключаем MCP tools (HTTP transport)
    client = MultiServerMCPClient(
        {
            "lab": {
                "transport": "http",
                "url": mcp_url,
            }
        }
    )
    tools = await client.get_tools()

    # 2) LLM через Ollama
    llm = ChatOllama(
        model=model_name,
        base_url=ollama_base_url,
        temperature=temperature,
        num_ctx=num_ctx,
        reasoning=reasoning,
    )

    # 3) Агент (LangChain create_agent)
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )

    # Печатаем финальный ответ
    messages = result.get("messages", [])
    if not messages:
        print("(no messages)")
        return

    last = messages[-1]
    print(getattr(last, "content", str(last)))

    # Если включён reasoning=True, ChatOllama кладёт reasoning в additional_kwargs.reasoning_content
    # (для поддерживаемых моделей)
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

    # интерактивный режим
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
```

> Важно: `ChatOllama` поддерживает `base_url`, `num_ctx` и `reasoning` (thinking‑mode) параметрами. ([reference.langchain.com][7])
> `MultiServerMCPClient` в LangChain MCP‑доках показывает `transport: "http"` и URL вида `http://localhost:8000/mcp`. ([docs.langchain.com][3])
> `create_agent` — “стандартный” способ собрать агента в LangChain v1. ([docs.langchain.com][8])

---

### `lab.sh` (обёртка)

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

compose() {
  if [[ "${PROFILE:-cpu}" == "gpu" ]]; then
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml "$@"
  else
    docker compose -f docker-compose.yml "$@"
  fi
}

cmd="${1:-help}"
shift || true

case "$cmd" in
  up)
    PROFILE="${1:-cpu}"
    export PROFILE
    echo "Starting stack (PROFILE=$PROFILE)..."
    compose up -d --build
    ;;
  down)
    PROFILE="${1:-cpu}"
    export PROFILE
    compose down
    ;;
  pull)
    PROFILE="${PROFILE:-cpu}"
    model="${1:-${MODEL:-qwen3:8b}}"
    echo "Pulling model: $model"
    compose exec -T ollama ollama pull "$model"
    ;;
  list)
    PROFILE="${PROFILE:-cpu}"
    compose exec -T ollama ollama list
    ;;
  ask)
    PROFILE="${PROFILE:-cpu}"
    if [[ $# -lt 1 ]]; then
      echo "Usage: ./lab.sh ask \"your prompt\""
      exit 1
    fi
    compose run --rm agent python /app/ask.py "$*"
    ;;
  logs)
    PROFILE="${PROFILE:-cpu}"
    compose logs -f
    ;;
  *)
    cat <<'USAGE'
Usage:
  ./lab.sh up [cpu|gpu]
  ./lab.sh down [cpu|gpu]
  ./lab.sh pull <model>
  ./lab.sh list
  ./lab.sh ask "your prompt"
  ./lab.sh logs
USAGE
    ;;
esac
```

Сделайте его исполняемым:

```bash
chmod +x lab.sh
```

---

## 3) Запуск (3 команды)

```bash
cp .env.example .env
mkdir -p workspace

./lab.sh up cpu
./lab.sh pull qwen3:8b
./lab.sh ask "Сделай файл report.txt с текущим временем UTC и перечисли файлы в workspace"
```

---

## 4) Как быстро менять модель/контекст/режим thinking

Правите `.env` и всё:

* `MODEL=qwen3:8b` (или `qwen2.5:7b`, `qwen2.5-coder:7b` и т.д.) ([ollama.com][5])
* `NUM_CTX=4096|8192|16384...` — больше контекст → выше расход RAM/VRAM. (`num_ctx` описан в `ChatOllama`). ([reference.langchain.com][7])
* `REASONING=true` — если модель поддерживает reasoning, LangChain вернёт reasoning отдельно в `reasoning_content`. ([reference.langchain.com][7])

---

## 5) GPU режим (RTX A2000 и т.п.)

```bash
./lab.sh up gpu
```

Если GPU не подхватывается:

* убедитесь, что настроен NVIDIA GPU в Docker (обычно нужен `nvidia-container-toolkit`). ([docs.ollama.com][6])
* Compose‑схема с `deploy.resources.reservations.devices` — это то, что рекомендует документация Docker Compose. ([Docker Documentation][4])

---

## 6) Мини‑проверки

Проверить, что MCP живой (с хоста):

```bash
curl -s http://localhost:8000/mcp | head
```

Проверить, что Ollama живой:

```bash
curl -s http://localhost:11434/api/tags | head
```

---

Если хочешь — могу добавить в этот же шаблон **второй MCP‑сервер “под stdio”** (например, референс‑серверы через `npx`) и подключить его вторым источником в `MultiServerMCPClient`, чтобы у тебя одновременно были:

* HTTP MCP (ваш кастомный)
* stdio MCP (готовые тулзы типа filesystem/fetch)

Но текущий шаблон уже закрывает “3 компонента” и даёт максимально простую параметрику.

[1]: https://docs.ollama.com/docker?utm_source=chatgpt.com "Docker"
[2]: https://gofastmcp.com/deployment/running-server?utm_source=chatgpt.com "Running Your Server"
[3]: https://docs.langchain.com/oss/python/langchain/mcp "Model Context Protocol (MCP) - Docs by LangChain"
[4]: https://docs.docker.com/compose/how-tos/gpu-support/?utm_source=chatgpt.com "Enable GPU support - Docker Compose"
[5]: https://ollama.com/library/qwen3/tags?utm_source=chatgpt.com "Tags · qwen3"
[6]: https://docs.ollama.com/faq?utm_source=chatgpt.com "FAQ"
[7]: https://reference.langchain.com/v0.3/python/ollama/chat_models/langchain_ollama.chat_models.ChatOllama.html "ChatOllama —  LangChain  documentation"
[8]: https://docs.langchain.com/oss/python/langchain/agents?utm_source=chatgpt.com "Agents - Docs by LangChain"
