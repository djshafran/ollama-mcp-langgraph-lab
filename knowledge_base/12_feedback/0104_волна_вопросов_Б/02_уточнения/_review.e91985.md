# Рецензия реализации SPIR v0.4 в репозитории djshafran/ollama-mcp-langgraph-lab относительно плана A5+A6+Full KAG Event+Deontic

## Executive summary

В репозитории на entity["company","GitHub","code hosting platform"] действительно реализован **SPIR v0.4 сквозным конвейером** (A0..A7) и обвязкой MCP/CLI/BDD: артефакты `syntax.paninian_edges`, `syntax.ud.basic_edges`, `syntax.ud.enhanced_edges`, `syntax.ud.empty_nodes`, `syntax.clauses`, `syntax.discourse_links`, `semantics.kag`, `provenance` формируются в одном вызове `analyze` и проверяются валидатором. Реализация **детерминированная** и хорошо подходит как “лабораторный baseline”.

Однако относительно предложенного вами плана **A5+A6+Full KAG (Event+Deontic)** имеются ключевые несоответствия:

- **SPIR v0.4 контракт** формально задан “функциями/валидацией” (процедурно), но не закреплён как строгие JSON Schema. Это повышает риск расползания контрактов между модулями и тестами.
- **UD basic (A5)** реализован как *проекция карáка→UD* (маппинг labels), а не как UD‑дерево, построенное head‑rules. Формальная валидность дерева сильная, но UD‑семантика и “интероперабельность UD” зависят от качества upstream карáка‑графа.
- **Enhanced UD (A6)** реализован как MVP‑эвристика, но **empty_nodes не участвуют в enhanced‑графе как узлы**, а CoNLL‑U export не соответствует требованиям UD/CoNLL‑U для эллипсиса (пустые узлы `i.1`, HEAD/DEPREL `_`, связи через DEPS). ([universaldependencies.org](https://universaldependencies.org/format.html))
- **Overrides применяются поздно**: `clauses/discourse` и `enhanced_ud` вычисляются до патчей и становятся потенциально несогласованными с обновлёнными `paninian_edges`/`ud.basic_edges`.
- **KAG (Event+Deontic)** существует, но пока не “Full”: один Event, деонтические нормы адресуются в один target_event, `clause_id` фиксируется в `"c1"`, отсутствует scoping норм по клаузам/аргументам.
- **Retrieval** оформлен как “архитектурная заготовка” (TF‑лайт + trigram‑Jaccard + RRF), что нормально для baseline, но не соответствует anticipated “BM25 + embeddings + cross‑encoder reranker” уровню.

У репозитория сильная база: явная provenance‑структура и тесты — это хорошо согласуется с практиками управляемого риска (entity["organization","National Institute of Standards and Technology","us standards agency"] AI RMF подчёркивает необходимость прозрачности, измеримости и контроля рисков на жизненном цикле AI‑систем). ([nist.gov](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10))

## Инвентаризация репозитория по требуемым файлам и артефактам

Ниже перечень проверенных модулей, соответствующих вашему чек‑листу (указаны реальные пути; фрагменты кода приведены выборочно). Поиск по репо через code‑search ограничен, поэтому верификация делалась прямым чтением файлов по путям.

| Требование | Файл | Статус | Краткое замечание |
|---|---|---|---|
| SPIR v0.4 | `src/l0/core/sprs_l0/spir.py` | есть | `SPIR_VERSION="0.4.0"`, но `spir_schema()` — скорее заглушка (не JSON Schema) |
| Validator v0.4 | `src/l0/core/sprs_l0/validate.py` | есть | сильная процедурная валидация деревьев, но нет schema‑валидации JSON |
| Контракты v0.4 | `src/l0/core/sprs_l0/contracts_v04.py` | есть | enum‑наборы типов/values; schema.json в артефактах не используется |
| UD basic | `src/l0/core/sprs_l0/ud.py` | есть | карáка→UD mapping + строгая tree‑валидация; экспорт CoNLL‑U минимальный |
| Enhanced UD | `src/l0/core/sprs_l0/eud.py` | есть | эвристики shared‑args + empty_nodes, но empty_nodes не включены в enhanced edges |
| Clause/discourse | `src/l0/core/sprs_l0/clause.py` | есть | сегментация по пунктуации/маркерам, discourse links между соседними клаузами |
| KAG full | `src/l0/core/sprs_l0/kag.py` | есть | минимальный Event+Deontic граф (single event) |
| Analyze pipeline | `src/l0/core/sprs_l0/analyze.py` | есть | A0..A7, но overrides стоят после clauses/eud |
| MCP server | `src/l0/server/server.py` | есть | реализованы tools: analyze/query_understand/retrieve/export/validate |
| Agent flow | `agent/flow.py` | есть | анализ → retrieval → LLM reconcile → answer |
| CLI | `src/l0/core/sprs_l0/cli.py` | есть | analyze/validate/export под v0.4 |
| Артефакты v0.4.0 | `src/l0/artifacts/v0.4.0/*` | частично “живые” | mapping/lexicon используются, head_rules.yaml и kag/schema.json — декларативные stubs |

Артефактный слой:
- `syntax/karaka_to_ud.json` соответствует заявленному mapping и используется загрузчиком mapping (это хорошо).  
- `syntax/head_rules.yaml` существует, но не участвует в построении UD дерева.  
- `kag/deontic_lexicon.json` реально используется, что позволяет расширять деонтические маркеры без правки кода.

## Контракты SPIR v0.4 и ID‑политика

### Контракты: “процедурная истина” вместо schema‑истины

В текущем виде контракт SPIR v0.4 фактически задаётся:
- конструктором `make_spir()` и “минимальным” `spir_schema()` (не формальным JSON Schema),
- плюс процедурными проверками `validate.py`.

Это нормально как быстрый релиз, но плохо машиночитаемо и сложно масштабируется на формальную совместимость (экспорт/интеграции/версионирование). Для “breaking v0.4” лучше закрепить:
- JSON Schema (draft 2020‑12) для всего SPIR,
- отдельные schema для `syntax.ud`, `syntax.clauses`, `semantics.kag`.

### ID‑политика: основная “техническая граница” между MVP и полноценным UD/EUD

Сейчас:
- `token_id`: int (0‑based по списку `tokens`).
- `ud.basic_edges`: `head`/`dep` — int|None.
- `ud.enhanced_edges`: `head`/`dep` — **только int|None** (валидатор отклоняет строки).
- `ud.empty_nodes`: ID вида `"E1"` (строка), но это “сайд‑лист”, не узел графа.

В entity["organization","Universal Dependencies","treebank annotation project"]/CoNLL‑U для эллипсиса описан другой механизм:
- empty nodes имеют ID вида `i.1`, `i.2`; HEAD/DEPREL у них пустые (`_`);
- связи с empty nodes выражаются через поле `DEPS` (enhanced dependencies), а не через basic HEAD/DEPREL. ([universaldependencies.org](https://universaldependencies.org/format.html))  
Рекомендации по enhanced syntax и роли empty nodes/ellipsis также вынесены отдельно. ([universaldependencies.org](https://universaldependencies.org/u/overview/enhanced-syntax.html))

Следовательно, текущая модель `empty_nodes` не соответствует UD‑контракту, а export `conllu_enhanced` не может считаться UD‑совместимым в части эллипсиса.

## A5 и A6: UD basic, Enhanced UD, clauses/discourse

### UD basic соответствует формальным инвариантам дерева

Сильная сторона реализации: строгий валидатор basic UD обеспечивает:
- 1 root,
- покрытие всех токенов,
- отсутствие циклов,
- достижимость.

Это прямо соответствует вашей цели “серийных валидируемых артефактов”.

При этом UD basic строится через `map_karaka_to_ud()` как **проекция** карáка‑графа. Плюсы: детерминизм и простота. Минусы: отсутствие независимого UD‑head policy и зависимости качества UD от “качества карáка”.

Для санскрита важно отдельно решать копулу/нулевую копулу и выбор головы; в UD именно лексический предикат обычно глава, а copula (`cop`) — зависимый элемент. ([universaldependencies.org](https://universaldependencies.org/naq/dep/cop.html))

### Enhanced UD: есть “слой”, но он не формализует EUD‑граф как требует CoNLL‑U

Сейчас:
- enhanced_edges — это фактически “копия basic + несколько эвристических добавок”,
- empty_nodes создаются, но не связаны и не экспортируются как строки `i.1` и не используются в DEPS.

Поскольку CoNLL‑U/UD строго задаёт, как представлять empty nodes и enhanced graph, корректная реализация A6 требует перестроить контракт `enhanced_edges` так, чтобы `head/dep` могли ссылаться на empty node ID (строка) и экспорт включал empty node строки. ([universaldependencies.org](https://universaldependencies.org/v2/conll-u.html))

### Clause/discourse: MVP корректен, но needs “definition of span”

Clause segmentation реализован детерминированно (по пунктуации/маркерам), discourse links — между соседними клаузами (coord/subord/… heuristics). Это соответствует “MVP‑ограниченному A6”.

Однако contract `token_span` трактуется как **inclusive** `[start,end]` (валидатор требует `end < token_count`). В документации контракта это стоит закрепить явно (или перейти на half‑open `[start,end)`), иначе внешние интеграции быстро получат off‑by‑one ошибки.

## A7: KAG Event+Deontic, provenance и query/retrieval

### KAG: Event+Deontic существует, но “Full KAG” не закрыт

Текущий KAG:
- создаёт один `Event` узел по root UD,
- создаёт `Entity` на каждый токен,
- вешает `ARG` связи по paninian edge dep‑токенам,
- выводит `Norm` узлы (deontic modal values: `obligation/prohibition/permission/right`) по лексикону маркеров (`mā/मा`, `adhikāra/अधिकार` и т.п.).

Это хороший “скелет”, но ключевые ограничения относительно “Full”:
- multi‑event (несколько событий/состояний),
- scoping норм (к какой клаузе/ивенту относится конкретное `mā`),
- корректная provenance‑привязка к `clause_id` (сейчас `clause_id` фиксирован),
- валидация диапазонов `token_ids` и существования `clause_id`.

Для стиха entity["book","Bhagavad Gītā","Hindu scripture"] 2.47 характерно несколько запретов через повторяющийся маркер `mā`, что требует scoping минимум на уровне clause spans; текст можно брать из GRETIL. ([gretil.sub.uni-goettingen.de](https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/2_epic/mbh/ext/bhg4c02u.htm))

### Связь с Heritage/Hyderabad

Морфология/сегментация санскрита обычно получают от Sanskrit Heritage (проект Inria), который специально ориентирован на sandhi splitting, морфологию и “analysis modes”. Это является устойчивым базисом для L0 слоя. ([sanskrit.inria.fr](https://sanskrit.inria.fr/manual.html))  
Constraint‑based parser (Hyderabad/UoH) концептуально выдаёт те самые paninian dependencies (карáки) и используется как синтактико‑семантический слой. ([sanskrit.uohyd.ac.in](https://sanskrit.uohyd.ac.in/faculty/amba/PUBLICATIONS/papers/constraint_parser_revised.pdf))

### Query/retrieve: архитектура есть, но качество “не production”

`query_understand` строит `kag_query` из токенов и модальностей, а `retrieve` реализует детерминированный hybrid‑like baseline. Для MVP — нормально, но в плане подразумевался production‑уровень hybrid retrieval. Здесь лучше ввести двухскоростную модель: “baseline deterministic” + “optional embeddings backend”.

Для рамок управляемости риска важно: provenance retrieval/answer (какие источники и почему) постепенно превращать в first‑class артефакт — это поддерживает NIST AI RMF идеологию управляемого “trustworthy AI” через прозрачность и контроль жизненного цикла. ([nist.gov](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10))

## Тесты, CI и воспроизводимость

В репозитории присутствуют:
- unit‑тесты (pytest) для UD basic, EUD heuristics, clause graph, KAG norms, provenance;
- BDD контур (behave + testcontainers + allure) с `hydra_mock`.

Запуск unit/BDD тестов в рамках этого отчёта физически не выполнен из‑за ограничений среды (недоступность стандартного клонирования/сетевых зависимостей). Тем не менее структура `pyproject.toml` явно содержит dev‑extras для BDD, и compose‑контур для интеграционного тестирования уже оформлен. Практический риск: CI workflow отсутствует (файл `.github/workflows/ci.yml` не найден), поэтому regressions могут не ловиться автоматически.

## Таблица несоответствий и приоритетные PR

### Несоответствия “план → реализация”

| Область | План | Реализация | Риск | Приоритет |
|---|---|---|---|---|
| Контракты | Формальная JSON schema | procedural validate + минимальная schema-заглушка | дрейф контрактов | P0 |
| ID‑policy EUD | empty nodes `i.1` + DEPS links | empty nodes `E1` “сбоку”, enhanced_edges только int | UD несовместимость | P0 |
| A6 EUD | shared args + empty nodes как узлы графа | shared args есть (эвристика), empty nodes не участвуют | не закрыт A6 | P0 |
| Overrides | до пересчёта downstream | применяются после clauses/eud | несогласованная SPIR | P0 |
| KAG Full | multi‑event + scope norms + clause_id | single‑event, `clause_id="c1"` | слабый planning | P0 |
| Retrieval | BM25+embeddings+rereank | baseline TF+trigram+RRF | качество ниже обещания | P1 |
| CI | unit+BDD в CI | отсутствует workflow | риск regressions | P1 |

### Список приоритетных PR (конкретные правки)

**PR‑1 (P0): UD‑совместимый enhanced UD и empty nodes**  
- Изменить контракт: `head/dep` в `enhanced_edges` должны быть `int | str`, где str соответствует `^\d+\.\d+$`.  
- `empty_nodes` должны иметь `id="i.1"` формат, `HEAD/DEPREL` пустые при экспорте, связи идут через DEPS. ([universaldependencies.org](https://universaldependencies.org/format.html))  
- Изменить exporter: печатать строки empty nodes и корректно сериализовать DEPS.

Пример JSON Schema для enhanced UD (как просили):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["enhanced_edges", "empty_nodes"],
  "properties": {
    "enhanced_edges": {
      "type": "array",
      "items": { "$ref": "#/$defs/edge" }
    },
    "empty_nodes": {
      "type": "array",
      "items": { "$ref": "#/$defs/emptyNode" }
    }
  },
  "$defs": {
    "tokenId": { "type": "integer", "minimum": 0 },
    "emptyId": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+$" },
    "nodeRef": { "oneOf": [ { "$ref": "#/$defs/tokenId" }, { "$ref": "#/$defs/emptyId" } ] },
    "edge": {
      "type": "object",
      "required": ["head", "dep", "rel"],
      "properties": {
        "head": { "oneOf": [ { "$ref": "#/$defs/nodeRef" }, { "type": "null" } ] },
        "dep": { "$ref": "#/$defs/nodeRef" },
        "rel": { "type": "string" },
        "conf": { "type": "number", "minimum": 0, "maximum": 1 }
      }
    },
    "emptyNode": {
      "type": "object",
      "required": ["id", "anchor_token_id"],
      "properties": {
        "id": { "$ref": "#/$defs/emptyId" },
        "anchor_token_id": { "$ref": "#/$defs/tokenId" }
      }
    }
  }
}
```

**PR‑2 (P0): Переместить overrides и пересчитывать clauses/eud/kag после patch**  
- В `analyze.py` переставить порядок так, чтобы overrides применялись **до** сборки `clauses` и `enhanced_ud` (или пересчитывать эти слои после overrides). Иначе SPIR будет внутренне противоречив.

**PR‑3 (P0): KAG Full MVP**  
Минимум, не требующий обучения моделей:
- создавать Event по каждому `clause.root_token_id`;
- привязывать deontic norms к event по span маркера `mā` (по клаузам);
- provenance: валидировать `token_ids` диапазоны и реальные `clause_id`.  
Текстовые маркеры деонтики для санскрита (включая `mā`) хорошо извлекаются из морфологии/частиц, что согласуется с идеей Sanskrit Heritage + Hyderabad parser как L0 слоя. ([sanskrit.inria.fr](https://sanskrit.inria.fr/manual.html))  

Пример JSON Schema узла KAG (как просили):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["id", "type", "provenance"],
  "properties": {
    "id": { "type": "string" },
    "type": { "type": "string", "enum": ["Event", "Entity", "Norm", "State", "Source"] },
    "label": { "type": "string" },
    "data": { "type": "object" },
    "provenance": {
      "type": "object",
      "required": ["token_ids", "source_ref"],
      "properties": {
        "token_ids": { "type": "array", "items": { "type": "integer", "minimum": 0 } },
        "clause_id": { "type": ["string", "null"] },
        "source_ref": { "type": "string" }
      }
    }
  }
}
```

**PR‑4 (P1): head_rules как реально применяемый механизм или убрать из релиза**  
Сейчас `head_rules.yaml` есть, но не участвует. Либо:
- реально внедрить режим `ud_mode=head_rules`, либо
- честно убрать/отложить, чтобы артефакт не вводил в заблуждение.

Для head policy важно учитывать UD подход к копуле/нулевой копуле. ([universaldependencies.org](https://universaldependencies.org/naq/dep/cop.html))

**PR‑5 (P1): CI**  
Добавить GitHub Actions workflow для unit‑тестов (и опционально BDD на self‑hosted runner). Это критично для “big release”.

## Минимальный план релиза

1) Зафиксировать контракт SPIR v0.4 как JSON schema (или хотя бы schema‑подмодули для UD/EUD и KAG).  
2) Исправить overrides ordering (и последующий пересчёт слоёв).  
3) Сделать UD‑совместимый EUD (empty nodes + DEPS) и обновить тесты. ([universaldependencies.org](https://universaldependencies.org/format.html))  
4) Прокачать KAG в сторону “Full MVP” (multi‑event + scope deontic).  
5) Включить хотя бы unit CI.  
6) Прогнать `pytest` и BDD сценарии по BhG 2.47, сверяя текст с эталоном GRETIL. ([gretil.sub.uni-goettingen.de](https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/2_epic/mbh/ext/bhg4c02u.htm))