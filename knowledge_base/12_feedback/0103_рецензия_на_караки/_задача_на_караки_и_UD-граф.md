Ниже — **готовая постановка задачи (одним блоком) для OpenAI Codex-агента**, чтобы он в репозитории `ollama-mcp-langgraph-lab` **реализовал “управление” карáка‑графом и UD‑зависимостями** (генерация/маппинг/валидация/переключение бэкендов/оверайды) + **автотесты behave+allure с testcontainers**.

Скопируй целиком и отдавай Codex‑агенту.

---

```markdown
# ЗАДАЧА ДЛЯ CODEX: L0 — карáка‑граф + UD‑зависимости (управление, бэкенды, тесты)

## Контекст
Репозиторий: `ollama-mcp-langgraph-lab`.

В проекте уже есть L0-анализ (морфология/сегментация), BDD-сценарий `tests/bdd/features/bg_2_47.feature`, и артефакты `src/l0/artifacts/v0.3.0` (семантика/лингвистика в json/jsonl).
Также есть каркас под Hyderabad/Samsaadhanii в `scripts/hyderabad/*` (fetch/build/docker), и задача — довести до реально управляемого синтаксического слоя: карáка‑граф + UD.

## Цель (что в итоге должно уметь)
1) L0 должен уметь **строить карáка‑граф** зависимостей (Paninian roles) для предложения.
2) L0 должен уметь **строить UD‑зависимости** (Universal Dependencies) через явный маппинг карáка → UD.
3) Должна быть **возможность управления**:
   - переключать синтаксический бэкенд: `none | rules | hyderabad`
   - включать/выключать построение UD (например, `return_ud=true/false`)
   - подменять/расширять таблицу маппинга карáка→UD через файл артефакта
   - применять *overrides/patch* к графу (для “golden” корректировок по конкретным ref/doc/хэшу)
4) Всё должно быть доступно:
   - из Python API L0 (core)
   - из CLI
   - из L0 MCP-сервиса (tool calling), чтобы BDD ходил туда по HTTP
5) Должны быть автотесты:
   - unit: правила и маппинг
   - bdd: behave + allure
   - testcontainers: поднимать контейнеры (L0 сервис + mock hyderabad) и гонять BDD
6) Не сломать существующие сценарии, а расширить так, чтобы `bg_2_47.feature` доказывал наличие ролей + UD.

## Нефункциональные требования
- Детерминированность: одинаковый вход + одинаковые артефакты → одинаковый выход (граф).
- Обратная совместимость: текущий формат SPIR/вывода не должен “падать”; новые поля добавляются расширением.
- Если Hyderabad недоступен — аккуратный fallback на rules (с метаданными о fallback).

---

# A) Данные и контракт (SPIR/Syntax)

## A1) Формат карáка‑графа (в SPIR)
Добавить в SPIR объект `syntax` (или поля верхнего уровня, если уже так принято в коде), где:
- `syntax.backend`: `"hyderabad" | "rules" | "none"`
- `syntax.karaka`: список рёбер:
  - `head`: int | null        (null = root)
  - `dep`: int                (индекс токена)
  - `role`: str               (например: "root", "kartṛ", "karman", "karaṇa", "saṃpradāna", "apādāna", "adhikaraṇa", "sambandha", "vocative", "dep")
  - `conf`: float?            (опционально)
- `syntax.ud`: список рёбер UD:
  - `head`: int | null
  - `dep`: int
  - `rel`: str                (например: "root", "nsubj", "obj", "obl:loc", "obl:inst", "obl:abl", "iobj", "nmod", "nmod:poss", "dep", "vocative")
  - `conf`: float?            (опционально)
- `syntax.meta`: объект для диагностики:
  - `mapping_version`
  - `overrides_applied` (bool)
  - `errors` / `warnings` (списки строк)

Важно: индексация `head/dep` должна соответствовать `spir.tokens` (0-based).

## A2) Валидация
Расширить валидатор SPIR:
- Ровно 1 root в `karaka` и `ud`.
- Каждый токен должен иметь ровно 1 входящее ребро (как dep), кроме root.
- Нет циклов (минимальная проверка достижимости).
- Если `backend=none` — списки могут быть пустыми.

---

# B) Реализация: модули и функции

## B1) Найти текущие места в коде
Codex должен:
- найти текущую реализацию анализа L0 (где собирается SPIR)
- найти текущий формат SPIR/schema/validate
- найти MCP server (l0 tool endpoint)
- найти существующие BDD step definitions и как они вызывают L0

Дальше — внедрять новые функции, не дублируя второй “L0”.

## B2) Внутренний синтаксис rules (MVP)
Реализовать rule-based синтаксис, который использует морфологию из токенов (если есть):
- выбрать root:
  - если есть финитный глагол → он root
  - иначе “главное имя/сущ.” → root (для именных предложений)
- роли по падежам (если признаки доступны):
  - NOM → kartṛ
  - ACC → karman
  - INS → karaṇa
  - DAT → saṃpradāna
  - ABL → apādāna
  - LOC → adhikaraṇa
  - GEN → sambandha (или nmod:poss на UD-стороне)
- если морфологии нет (simple backend) → fallback: root=0, остальные dep

Должна быть функция:
- `build_karaka_rules(tokens, text, ...) -> karaka_edges, meta`

## B3) Бэкенд Hyderabad/Samsaadhanii
Добавить backend-адаптер, который умеет:
- HTTP-mode: `HYD_PARSER_URL` задан → POST/GET, получить JSON (или текст) и распарсить
- CLI-mode: если есть локальный бинарь/скрипт → вызвать subprocess
- привести результат к нашему `karaka_edges` (0-based по токенам)
- если маппинг по токенам невозможен (разный токенайзер) — делаем “best-effort”:
  - сначала match по surface (точное совпадение)
  - если не совпало — по lemma
  - иначе — пропускаем ребро с предупреждением в meta

Функция:
- `parse_karaka_hyderabad(text, tokens) -> karaka_edges, meta`

Примечание: тесты НЕ должны требовать реального Hyderabad-парсера. Для CI/локального прогна поднимем mock-контейнер.

## B4) Маппинг карáка → UD
Добавить явную таблицу (по умолчанию):
- kartṛ → nsubj
- karman → obj
- karaṇa → obl:inst
- adhikaraṇa → obl:loc
- apādāna → obl:abl
- saṃpradāna → iobj
- sambandha → nmod (или nmod:poss если GEN/poss)
- vocative → vocative
- dep → dep
- root → root

Сделать:
- файл артефакта маппинга, например:
  - `src/l0/artifacts/v0.3.0/syntax/karaka_to_ud.json`
- env override:
  - `KARAKA_UD_MAP_PATH` (если задан — читаем оттуда)
- версионирование:
  - `mapping_version` берём из артефакта (поле `version`) или из пути

Функция:
- `map_karaka_to_ud(karaka_edges, tokens, mapping) -> ud_edges, meta`

## B5) Overrides / patch управления графом
Нужно дать способ “управлять” графом для конкретных кейсов (golden):
- формат overrides: JSONL, каждая строка:
  - ключ (одно из): `input_hash` ИЛИ `{doc, ref}` (что реально есть в корпусе)
  - `karaka_patch`: операции:
    - `replace_all`: [edges...]
    - или `remove`: [...]
    - `add`: [...]
  - `ud_patch` (аналогично) — можно не задавать, если UD пересчитается автоматически после karaka override
- файл overrides в артефактах:
  - `src/l0/artifacts/v0.3.0/syntax/overrides.jsonl`
- env:
  - `SYNTAX_OVERRIDES_PATH`

Поведение:
- если найден override — применить, отметить `overrides_applied=true`
- если override задаёт только karaka — пересчитать UD после override
- если override задаёт UD тоже — использовать его (и валидировать)

Функции:
- `load_overrides(path) -> index`
- `apply_overrides(spir, overrides_index) -> spir`

---

# C) Встраивание в L0 analyze / MCP / CLI

## C1) L0 analyze
Расширить `analyze(...)` (или эквивалентную точку) так, чтобы:
- читался `SYNTAX_BACKEND` (none|rules|hyderabad), но также можно переопределить параметром функции/тулзы
- строился karaka_graph согласно backend
- строился ud_graph через mapping
- применялись overrides (если настроены)
- добавлялись capabilities: `"karaka_graph"`, `"ud_dependencies"` при наличии

Важно: при ошибке Hyderabad:
- fallback на rules
- meta должен содержать `fallback_from: "hyderabad"` и `error`

## C2) MCP tools
Если у вас уже есть tool `l0_analyze` — расширить его параметры (не ломая старые):
- `syntax_backend: optional[str]`
- `return_ud: bool = true`
- `return_syntax: bool = true`
и включить в ответ SPIR `syntax`.

(Если MCP-слой строгий, можно добавить отдельный tool `l0_syntax(...)`, но предпочтение — через `l0_analyze`.)

## C3) CLI
Добавить/расширить CLI команды:
- `sprs-l0 analyze --syntax-backend rules|hyderabad|none --ud/--no-ud`
- `sprs-l0 export-conllu --in spir.jsonl --out out.conllu` (опционально, но очень полезно)
- `sprs-l0 validate` должен проверять новые поля

---

# D) Автотесты: unit + behave/allure + testcontainers

## D1) Unit-тесты
Добавить unit тесты (pytest):
1) `test_karaka_rules_simple_sentence`
   - вход: "रामः वनं गच्छति" (или другой простой пример)
   - ожидания:
     - есть root
     - есть kartṛ/karman
2) `test_karaka_to_ud_mapping`
   - на заданном karaka_edges проверить UD rel
3) `test_validate_syntax_tree`
   - циклы/двойной root → ok False

## D2) BDD: расширить существующий `bg_2_47.feature`
Доработать сценарий так, чтобы он проверял:
- `syntax.karaka` присутствует
- в karaka есть хотя бы один role из {adhikaraṇa, kartṛ, karman} (для БГ 2.47 ожидаем как минимум adhikaraṇa для "कर्मणि")
- `syntax.ud` присутствует
- есть хотя бы один `rel` = "obl:loc" (для "कर्मणि")

Важно: не требовать 100% точной структуры от Hyderabad, чтобы тест был устойчив.
Достаточно проверок "ключевые роли присутствуют".

Также добавить отдельную feature, например `tests/bdd/features/simple_karaka_ud.feature` для простого предложения.

## D3) Testcontainers (обязательно)
Нужно сделать так, чтобы `behave` запускал контейнеры:
- L0 сервис (из Dockerfile/compose репозитория)
- mock-hyderabad сервис (контейнер на python:3.11-slim, который отдаёт предсказуемый JSON с карaka для 1–2 тестовых фраз)

Рекомендованный путь:
- создать `tests/compose/docker-compose.test.yml` с сервисами `l0` и `hydra_mock`
- в `tests/bdd/environment.py` использовать `testcontainers.compose.DockerCompose`:
  - поднять compose перед тестами
  - дождаться health/готовности
  - пробросить URL L0 MCP в steps (через env/context)
- `hydra_mock` должен слушать порт и иметь endpoint, который L0 backend вызывает (например `/parse`)

BDD steps должны вызывать L0 через HTTP/MCP так же, как в проекте принято сейчас.
Если сейчас steps вызывают Python напрямую — переключить их на HTTP/MCP (чтобы тестировал именно сервис/контейнер).

## D4) Allure
- подключить `allure-behave`
- сделать команду/скрипт:
  - `behave -f allure_behave.formatter:AllureFormatter -o allure-results`
- убедиться, что в репо есть `allure-results/` в .gitignore, и в CI/локально можно получить отчёт

---

# E) Документация
Обновить README / _base_idea.md:
- описать `SYNTAX_BACKEND`, `HYD_PARSER_URL`, `KARAKA_UD_MAP_PATH`, `SYNTAX_OVERRIDES_PATH`
- описать формат `syntax.karaka` и `syntax.ud`
- примеры запуска CLI и BDD

---

# F) Acceptance Criteria (что считается готовым)
1) `pytest` проходит.
2) `behave` проходит и создаёт `allure-results`.
3) BDD по `bg_2_47.feature` подтверждает:
   - в SPIR есть karaka roles
   - в SPIR есть UD rel (минимум `obl:loc` для BG 2.47)
4) При `SYNTAX_BACKEND=hyderabad` и доступном mock-сервисе L0 реально ходит в него (проверить в мета/логах/ответе).
5) При недоступном Hyderabad L0 падает НЕ должен: fallback на rules + meta.fallback_from присутствует.
6) Маппинг и overrides работают и документированы.

---

# G) Инструкции Codex
1) Сделай инвентаризацию текущих файлов/модулей: где L0 core, где MCP server, где tests.
2) Реализуй пункты A–F, минимально ломая структуру.
3) Не добавляй тяжёлые зависимости, если не требуется. Используй уже принятый стек.
4) Все изменения — с тестами и понятными коммитами/PR-описанием.
```

---

Если хочешь — я могу дополнительно сделать **2 мини-шаблона** (прямо готовые файлы) для Codex в стиле “вставь и адаптируй”:

1. `tests/compose/docker-compose.test.yml` (l0 + hydra_mock)
2. `tests/fixtures/hydra_mock/app.py` (микро-сервер, отдающий карáка JSON для пары фраз)

Но постановка выше уже достаточна, чтобы Codex отработал задачу end-to-end.
