# Компоненты для карáка-графа и UD-зависимостей

## Синтаксический парсер (Hyderabad/Samsaadhanii)

Первым делом нужен **работающий синтаксический парсер**, который будет определять паниниевские зависимости (карáка-отношения) между словами[[1]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L26-L34). В нашем проекте уже интегрирован **constraint-парсер Университета Хайдарабада (Samsaadhanii)** – он способен строить зависимые связи по Панини для санскритского текста. В репозитории предусмотрены все скрипты для локального запуска этого парсера: например, scripts/hyderabad/00_fetch.sh и 01_build.sh автоматически клонируют исходники Samsaadhanii (репозиторий samsaadhanii/scl) и необходимые компоненты, а затем собирают их[[2]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/00_fetch.sh#L10-L18)[[3]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/01_build.sh#L38-L42). Также есть скрипт для сборки Docker-образа парсера[[4]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/02_docker.sh#L12-L18) – это позволяет поднять его в контейнере при необходимости.

После установки **парсер Samsaadhanii** можно вызывать офлайн через CGI-интерфейс. Проект настраивает Apache с CGI-модулями, поэтому парсер доступен локально по URL вида http://localhost/cgi-bin/SKT/…. Например, можно отправить GET-запрос на локальный CGI-скрипт парсера с параметрами (текст, кодировка, формат) и получить разбор в формате JSON. В документации Samsaadhanii приведён пример: запрос к скрипту anusaaraka.cgi с параметрами parse=FULL, mode=json, text=<предложение> возвращает полный разбор предложения в JSON-формате[[5]](https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf#:~:text=Usage%3A%20https%3A%2F%2Fsanskrit.uohyd.ac.in%2Fcgi,the%20input%20is%20already%20split)[[6]](https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf#:~:text=%E2%80%A2%20compound_analysis%3DYES%2FNO%20%E2%80%A2%20mode%3Ajson%20G,%E2%80%A2%20outencoding%3A%20IAST%2FDEV%20%E2%80%A2%20mode%3Ajson). Таким образом, наше приложение L0 может либо делать HTTP-запрос к локальному CGI-парсеру, либо (в перспективе) вызвать парсер через CLI, передав ему строку и получив разбор. (На время разработки у нас также реализован простой **rule-based** режим – при переключении SYNTAX_BACKEND на "rules" – который связывает слова примитивно для отладки, но полноценный анализ требует Samsaadhanii[[7]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/syntax.py#L16-L21).) Парсер должен быть настроен на нужную транслитерацию ввода (например, WX или IAST) и уметь работать с несегментированным текстом (для этого мы можем сначала применять сегментацию Heritage, см. ниже).

## Схема зависимостей и карáка-роли

Нужно определить **формат выходных зависимостей** и перечень допустимых ролей. Мы используем следующую структуру: каждая зависимость представляется триплетом { head, dep, role }, где **head** – индекс головного токена, **dep** – индекс зависимого токена, а **role** – название грамматической роли этой зависимости[[8]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/artifacts/v0.3.0/spir_corpus.jsonl#L1-L3). Например, для корневого слова указывается head: null и role: "root", а для зависимых – индекс их главы и конкретная карáка-роль.

**Список ролей карáка** соответствует классической паниниевской грамматике: **kartṛ** (картṛ, деятель), **karman** (карман, объект действия), **karaṇa** (каран̣а, орудие/инструмент), **saṃpradāna** (сампрадāна, адресат/получатель), **apādāna** (апāдāна, источник/отправная точка) и **adhikaraṇa** (адхикар̣ан̣а, местоположение) и т.д.[[9]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L8-L10). В зависимости от предложения, каждому зависимому слову будет присвоена одна из этих ролей. Важный момент – определить, **какой токен считать** **root**: как правило, корневым делается финитный глагол главного предложения. В нашем текущем прототипе (режим “rules”) по умолчанию корнем берётся первый токен предложения[[7]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/syntax.py#L16-L21), но при полноценном разборе (Hyderabad) корневой узел будет определяться грамматически (главный предикат).

Сейчас в артефактах L0 **структура для зависимостей уже заложена** – в выходном JSON (SPIR) есть массив dependencies с полями head, dep, role для каждого отношения[[8]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/artifacts/v0.3.0/spir_corpus.jsonl#L1-L3). Пока что при заглушечном разборе все роли помечаются общим dep (заглушка), кроме корня, но проверка BDD уже ожидает наличие осмысленных ролей[[10]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/tests/bdd/features/bg_2_47.feature#L12-L15). Далее, по мере интеграции парсера, эти поля будут заполняться реальными карáка-ролями. Формат хранения (head/dep/role) выбран с расчётом на последующее удобное преобразование в дерево зависимостей UD.

## Морфологический анализ для правил

Для построения зависимостей по правилам необходима **морфологическая информация** о каждом слове: падеж, число, род для имён; лицо, время/наклонение (lakāra), переходность для глаголов и т.д.[[11]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L8-L11). Эти сведения позволяют применять правила согласования и узнавать, например, чем является аргумент глагола (по падежу можно угадать карáку). В нашем проекте интегрирован **морфологический анализатор Sanskrit Heritage Engine** (разработка Ж.Ю. Юэ, Inria) – он выполняет сегментацию слов (падаччхеда), разбор сандхи и выдаёт все возможные морфологические разборы[[1]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L26-L34). Репозиторий содержит скрипты для локальной сборки Heritage (клонируются проекты Heritage_Resources, Heritage_Platform и т.д., а затем компилируются OCaml-модули)[[12]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/heritage/00_fetch.sh#L34-L40)[[13]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/heritage/01_build.sh#L50-L59). При анализе L0 мы вызываем Heritage, чтобы получить для каждого токена лемму и грамматические признаки.

В результате в структуре SPIR у каждого токена заполняются поля **lemma** (основа) и **feats** с подробностями. Сейчас эти данные включают информацию Heritage: например, идентификатор решения и список возможных анализов слова[[14]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/analyze.py#L44-L53)[[15]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/analyze.py#L74-L82). BDD-тест подтверждает, что после анализа **каждый токен содержит лемму** и присутствуют **морфологические детали Heritage**[[16]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/tests/bdd/features/bg_2_47.feature#L3-L8). В дальнейшем можно выделить из этих данных нужные признаки (вибхакти, лексическую категорию и пр.) и использовать их для применения правил карáк, если работаем в rule-based режиме. Таким образом, морфологический “ступень” обеспечивает необходимые атрибуты для связей: например, показывает, что слово в номинативе единственного числа мужского рода likely будет картṛ при наличии связанного глагола, слово в винительном – вероятный karman и т.д.

## Маппинг карáк-ролей на отношения UD

Необходимо явно сопоставить каждую карáк-роль с соответствующим отношением в схемe **Universal Dependencies (UD)**[[17]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L10-L11). Это нужно, чтобы по полученному карáка-графу строить стандартное UD-дерево для совместимости с другими языками и корпусами[[18]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L51-L54). Ниже приведена таблица основных соответствий ролей Панини и этикеток UD:

·       **kartṛ** (агент) → **nsubj** (номинативный подлежащий)

·       **karman** (пациенс/объект) → **obj** (прямое дополнение)

·       **karaṇa** (орудие) → **obl:inst** (обстоятельство со знач. инструмента)

·       **saṃpradāna** (адресат) → **iobj** (косвенное дополнение)

·       **apādāna** (источник) → **obl:abl** (обстоятельство исходной точки/аблатива)

·       **adhikaraṇa** (место) → **obl:loc** (обстоятельство места/локатива)

Помимо этих основных ролей, могут быть дополнительные соглашения. Например, обращение (вокатив) в UD отмечается отдельной меткой **vocative** – в паниниевской системе это не карáка, но мы должны обработать такие случаи отдельно. Также агент в пассивных конструкциях (картаṛ в форме инструменталя) в UD помечается как **obl:agent** (обстоятельство-агент) вместо стандартного nsubj. **Частицы** и другие служебные слова нужно маппить на соответствующие отношения UD (например, तु – как дискурсивный маркер discourse, частица इति – как quoted или disp:quote в некоторых схемах и т.п.). Эти правила маппинга выйдут за рамки простого соответствия карáка-ролей, но их тоже надо прописать.

Важно, что мы **сохраняем обе разметки параллельно**: система сможет выдавать и паниниевские карáка-роли, и их UD-аналоги для каждого зависимого[[17]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L10-L11). В структуре данных можно, к примеру, хранить два поля роли – одно для карáки, другое для UD. Либо сразу в значении role использовать комбинированный тег (например, kartṛ/nsubj). Планируется экспортировать результаты в формате UD (например, CoNLL-U), чтобы их можно было проверять существующими UD-деревьями и использовать в многоязычном сравнении. Таким образом, **карáка-граф однозначно переводится в UD-дерево** – это создаёт мост между санскритом и другими языками без потери семантики ролей[[19]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L20-L21).

## Эталонные примеры (golden set)

Наконец, необходимо подготовить несколько **эталонных примеров** – предложений с вручную размеченными карáка-графами и UD-зависимостями, чтобы проверить качество работы парсера и правил. Такие _golden examples_ помогут убедиться, что все компоненты собраны правильно. Приведём парочку примеров разметки:

- **रामः फलम् खादति** _(rāmaḥ phalam khādati – «Рама ест фрукт»)_. Здесь रामः (Rāmaḥ, ном.) – роль **kartṛ** (агент) → в UD **nsubj**, फलम् (phalam, вин.) – роль **karman** (прямой объект) → UD **obj**, а глагол खादति («ест») является корнем, помеченным как **root**. В карáка-графе это выглядит: картṛ(रामः ← खादति) и карман(फलम् ← खादति), что в UD-дереве соответствует отношениям nsubj(खादति, रामः) и obj(खादति, फलम्).
- **रामः सीतायै पुष्पं ददाति** _(rāmaḥ sītāyai puṣpam dadāti – «Рама даёт Сите цветок»)_. Здесь रामः – **kartṛ** → **nsubj** (Рама – подлежащее-агент), पुष्पं (puṣpam, вин.) – **karman** → **obj** (цветок как прямое дополнение), सीतायै (sītāyai, дат.) – **saṃpradāna** → **iobj** (Сите как косвенное дополнение), а глагол ददाति («даёт») – **root**. Проверяем: карáка-граф содержит связи картṛ(रामः ← ददाति), карман(पुष्पं ← ददाति), संप्रदान(सीतायै ← ददाति), что соответствует UD-отношениям nsubj(ददाति, रामः), obj(ददाति, पुष्पं) и iobj(ददाति, सीतायै).

Эти примеры могут служить “золотым стандартом” для отладки: запустив наш L0-пайплайн на них, мы ожидаем получить те же карáка-роли и UD-метки на выходе. Если какие-то роли или зависимости определены неверно, правила нужно скорректировать или убедиться в правильной работе парсера. Таким образом, собрав все перечисленные компоненты – **синтаксический парсер**, **схему зависимостей с карáка-ролями**, **морфологическую поддержку** и **таблицу маппинга в UD**, плюс проверив их на эталонных примерах – мы получим полностью работающую систему, строящую карáка-граф и эквивалентные ему UD-зависимости для санскрита.

**Источники:**  
- Интеграция парсера Hyderabad (Samsaadhanii) и Heritage в проекте[[1]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L26-L34)[[16]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/tests/bdd/features/bg_2_47.feature#L3-L8)  
- Формат и роли карáка-графа, соответствие UD[[8]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/artifacts/v0.3.0/spir_corpus.jsonl#L1-L3)[[11]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L8-L11)  
- План маппинга карáк → UD в документации проекта[[17]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L10-L11)[[18]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L51-L54)

---

[[1]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L26-L34) [[9]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L8-L10) [[11]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L8-L11) [[17]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L10-L11) [[18]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L51-L54) [[19]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md#L20-L21) _base_idea.md

[https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/knowledge_base/01_formalization/_base_idea.md)

[[2]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/00_fetch.sh#L10-L18) 00_fetch.sh

[https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/00_fetch.sh](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/00_fetch.sh)

[[3]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/01_build.sh#L38-L42) 01_build.sh

[https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/01_build.sh](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/01_build.sh)

[[4]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/02_docker.sh#L12-L18) 02_docker.sh

[https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/02_docker.sh](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/hyderabad/02_docker.sh)

[[5]](https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf#:~:text=Usage%3A%20https%3A%2F%2Fsanskrit.uohyd.ac.in%2Fcgi,the%20input%20is%20already%20split) [[6]](https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf#:~:text=%E2%80%A2%20compound_analysis%3DYES%2FNO%20%E2%80%A2%20mode%3Ajson%20G,%E2%80%A2%20outencoding%3A%20IAST%2FDEV%20%E2%80%A2%20mode%3Ajson) API_DOC

[https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf](https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf)

[[7]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/syntax.py#L16-L21) syntax.py

[https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/syntax.py](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/syntax.py)

[[8]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/artifacts/v0.3.0/spir_corpus.jsonl#L1-L3) spir_corpus.jsonl

[https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/artifacts/v0.3.0/spir_corpus.jsonl](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/artifacts/v0.3.0/spir_corpus.jsonl)

[[10]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/tests/bdd/features/bg_2_47.feature#L12-L15) [[16]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/tests/bdd/features/bg_2_47.feature#L3-L8) bg_2_47.feature

[https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/tests/bdd/features/bg_2_47.feature](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/tests/bdd/features/bg_2_47.feature)

[[12]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/heritage/00_fetch.sh#L34-L40) 00_fetch.sh

[https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/heritage/00_fetch.sh](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/heritage/00_fetch.sh)

[[13]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/heritage/01_build.sh#L50-L59) 01_build.sh

[https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/heritage/01_build.sh](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/scripts/heritage/01_build.sh)

[[14]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/analyze.py#L44-L53) [[15]](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/analyze.py#L74-L82) analyze.py

[https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/analyze.py](https://github.com/djshafran/ollama-mcp-langgraph-lab/blob/160cc236451c07ef0bd0a2515d2b3d0cb1f1cca3/src/l0/core/sprs_l0/analyze.py)
