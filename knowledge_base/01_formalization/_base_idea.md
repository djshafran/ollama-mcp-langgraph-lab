Классная идея — **сделать санскрит «нулевым слоем»** и строить поверх него интероперабельность. Ниже — рабочий чертёж такой системы: где именно опереться на санскритскую грамматику (Панини), какие корпуса/инструменты взять, как «прошить» символические правила в нейросетевую модель и как связать другие языки поверх.

> ⚠️ Сначала важная поправка. **Большие языковые модели не строятся на цепях Маркова.** Они обучаются как *авторегрессионные трансформеры* (Transformer) с вниманием и длинной памятью, а не как конечной памяти n‑граммные цепочки. Но цель у них действительно «следующий токен», что позволяет совместить их с грамматическими ограничениями как с *приором*. ([arXiv][1])

---

## Цель и принцип

* **Нулевой слой (L0)** — *символический* компонент: морфология/сандхи/самасы + зависимости в терминах карáк (kartṛ, karma, karaṇa и т.п.) по Панини. Он даёт **жёсткие ограничения** и разметку.
* **Обучаемый слой (L1)** — нейросетевой *санскритский базовый LM* (Transformer), который потребляет токены **вместе** с морфо‑грамм. факторами L0.
* **Интероперабельные слои (L2+)** — адаптеры/проекции к другим языкам: выравнивание через словарные и синтаксические ресурсы (IndoWordNet/Princeton WordNet, UD‑деревья, параллельные тексты), а также MT‑модели для Индийских языков (например, IndicTrans2). ([universaldependencies.org][2])

### Практический контракт в репозитории (SPIR v0.5.0)

В текущей реализации L0 в репозитории `ollama-mcp-langgraph-lab` целевой контракт теперь такой:

1. `syntax.paninian_edges` — карáка-ребра `{head, dep, role}`.
2. `syntax.ud.basic_edges` — базовое UD-дерево.
3. `syntax.ud.enhanced_edges` + `syntax.ud.empty_nodes` — enhanced слой (UD-compatible empty nodes `i.j` + DEPS).
4. `syntax.clauses` + `syntax.discourse_links` — межклаузные связи.
5. `semantics.kag` — Event+Deontic граф с provenance.
6. `token_span` в `syntax.clauses` — half-open: `[start, end)`.

Параметры окружения для управляемости:

1. `SYNTAX_BACKEND=rules|hyderabad|none`
2. `HYD_PARSER_URL` / `HYD_PARSER_CMD`
3. `KARAKA_UD_MAP_PATH`
4. `UD_HEAD_RULES_PATH`
5. `SYNTAX_OVERRIDES_PATH`
6. `ud_mode=head_rules|projected|none`

---

## Данные и инструменты: «из чего варим суп»

**Корпуса санскрита (классика):**

* **Bhagavad‑gītā** (текст по критическому изданию BORI в GRETIL). ([gretil.sub.uni-goettingen.de][3])
* **Śrīmad‑Bhāgavatam (Bhāgavata Purāṇa)** (книги/skandha в GRETIL). ([gretil.sub.uni-goettingen.de][4])
* **Mahābhārata** (электронные книги/главы). ([gretil.sub.uni-goettingen.de][5])
* Для широты жанров — **DCS (Digital Corpus of Sanskrit)**: лемматизированный **sandhi‑split** корпус с морф. и лексической разметкой. Идеален как «серебряная» разметка для пре‑тренировки. ([sanskrit-linguistics.org][6])
* Дополнительно: **SARIT** (TEI‑размеченные издания) для отслеживаемых источников. ([tei-c.org][7])

**Символические инструменты L0:**

* **Sanskrit Heritage Engine** (Huet, Inria): сегментация, сандхи‑сплиттер, морфоанализатор, первоначальный парсинг. ([sanskrit.inria.fr][8])
* **Констрейнт‑парсер Університета Хайдарабада (Amba Kulkarni)** на паниниевских зависимостях (карáк). Основа для извлечения «карáка‑графов». ([sanskrit.uohyd.ac.in][9])

**Лексикон/семантика:**

* **Monier‑Williams** (Кёльн): открытый санскрит‑английский словарь, с поддержкой IAST/SLP1. Удобен для лемматизации/семантических якорей. ([sanskrit-lexicon.uni-koeln.de][10])
* **Sanskrit WordNet / IndoWordNet** (CFILT, IIT‑Bombay): семантические синсеты, мост к хинди/другим инд. языкам и далее к Princeton WordNet/английскому. ([cfilt.iitb.ac.in][11])

**Нормализация и транслитерация:**

* **Nisaba** (Google Research): FST‑библиотека для унификации Брахмийских письменностей (визуальная/Unicode‑нормализация, обратимая транслитерация). Отлично решает «конфузаблы» Деванагари. ([GitHub][12])

**Кросс‑языковой слой (MT):**

* **IndicTrans2** (AI4Bharat): открытая высококач. мультиязычная MT для 22 индийских языков; годится для выравнивания санскрит↔инд. языки/английский и для дообучения адаптеров. ([arXiv][13])

---

## Архитектура по слоям

### L0 — символический «скелет» санскрита

1. **Скрипт и нормализация.** Один стандарт (Деванагари), Unicode **NFC** + визуальная норм. (Nisaba), запрет нулевой ширины и «нестандартных» комбинируемых знаков. ([GitHub][12])
2. **Сегментация/сандхи/самасы.** Насильно «распаковываем» слова (padaccheda), фиксируем границы sandhi и составные (tatpuruṣa, bahuvrīhi, dvandva…). Используем Heritage Engine как генератор кандидатов + ретри‑ранжер. ([sanskrit.inria.fr][8])
3. **Морфология.** Для каждой леммы: падеж/число/род, лáкара/пуруша/наклонение и др.
4. **Синтаксис.** Строим **карáка‑граф** (kartṛ/karman/karaṇa/saṃpradāna/apādāna/adhikaraṇa…) на базе констрейнт‑парсера (Hyderabad) или собственных правил. ([sanskrit.uohyd.ac.in][9])
5. **Маппинг в UD.** Сохраняем параллельно стандартные **UD‑релэйшны** для совместимости (nsubj/obj/obl:instr…) и экспортируем в формат UD; это мост к многим языкам. ([ACL Anthology][14])

> Результат L0: для каждого стиха/предложения — **(а)** нормализованный текст, **(б)** токены и их морфо‑теги, **(в)** карáка‑граф и **(г)** UD‑дерево. Это и будет «нулевой слой» — *жёсткий приор* и богатая разметка для следующего слоя.

### L1 — санскритский базовый Transformer (нейросетевой)

* **Токенизация.** SentencePiece на Деванагари *с учётом* границ sandhi и меток морфем (factored embeddings): `E(token) + E(morph) + E(sandhi_boundary) + E(lemma)`.
* **Цель обучения.** Авторегрессия (next‑token) **+ многозадачность**: предсказать морфо‑теги, точки сандхи, тип самасы, карáку для зависимостей (aux‑головы). Это «пришивает» грамматику к представлениям.
* **Источники.** DCS как полуразмеченное «серебро»; Heritage/SARIT для генерации/валидации; GRETIL‑тексты для покрытия Гиты/Бхагаватамы/Махабхараты. ([sanskrit-linguistics.org][6])
* **Декодирование.** *Constrained decoding*: запрещаем последовательности, противоречащие L0 (например, несогласование vibhakti/пуруша/числа). Это реализуемо через FST‑решётку/penalty‑mask поверх логитов.

### L2+ — интероперабельность с другими языками

1. **Семантический мост через WordNet.** Линкуем санскритские леммы/синсеты из **Sanskrit WordNet/IndoWordNet** с хинди и англ. синсетами — получаем «интерлингву» для смысловой устойчивости. ([cfilt.iitb.ac.in][11])
2. **UD‑совместимость.** Поскольку санскритские деревья у нас есть и в UD, мы можем совместно обучать парсинг/понимание с UD‑корпусами других языков. (В UD уже есть **Sanskrit‑UFAL** и **Sanskrit‑Vedic**, пусть и небольшие.) ([universaldependencies.org][2])
3. **MT‑адаптеры.** Для индийских языков и англ. — ставим **адаптер‑слои** и дообучаем на параллельных корпусах через **IndicTrans2** (как студент/teacher‑forcing), добиваясь хорошей передачи смысла без потери карáк‑структуры. ([arXiv][13])
4. **Кросс‑скриптовая устойчивость.** Для латиницы/IAST — транслитерация туда‑обратно (Nisaba/IndicNLP), чтобы модель была устойчива к вводу не в Деванагари. ([GitHub][12])

---

## Конкретный pipeline (пошагово)

1. **Сборка корпуса.**

   * GRETIL: Bhagavad‑gītā/Śrīmad‑Bhāgavatam/Mahābhārata. ([gretil.sub.uni-goettingen.de][3])
   * DCS и SARIT для широты жанров и «паспортизации» текстов. ([sanskrit-linguistics.org][6])
2. **Нормализация.** Nisaba: визуальная нормализация + NFC; отладка «токсичных» последовательностей Юникода. ([ACL Anthology][15])
3. **Авто‑анализ L0.** Heritage Engine → все возможные сегментации/теги; затем ранжирование (минимум нарушений правил Панини, вероятности из LM). ([sanskrit.inria.fr][8])
4. **Голдинг.** Где есть «золото» (размеченные DCS/UD куски) — используем для валидации и ранней остановки. ([sanskrit-linguistics.org][6])
5. **Обучение L1.**

   * Многозадачно: `L = L_NTP + λ1·L_morph + λ2·L_sandhi + λ3·L_karaka + λ4·L_UD`.
   * Токенизация SentencePiece; при желании — byte‑level (в духе ByT5) для ICU‑устойчивости. ([ResearchGate][16])
6. **Constrained decoding.** Слои ограничений: (а) морфосогласование, (б) допустимые sandhi, (в) валидность самас.
7. **Интероперабельность.**

   * Выравнивание лексем по **Sanskrit/IndoWordNet**;
   * MT‑адаптеры на **IndicTrans2**: санскрит↔хинди/англ/др. инд. языки;
   * Маппинг карáк → UD‑ролей для универсального обмена синтаксисом. ([cfilt.iitb.ac.in][11])

---

## Мини‑пример: что хранит «нулевой слой»

Возьмём *BhG 2.47* («karmaṇy evādhikāras te…»). L0 хранит:

* токены с padaccheda и sandhi‑границами;
* морфологию (например, **adhikāra‑s**: nom.sg, m.; **karmaṇi**: loc.sg, n.);
* карáки: `kartṛ(‘te’, 2sg)`, `adhikaraṇa(‘karmaṇi’)` и т.д.;
* UD‑дерево: `nsubj`, `obl:loc`, `advmod` …
  При генерации L1 модель **не сможет** выпустить сочетания, нарушающие согласование (это заслуга constrained decoding).

---

## Проверка качества (метрики)

* **Сандхи/самасы:** точность сплита/типов. (Бенчмарки на DCS/Heritage.) ([sanskrit-linguistics.org][6])
* **Морфология:** теггинг/лемматизация (аккуратность по DCS). ([sanskrit-linguistics.org][6])
* **Синтаксис:** UAS/LAS для UD‑деревьев (UFAL, Vedic). ([universaldependencies.org][2])
* **Семантика/перевод:** точность переноса карáк через мост (санскрит→хинди/англ) + BLEU/COMET с адаптерами IndicTrans2. ([arXiv][13])

---

## Почему такой дизайн работает

* Санскрит «любит» символику: свободный порядок слов, богатая морфология и сандхи **сильно выигрывают** от L0‑ограничений (иначе нейросеть «смазывает» редкие формы). Инструменты Heritage/Hyderabad дают готовые кирпичи. ([sanskrit.inria.fr][8])
* UD‑совместимость и WordNet делают санскрит **узлом интерлингвы**: мы можем проигрывать один и тот же «карáка‑граф» через разные языки без потери роли. ([ACL Anthology][14])
* Современные трансформеры (а не Марковские цепочки) хорошо впитывают такие *факторы* как дополнительные эмбеддинги/многозадачность. ([arXiv][1])

---

## Риски/подводные камни

* **Лицензии и версии текстов.** GRETIL/SARIT — агрегаторы; важно фиксировать издание (например, BORI для Гиты) и их условия. ([gretil.sub.uni-goettingen.de][3])
* **Юникод‑хаос в Деванагари.** Без визуальной нормализации (Nisaba) получите «конфузаблы» и разъезды токенайзера. ([ACL Anthology][15])
* **Малые treebank’и.** UD‑корпуса санскрита невелики; компенсируем обучение «карáк‑голов» на полуразметке + перенос с родственных языков через UD/WordNet/MT. ([universaldependencies.org][2])

---

## Что можно собрать «быстро» как PoC

1. Взять **Bhagavad‑gītā** (GRETIL) и **DCS** как тренировочную пару «сырой текст ↔ разметка». ([gretil.sub.uni-goettingen.de][3])
2. Прогнать тексты через **Heritage** (сегментация/морфо‑кандидаты) и собрать «серебряный» датасет. ([sanskrit.inria.fr][8])
3. Обучить лёгкий декодер‑трансформер (100–300M) с факторными эмбеддингами и **penalty‑mask** из L0.
4. Добавить **адаптер** для хинди/английского с помощью **IndicTrans2** (либо как teacher при генерации, либо как помощь в словесном выравнивании). ([arXiv][13])

---

### Полезные опорные ссылки ещё раз

* **DCS** — sandhi‑split корпус с морфо/лекс. анализом. ([sanskrit-linguistics.org][6])
* **Sanskrit Heritage Engine** — сегментация/морфо/парсинг. ([sanskrit.inria.fr][8])
* **GRETIL** — машина‑читаемые тексты (в т.ч. *Bhagavad‑gītā*, *Bhāgavata Purāṇa*, *Mahābhārata*). ([gretil.sub.uni-goettingen.de][3])
* **UD (Sanskrit‑UFAL, Sanskrit‑Vedic)** — деревья для совместимости. ([universaldependencies.org][2])
* **IndoWordNet / Sanskrit WordNet** — семантический мост. ([cfilt.iitb.ac.in][11])
* **Nisaba** — нормализация/транслитерация индийских письменностей. ([GitHub][12])
* **IndicTrans2** — мультиязычная MT для 22 индийских языков. ([arXiv][13])

---

Если хотите, я могу **набросать схему данных для L0** (JSON для токена/морф‑тегов/карáк/UD) и показать, как включить такие факторы в вход модели и в маскирование логитов при декодировании.

[1]: https://arxiv.org/abs/1706.03762?utm_source=chatgpt.com "Attention Is All You Need"
[2]: https://universaldependencies.org/sa/index.html?utm_source=chatgpt.com "UD for Sanskrit"
[3]: https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/2_epic/mbh/ext/bhgce__u.htm?utm_source=chatgpt.com "Bhagavadgita"
[4]: https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/bhagp/bhp_01u.htm?utm_source=chatgpt.com "Bhagavata-Purana 1"
[5]: https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/2_epic/mbh/sas/mahabharata.htm?utm_source=chatgpt.com "Mahābhārata online"
[6]: https://www.sanskrit-linguistics.org/dcs/?utm_source=chatgpt.com "DCS - Digital Corpus of Sanskrit"
[7]: https://tei-c.org/activities/projects/sarit/?utm_source=chatgpt.com "SARIT"
[8]: https://sanskrit.inria.fr/?utm_source=chatgpt.com "The Sanskrit Heritage Site - Inria"
[9]: https://sanskrit.uohyd.ac.in/faculty/amba/PUBLICATIONS/papers/constraint_parser_revised.pdf?utm_source=chatgpt.com "Designing a Constraint Based Parser for Sanskrit"
[10]: https://www.sanskrit-lexicon.uni-koeln.de/scans/MWScan/2020/web/webtc2/index.php?utm_source=chatgpt.com "Monier-Williams Sanskrit Dictionary 1899 Advanced"
[11]: https://www.cfilt.iitb.ac.in/wordnet/webswn/english_version.php?utm_source=chatgpt.com "संस्कृतशब्दबन्धः Sanskrit WordNet - CFILT - IIT Bombay"
[12]: https://github.com/google-research/nisaba?utm_source=chatgpt.com "google-research/nisaba: Finite-state script normalization ..."
[13]: https://arxiv.org/pdf/2305.16307?utm_source=chatgpt.com "IndicTrans2: Towards High-Quality and Accessible ..."
[14]: https://aclanthology.org/I08-2099.pdf?utm_source=chatgpt.com "Dependency Annotation Scheme for Indian Languages"
[15]: https://aclanthology.org/2022.lrec-1.692.pdf?utm_source=chatgpt.com "Extensions to Brahmic script processing within the Nisaba ..."
[16]: https://www.researchgate.net/publication/397068248_Leveraging_Paninian_Grammar_and_Neural_Models_for_Morphologically_Rich_Sanskrit_NLP?utm_source=chatgpt.com "(PDF) Leveraging Pāṇinian Grammar and Neural Models ..."
