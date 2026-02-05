По приложенным **артефактам (`lexicon.json`, `freqs.json`, `eval_smoke.json` и т.д.)** — **нет, это утверждение сейчас не подтверждается**.

* В вашем `lexicon.json` (который вы приложили) **вообще нет** ни `कर्मण्येवाधिकारस्ते`, ни `एवाधिकारस्ते`, ни леммы `अधिकार` (я проверил точным поиском по спискам `surface` и `lemma`).
* Плюс по `freqs.json` видно, что лексикон построен на очень маленьком объёме (порядка сотен токенов суммарно), то есть **глава 2 до TEXT 47 туда, скорее всего, просто не попадала**.
* И главное: ваш текущий `01_build_lexicon.py` **по умолчанию** строит “леммы” как `tok.lower()` при whitespace-split, т.е. **никакой “heritage‑лемматизации” в артефакте не окажется**, пока вы не делаете `--use-analyze` и не включаете `L0_BACKEND=heritage`.

То есть логика “в очищенном корпусе есть строка … и Heritage уже лемматизирует это как अधिकार в лексиконе” может быть **в принципе верной в целевом пайплайне**, но **текущие артефакты этого не демонстрируют**.

---

## Что сделать, чтобы Allure‑отчёт реально показывал “есть лемма `अधिकार`”

Ниже — именно то, что вы попросили: **behave + allure-behave + testcontainers**, где тест:

1. читает `src/l0/data/raw/bg/vedabase.io/chapter-02.md` и вытаскивает шлоку **TEXT 47**
2. поднимает контейнер **l0** (через testcontainers)
3. вызывает `tools/call` → `l0_analyze` по **HTTP MCP** (Streamable HTTP)
4. проверяет, что в SPIR есть **отдельная лемма `अधिकार`** (и при желании — что есть морфо‑детали `feats.heritage.analyses`)
5. прикладывает в Allure **сниппет исходника** + **SPIR JSON** как attachments

Для MCP по HTTP вам нужен “сеанс”: `initialize` → получить `mcp-session-id` → `notifications/initialized` → `tools/call`. Это стандартный паттерн для FastMCP по Streamable HTTP.

---

# 1) Dev‑зависимости (pyproject)

Добавьте в `src/l0/core/pyproject.toml` (или в корневой — где вы держите dev‑deps) примерно так:

```toml
[project.optional-dependencies]
dev = [
  "behave>=1.2.6",
  "allure-behave>=2.13.5",
  "allure-python-commons>=2.13.5",
  "testcontainers>=4.0.0",
  "requests>=2.31.0",
]
```

Установка:

```bash
pip install -e .[dev]
```

---

# 2) Минимальный compose-файл именно для BDD

Создайте **в корне репо** `docker-compose.bdd.yml` (чтобы testcontainers легко его находил):

```yaml
services:
  l0:
    build: ./src/l0/server
    environment:
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8000

      # ВАЖНО: чтобы тест реально ловил "अधिकार" как лемму
      - L0_BACKEND=${L0_BACKEND:-heritage}

      - L0_ARTIFACT_DIR=/artifacts/current
      - L0_DATA_DIR=/data

      # Если Heritage требует настройки — добавьте ваши HERITAGE_* env здесь
      # - HERITAGE_METHOD=shell
      # - HERITAGE_BASE_DIR=/opt/heritage
      # - HERITAGE_LEXICON=...
    ports:
      - "8000"   # без host-порта => docker сам выберет свободный (удобно для parallel runs)
    volumes:
      - ./src/l0/artifacts:/artifacts
      - ./src/l0/data:/data:ro
```

---

# 3) BDD структура

Добавьте:

```
tests/
  bdd/
    features/
      bg_2_47.feature
    steps/
      bg_2_47_steps.py
    support/
      mcp_http.py
    environment.py
```

---

## 3.1 Feature-файл `tests/bdd/features/bg_2_47.feature`

```gherkin
Feature: BG 2.47 - Heritage lemmatization through L0 MCP service

  Scenario: Fused karmanyevaadhikaraste yields lemma adhikAra
    Given raw file "src/l0/data/raw/bg/vedabase.io/chapter-02.md" contains BG TEXT 47
    When I analyze BG TEXT 47 via L0 MCP
    Then SPIR tokens contain lemma "अधिकार"
    And SPIR has heritage morphology details
```

---

## 3.2 MCP HTTP helper `tests/bdd/support/mcp_http.py`

Это делает ровно: `initialize` → header `mcp-session-id` → `notifications/initialized` → `tools/list` / `tools/call`.

```python
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests


@dataclass
class McpHttpClient:
    """Tiny MCP-over-HTTP (Streamable HTTP) client for FastMCP servers."""

    url: str
    session_id: Optional[str] = None
    _next_id: int = 0

    def _headers(self) -> dict[str, str]:
        h = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            # header name is case-insensitive, but keep canonical-ish form
            h["Mcp-Session-Id"] = self.session_id
        return h

    def _rpc(self, payload: dict[str, Any], timeout_s: float = 30.0) -> requests.Response:
        r = requests.post(self.url, headers=self._headers(), json=payload, timeout=timeout_s)
        r.raise_for_status()
        return r

    def initialize(self) -> None:
        if self.session_id:
            return

        self._next_id += 1
        init_payload = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "initialize",
            "params": {
                # protocolVersion может отличаться у вас; это безопасный дефолт
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "bdd-tests", "version": "0.1.0"},
            },
        }
        r = self._rpc(init_payload, timeout_s=30.0)

        # FastMCP возвращает session id в заголовке "mcp-session-id"
        sid = r.headers.get("mcp-session-id") or r.headers.get("Mcp-Session-Id") or r.headers.get("MCP-SESSION-ID")
        if not sid:
            raise RuntimeError(f"No mcp-session-id header from {self.url}. Headers={dict(r.headers)} Body={r.text[:300]}")

        self.session_id = sid

        # notification: initialized
        self._rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}, timeout_s=30.0)

    def wait_ready(self, timeout_s: float = 60.0) -> None:
        deadline = time.time() + timeout_s
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                self.initialize()
                return
            except Exception as e:
                last_err = e
                time.sleep(0.5)
        raise RuntimeError(f"MCP server not ready at {self.url} after {timeout_s}s") from last_err

    def tools_list(self) -> dict[str, Any]:
        self.initialize()
        self._next_id += 1
        r = self._rpc({"jsonrpc": "2.0", "id": self._next_id, "method": "tools/list", "params": {}})
        return r.json()

    def tools_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        self._next_id += 1
        r = self._rpc(
            {
                "jsonrpc": "2.0",
                "id": self._next_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        return r.json()


def extract_json_from_tool_call(resp: dict[str, Any]) -> dict[str, Any]:
    """
    FastMCP/MCP tools/call typically returns:
      {"result": {"content": [{"type":"json","json": {...}}]}}
    but sometimes content is text with JSON inside.
    """
    result = resp.get("result")
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if "json" in item and isinstance(item["json"], dict):
                        return item["json"]
                    if "text" in item and isinstance(item["text"], str):
                        t = item["text"].strip()
                        try:
                            obj = json.loads(t)
                            if isinstance(obj, dict):
                                return obj
                        except Exception:
                            pass
        # fallback: maybe the tool returned dict directly
        if all(isinstance(k, str) for k in result.keys()):
            # heuristic: looks like SPIR
            if "tokens" in result and "meta" in result:
                return result  # type: ignore[return-value]
    raise RuntimeError(f"Cannot extract JSON from tools/call response: {resp}")
```

---

## 3.3 testcontainers glue `tests/bdd/environment.py`

Тут я использую `testcontainers.compose.DockerCompose` (если вы реально хотите поднимать именно compose). Если у вас другая версия testcontainers — возможно, потребуется лёгкая подстройка конструктора, но общий смысл тот же.

```python
from __future__ import annotations

import os
from pathlib import Path

import allure

from testcontainers.compose import DockerCompose  # type: ignore

from tests.bdd.support.mcp_http import McpHttpClient


def before_all(context):
    project_root = Path(__file__).resolve().parents[2]
    compose_file = os.getenv("BDD_COMPOSE_FILE", "docker-compose.bdd.yml")

    # Стартуем l0 как отдельный compose-проект
    context.compose = DockerCompose(
        filepath=str(project_root),
        compose_file_name=compose_file,
        pull=False,
        build=True,
    )
    context.compose.start()

    # Достаём host/port для сервиса l0:8000
    host = context.compose.get_service_host("l0", 8000)
    port = context.compose.get_service_port("l0", 8000)
    context.l0_mcp_url = f"http://{host}:{port}/mcp"

    allure.attach(context.l0_mcp_url, name="L0 MCP URL", attachment_type=allure.attachment_type.TEXT)

    # Ждём готовности MCP (initialize)
    context.mcp = McpHttpClient(context.l0_mcp_url)
    context.mcp.wait_ready(timeout_s=60.0)


def after_all(context):
    compose = getattr(context, "compose", None)
    if compose is not None:
        try:
            compose.stop()
        except Exception as e:
            # чтобы это тоже попало в отчёт
            allure.attach(str(e), name="compose.stop error", attachment_type=allure.attachment_type.TEXT)
```

> Если вы хотите более “жёстко” привязаться к вашему основному `docker-compose.yml`, просто поменяйте `BDD_COMPOSE_FILE` или используйте ваш compose и поднимайте только сервис `l0`.

---

## 3.4 Steps `tests/bdd/steps/bg_2_47_steps.py`

```python
from __future__ import annotations

import json
import re
from pathlib import Path

import allure
from behave import given, when, then

from tests.bdd.support.mcp_http import extract_json_from_tool_call

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def extract_text_47_block(md_text: str) -> list[str]:
    lines = md_text.splitlines()
    in_47 = False
    out: list[str] = []
    for line in lines:
        if re.match(r"^\s*TEXT\s+47\b", line):
            in_47 = True
            continue
        if in_47:
            if re.match(r"^\s*TEXT\s+\d+\b", line):
                break
            s = line.strip()
            if not s:
                continue
            if DEVANAGARI_RE.search(s):
                out.append(s)

    return out


@given('raw file "{rel_path}" contains BG TEXT 47')
def step_given_file_contains_text_47(context, rel_path: str):
    project_root = Path(__file__).resolve().parents[3]
    fp = project_root / rel_path
    assert fp.exists(), f"File not found: {fp}"

    md = fp.read_text(encoding="utf-8")
    block = extract_text_47_block(md)

    allure.attach(
        "\n".join(block) if block else "(not found)",
        name="BG TEXT 47 excerpt (raw)",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert block, "TEXT 47 block not found in markdown"

    context.bg_2_47_lines = block
    context.bg_2_47_text = " ".join(block)


@when("I analyze BG TEXT 47 via L0 MCP")
def step_when_analyze(context):
    verse = getattr(context, "bg_2_47_text", "").strip()
    assert verse, "No verse text in context"

    # Находим имя тулзы (поддержим и префиксованный, и непрефиксованный варианты)
    tools = context.mcp.tools_list()
    tool_names = []
    try:
        tool_names = [t.get("name") for t in tools.get("result", {}).get("tools", []) if isinstance(t, dict)]
    except Exception:
        tool_names = []

    allure.attach(
        json.dumps(tools, ensure_ascii=False, indent=2),
        name="tools/list response",
        attachment_type=allure.attachment_type.JSON,
    )

    preferred = ["l0_analyze", "analyze"]
    tool_name = next((n for n in preferred if n in tool_names), None)
    assert tool_name, f"Analyze tool not found. Available: {tool_names}"

    resp = context.mcp.tools_call(
        tool_name,
        {
            "text": verse,
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


@then('SPIR tokens contain lemma "{lemma}"')
def step_then_contains_lemma(context, lemma: str):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"

    tokens = spir.get("tokens", [])
    assert isinstance(tokens, list), "SPIR.tokens must be list"

    lemmas = []
    for t in tokens:
        if isinstance(t, dict) and isinstance(t.get("lemma"), str):
            lemmas.append(t["lemma"])

    allure.attach(
        "\n".join(lemmas),
        name="lemmas list",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert lemma in lemmas, f'Lemma "{lemma}" not found. Got: {lemmas}'


@then("SPIR has heritage morphology details")
def step_then_has_heritage_details(context):
    spir = getattr(context, "spir", None)
    assert isinstance(spir, dict), "SPIR missing or invalid"

    tokens = spir.get("tokens", [])
    assert isinstance(tokens, list), "SPIR.tokens must be list"

    found = False
    for t in tokens:
        if not isinstance(t, dict):
            continue
        feats = t.get("feats")
        if not isinstance(feats, dict):
            continue
        h = feats.get("heritage")
        if isinstance(h, dict) and h.get("analyses"):
            found = True
            break

    assert found, "No token contains feats.heritage.analyses (heritage backend not active or returned empty analyses)"
```

---

# 4) Как запускать и получать Allure‑отчёт

Запуск behave с форматтером Allure:

```bash
behave -f allure_behave.formatter:AllureFormatter -o allure-results tests/bdd
```

Потом:

```bash
allure serve allure-results
```

> Allure CLI ставится отдельно (это нормально), но тесты будут генерить `allure-results` без него.

---

# 5) Почему это закроет именно ваш кейс “कर्मण्येवाधिकारस्ते → अधिकार”

* В отчёте будет attachment **с точной строкой/блоком из `chapter-02.md`**, где видно `कर्मण्येवाधिकारस्ते …` (то есть “слитое एवाधिकारस्ते” реально присутствует).
* Потом будет attachment **SPIR JSON**, где вы глазами увидите:

  * как Heritage разрезал/проанализировал,
  * какие токены и леммы получились,
  * есть ли `feats.heritage.analyses`.
* И тест будет падать **именно если**:

  * сервис не поднялся,
  * MCP/HTTP не отвечает,
  * тулза не называется `l0_analyze`,
  * или **лемма `अधिकार` не появилась** (то есть heritage не активен/не настроен/не тот корпус).

Протокол MCP по HTTP (initialize + `mcp-session-id` + `tools/call`) я заложил “как в FastMCP по Streamable HTTP”.

---

## Важная ремарка про ваши текущие артефакты лексикона

Если ваша цель — чтобы **`src/l0/artifacts/.../lexicon.json` реально содержал `अधिकार`**, то вам нужно, чтобы билд лексикона делался **не whitespace split**, а через `--use-analyze` и с `L0_BACKEND=heritage`, и чтобы `00_prepare_corpus.py` реально подхватывал `src/l0/data/raw/bg/vedabase.io/chapter-02.md` (сейчас он читает только `*.txt` и не рекурсивно).

BDD‑тест выше проверяет ключевое свойство (лемма в SPIR), после чего вы уже можете “докрутить” пайплайн артефактов так, чтобы лексикон это фиксировал.

---

Если хотите — следующим шагом могу дать **второй сценарий** в behave, который:

1. собирает мини‑`corpus.jsonl` из одной шлоки (TEXT 47),
2. запускает внутри контейнера `01_build_lexicon.py --use-analyze`,
3. и проверяет, что в сгенерённом `lexicon.json` в `lemma` реально есть `अधिकार` (и это тоже будет в Allure attachments).
