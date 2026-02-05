Ниже — **целостная “постановка под следующий спринт”**: как из вашего текущего репо сделать **L0 как продукт**, который:

1. можно использовать **как сейчас** (через `ask.py` и tool‑calling),
2. можно **переиспользовать** в других пайплайнах/репо (как lib и/или как сервис),
3. можно **заменять reasoning** частично/полностью (не путая это с “thinking trace”),
4. имеет **полную подготовку/обучение** на корпусах (Бхагавад‑гита + Шримад Бхагаватам) и **тестовые инференсы**.

Я буду говорить в вашем стиле: Docker Compose‑лаб, MCP‑tools, LangChain/LangGraph.

---

# A) Куда вы целитесь архитектурно

## A1) Текущая картина (как у вас сейчас)

* **ollama**: LLM
* **mcp_server**: общие инструменты (filesystem + now/add)
* **agent/ask.py**: универсальный агент через `create_agent`, который *может* вызвать tools

Это отлично для экспериментов, но:

* L0 вам нужен как **детерминированный узел** (а не “вдруг агент догадается”),
* L0 нужен как **переносимый компонент** (lib/сервис),
* reasoning нужно делать **заменяемым модулем**, а не думать, что `REASONING=true` решает задачу.

## A2) Целевая конструкция (минимальная, но правильная)

Добавляем **L0 как отдельную подсистему**:

1. **`src/l0/core`** — *чистая* Python‑библиотека (без LangChain/MCP/Docker)
   Функции: `analyze / keys / compress / validate / constraints`

   * SPIR schema + versioning.

2. **`src/l0/server`** — тонкая обёртка FastMCP, которая экспортирует `src/l0/core` как tools на `/mcp`
   (транспорт можно менять потом, ядро — нет).

3. **`agent`** получает два режима:

   * **ask‑режим** (как сейчас): универсальный агент + tools (в том числе L0 tools)
   * **flow‑режим** (явный граф): `pivot(L0) → plan → retrieve → compress(L0) → reconcile → answer`
     Здесь reasoning — заменяемые узлы.

---

# B) Что именно менять в вашем репо (минимально ломающим способом)

## B1) Новые директории в корне

Рекомендую добавить:

```
src/l0/core/
  pyproject.toml
  sprs_l0/
    __init__.py
    spir.py
    normalize.py
    keys.py
    compress.py
    validate.py
    constraints.py
    # дальше: segment.py, morph.py, compound.py, syntax.py, rank.py (по мере роста)
  scripts/
    00_prepare_corpus.py
    01_build_lexicon.py
    02_train_priors.py
    03_eval_smoke.py
    04_export_artifacts.py
  tests/
    unit/
    golden/
    bdd/
src/l0/server/
  Dockerfile
  server.py   # импортирует из sprs_l0
src/l0/data/
  raw/
  prepared/
src/l0/artifacts/
  current/   # симлинк/копия на версию
  v0.1.0/
agent/
  ask.py      # почти без изменений
  flow.py     # новый явный LangGraph граф
```

> Важно: `src/l0/data` и `src/l0/artifacts` держите отдельно от `workspace/`, чтобы не смешивать “лабораторные файлы” и “артефакты продукта”.

---

## B2) .env: добавляем переменные для L0 и для “заменяемого reasoning”

Добавьте в `.env` и `.env.example`:

```dotenv
# L0 MCP endpoint (new service)
L0_MCP_URL=http://l0:8000/mcp

# Which backend implements planning/reconcile in flow-mode
PLAN_BACKEND=llm          # llm | l0 | rules
RECONCILE_BACKEND=llm     # llm | rules

# Thinking trace is telemetry (not planner). Keep your existing REASONING too if you want.
THINKING_TRACE=true       # true/false (maps to ChatOllama(reasoning=...))
```

Можно оставить ваш `REASONING=true`, но я бы **явно развёл**:

* `THINKING_TRACE` — телеметрия,
* `PLAN_BACKEND/RECONCILE_BACKEND` — реальные модули reasoning.

---

## B3) docker-compose.yml: добавляем сервис l0

Добавьте рядом с `mcp`:

```yaml
  l0:
    build: ./src/l0/server
    environment:
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8000
      - L0_ARTIFACT_DIR=/artifacts/current
      - L0_DATA_DIR=/data
    ports:
      - "8001:8000"   # хост:8001 -> контейнер:8000 (чтобы не конфликтовать с mcp:8000)
    volumes:
      - ./src/l0/artifacts:/artifacts
      - ./src/l0/data:/data
```

И в `agent` добавьте env:

```yaml
  agent:
    environment:
      - L0_MCP_URL=${L0_MCP_URL}
      - PLAN_BACKEND=${PLAN_BACKEND}
      - RECONCILE_BACKEND=${RECONCILE_BACKEND}
      - THINKING_TRACE=${THINKING_TRACE}
```

---

## B4) agent/ask.py: подключаем второй MCP‑сервер (L0) и не ломаем ask‑режим

У вас сейчас:

```python
client = MultiServerMCPClient({"lab": {...}})
```

Станет:

```python
servers = {"lab": {"transport": "http", "url": mcp_url}}

l0_url = os.getenv("L0_MCP_URL", "").strip()
if l0_url:
    servers["l0"] = {"transport": "http", "url": l0_url}

client = MultiServerMCPClient(servers)
tools = await client.get_tools()
```

**Правило:** тулзы L0 должны быть префиксованы (`l0_analyze`, `l0_compress`…), чтобы не словить коллизии.

---

# C) Контракт L0 (как продукт) — чтобы “смысл не потерялся”

Чтобы L0 не превратился в “регекс токенайзер”, фиксируем минимальный **SPIR v0.1** и **capabilities**.

## C1) MCP tools, которые L0 обязан предоставить

Минимально:

1. `l0_analyze(text, input_format="auto", k_best=5, return_lattice=true) -> spir`
2. `l0_keys(query_spir, max_terms=12) -> {keywords, query, role_patterns?, lemma_terms?}`
3. `l0_compress(query_spir, passages, policy=..., max_chars=...) -> compact_passages`
4. `l0_validate(spir) -> {ok, errors, warnings, metrics}`
5. `l0_constraints(state_or_spir) -> {hard_mask?, soft_penalties?, explanations?}`

> Даже если `constraints` сначала “пустой”, он должен быть в контракте, иначе L0 не станет тем самым “нулевым слоем”.

## C2) SPIR v0.1: минимально “смысловой”, но реализуемый быстро

Обязательные поля:

* `normalized_text`
* `tokens[]`: `surface`, `lemma`, `pos?`, `feats{}`, `conf`
* `segments`: lattice (хотя бы список альтернативных разбиений)
* `meta.version` + `meta.artifacts_hash` + `meta.input_hash`
* `capabilities[]`: например `["normalize","segment_lattice","lemma","morph_stub"]`

И важная оговорка: **unknown лучше чем ложь**
если морфология не готова — пишите `feats={}` и `capabilities` честно.

---

# D) “Reasoning” как заменяемый модуль (и почему thinking trace — не он)

## D1) Вводим три интерфейса (концептуально)

* **L0**: `analyze / keys / compress / validate / constraints`
* **Planner**: `plan(query_spir) -> plan_json`
* **Reconciler**: `reconcile(query_spir, evidence_compact) -> facts_json`

И выбираем реализацию через env:

* `PLAN_BACKEND=llm` → план делает LLM (строгий JSON)
* `PLAN_BACKEND=l0` → план делает детерминированный модуль (keys+эвристика)
* `PLAN_BACKEND=rules` → полностью rules‑based

`THINKING_TRACE=true/false` влияет только на телеметрию (то, что у вас сейчас `REASONING=true`).

## D2) Зачем нужен agent/flow.py (явный граф)

Потому что `create_agent`:

* удобен,
* но скрывает шаги,
* и плохо поддаётся “замене одного узла reasoning”.

В `flow.py` вы получите:

* воспроизводимый пайплайн,
* трейс `PLAN/RETRIEVE/COMPRESS/RECONCILE/ANSWER`,
* и очень ясные точки замены.

---

# E) Постановка задачи “обучение/подготовка L0” на Бхагавад‑гите и Шримад Бхагаватам

Важно: L0 в зрелом виде будет в основном **символическим** (правила/лексикон/валидация), но “обучение” L0 вполне реально и полезно, просто это не “предобучение трансформера”, а:

* построение **лексикона и частотных приоров**,
* калибровка confidence,
* обучение мини‑ранжировщика для выбора разбора (опционально),
* обучение токенизатора (если надо),
* подготовка эталонных тестов.

## E1) Данные (вход)

В `src/l0/data/raw/` кладёте:

* `bhagavad_gita.txt`
* `srimad_bhagavatam.txt`

Формат: деванагари или IAST (главное — единообразие или явная маркировка).

**Требование:** сохранить “provenance” (откуда текст, какая лицензия/условия) в `src/l0/data/raw/manifest.json`.

## E2) Пайплайн подготовки (scripts/)

### Script 00 — Prepare corpus

**Вход:** raw тексты
**Выход:** `src/l0/data/prepared/corpus.jsonl`

Каждая запись:

* `doc`: `bg|sb`
* `ref`: глава/шлока (если есть) или индекс строки
* `text_deva` (канонический)
* `text_iast` (если возможно)
* `text_norm` (после L0 normalize)

### Script 01 — Build lexicon

**Цель:** собрать:

* частоты поверхностных форм,
* частоты лемм (пока proxy),
* частоты окончаний/суффиксов (эвристика),
* стоп‑список служебных элементов.

**Выход:** `src/l0/artifacts/v0.1.0/lexicon.json`, `freqs.json`

### Script 02 — Train priors / ranker (этап 1)

На старте делаем **приоры для ранжирования** без сложной ML:

* penalty за редкие разбиения,
* бонус за частотные леммы,
* penalty за слишком много UNK,
* бонус за согласование (когда появится морфология).

**Выход:** `priors.json`, `scoring_config.json`

### Script 03 — Smoke eval

Прогоняем `l0_analyze + l0_validate` на:

* N случайных шлок,
* N заранее подобранных “сложных” случаев.

Сохраняем:

* процент “валидных SPIR”,
* процент “ambiguous”,
* время на 1k строк.

**Выход:** `eval_smoke.json` + логи.

### Script 04 — Export artifacts

Складываем всё в версионируемую папку `src/l0/artifacts/v0.1.0/` и делаем `current/` ссылкой/копией.

---

## E3) (Опционально) “обучение” L0 v0.2: мини‑ранжировщик

Когда появятся:

* sandhi lattice,
* k‑best морфо‑анализы,
* хотя бы небольшой gold‑набор (200–500 примеров),

можно обучить tiny‑ranker:

* вход: признаки кандидата разбора (число токенов, частоты, согласование, нарушения правил)
* выход: score

Это даст реальный прирост качества “best parse” без тяжёлой LLM.

---

# F) Тестовые инференсы L0 (как часть продукта и как часть контура)

## F1) L0 “smoke inference” как команда (обязательный артефакт)

Добавьте CLI (в src/l0/core) или скрипт:

* `python -m sprs_l0.cli analyze --in src/l0/data/prepared/corpus.jsonl --out workspace/spir_samples.jsonl --limit 50`
* `python -m sprs_l0.cli validate --in workspace/spir_samples.jsonl`

Критерии:

* 100% SPIR проходит JSON Schema
* ≥X% записей без критических ошибок (порог вы зададите)
* детерминизм: повторный запуск даёт те же hash/выходы (при фиксированных artifacts)

## F2) Интеграционный “flow inference” (в графе)

В `agent/flow.py` вы делаете:

* `pivot(L0)` на query
* `plan` (по PLAN_BACKEND)
* `retrieve` (для лабораторки достаточно читать `workspace/kb/*.txt` через ваши MCP tools)
* `compress(L0)` (вызов `l0_compress`)
* `reconcile`
* `answer`

И стримите события.

---

# G) Разные случаи использования и “предварительная подготовка” под них

Ниже — матрица “use case → что подготовить заранее”.

## Use case 1 — как сейчас: ask.py + tool calling

**Цель:** “работает как сейчас, но L0 доступен как tool”

* Поднять `l0` сервис
* Подключить L0 в `MultiServerMCPClient`
* L0 может быть вызван моделью (не детерминированно)

**Подготовка:** минимальная (`src/l0/artifacts/current` может быть пустым на v0.1)

---

## Use case 2 — детерминированный пайплайн: flow.py

**Цель:** reproducible контур и наблюдаемость

* Граф узлов, где L0 вызывается явно
* Планнер/ре-консайлер можно менять через env

**Подготовка:**

* `src/l0/artifacts/current` (лексикон/priors)
* `src/l0/data/prepared` (корпус/индексация)

---

## Use case 3 — построение индекса для retrieval (RAG-lite)

**Цель:** быстро и точно вытаскивать нужные места из корпуса

* Предварительно батч‑анализ L0 на корпусе → сохранить `passage_spir`
* Индексировать:

  * BM25 по нормализованному тексту
  * vectors по embed (пока можно TF‑IDF; позже L1 embeddings)

**Подготовка:**

* батч‑прогон L0 по корпусу
* сохранение `doc_id/span → spir` маппинга

---

## Use case 4 — подготовка датасета для обучения L1

**Цель:** L1 учится на факторах L0

* Сгенерировать `spir_dataset.jsonl`
* Сохранить версии L0 artifacts

**Подготовка:**

* стабильный SPIR schema
* стабильная версия artifacts

---

## Use case 5 — constraints для генерации санскрита/JSON

**Цель:** уменьшать грамматические/структурные ошибки

* Реализовать `l0_constraints`
* Подключить в L1 decode или хотя бы в validate‑после‑генерации

**Подготовка:**

* хотя бы базовые hard checks + soft penalties

---

# H) Итоговая постановка задачи “под Codex‑агента” (целиком, 1 блок)

**Сделать L0 как продукт и встроить в текущий lab‑stack.**

1. Вынести L0 в `src/l0/core` (чистая библиотека) с SPIR schema + версиями + функциями `analyze/keys/compress/validate/constraints`.
2. Сделать `src/l0/server` (FastMCP) как тонкую обёртку над `src/l0/core`, поднять отдельным сервисом `l0` в docker‑compose, подключить в `agent/ask.py` как второй MCP‑сервер через `MultiServerMCPClient`.
3. Добавить `agent/flow.py` (явный LangGraph граф) с узлами `pivot(L0) → plan → retrieve → compress(L0) → reconcile → answer`, где планнер/ре-консайлер выбираются через `PLAN_BACKEND/RECONCILE_BACKEND`. Thinking trace (`THINKING_TRACE/REASONING`) оставить как телеметрию, не как модуль reasoning.
4. Реализовать пайплайн подготовки/“обучения” L0 на корпусах **Бхагавад‑гита + Шримад Бхагаватам**: `prepare_corpus → build_lexicon → train_priors → export_artifacts`. Все артефакты версионировать в `src/l0/artifacts/vX.Y.Z` и выставлять `current/`.
5. Добавить тестовые инференсы L0: `smoke` (batch analyze+validate на выборке), `golden` (фикстуры), `bdd` (Given/When/Then для поведения normalize/segment/kbest/validate), и интеграционный прогон flow‑графа со стримингом событий и сохранением артефактов.

---

Если хотите, я могу следующим сообщением **дать “скелет” `agent/flow.py`** под ваш стек (без лишних зависимостей), который:

* явно вызывает L0 tools,
* делает простой retrieval по `workspace/kb/`,
* стримит `PLAN / RETRIEVE / COMPRESS / RECONCILE / ANSWER`,
* и переключает planner/reconciler через env — ровно как вы запросили.
