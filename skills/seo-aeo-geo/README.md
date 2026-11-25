# seo-aeo-geo

Агентный навык для органического SEO, оптимизации под прямые ответы (AEO) и видимости в генеративном поиске (GEO). Аудирует сайт и контент, помогает подготовить правки и черновики, проверяет представление бренда в ответах и сравнивает замеры видимости.

## Быстрый старт

Подключите папку навыка в своей оболочке агента или укажите агенту на [SKILL.md](SKILL.md). Если оболочка регистрирует slash-команды, используйте один из двух вызовов.

```text
/seo-aeo-geo audit https://example.com
/aeo audit https://example.com
```

Оба вызова используют форму `<маршрут> <объект>`. Совместимый вызов `/aeo` описан в [commands/aeo.md](../../commands/aeo.md). В обычном текстовом запросе достаточно указать задачу и объект, например «Проведи SEO, AEO и GEO-аудит example.com». Можно указать рынок, язык, целевые поисковые системы и AI-платформы.

## Все маршруты

Префикс `/seo-aeo-geo` в примерах можно заменить на `/aeo`, если оболочка поддерживает команду совместимости.

| Маршрут | Пример | Что возвращает |
| --- | --- | --- |
| [audit](references/audit.md) | `/seo-aeo-geo audit https://example.com` | Выборку, охват проверок и приоритетный список задач с доказательствами и проверкой результата. |
| [technical](references/technical.md) | `/seo-aeo-geo technical https://example.com/pricing` | Наблюдения по HTTP, robots.txt, доступу ботов, рендерингу, canonical, sitemap и индексации. |
| [content](references/content.md) | `/seo-aeo-geo content Проверь статью https://example.com/guide и подготовь черновик правок` | Разбор интента, заголовков, структуры ответа и утверждений. По прямой просьбе готовит полный черновик для ревью. |
| [entity](references/entity.md) | `/seo-aeo-geo entity Acme, https://example.com` | Карту официальных фактов о бренде и расхождения в их воспроизведении. |
| [offpage](references/offpage.md) | `/seo-aeo-geo offpage Acme в категории CRM` | Карту независимых источников и пробелы во внешней представленности. |
| [visibility](references/visibility.md) | `/seo-aeo-geo visibility Acme в ChatGPT по приложенным ответам` | Портфель запросов и журнал наблюдений. Считает цитаты, упоминания и рекомендации за и против отдельно. |
| [measure](references/measure.md) | `/seo-aeo-geo measure Приложенные выгрузки поисковой и веб-аналитики` | Разбор поисковых метрик, рефералов, атрибуции и результатов экспериментов. |
| [local](references/local.md) | `/seo-aeo-geo local Acme, адрес и страница филиала` | Наблюдения по карточкам бизнеса, отзывам и страницам локаций. |
| [ecommerce](references/ecommerce.md) | `/seo-aeo-geo ecommerce https://example.com/catalog и приложенный фид` | Проверку категорий, фильтров и согласованности товарных данных в фиде, карточках и разметке. |
| [refresh](references/refresh.md) | `/seo-aeo-geo refresh https://example.com/guide и выгрузка Search Console` | Диагноз падения трафика и матрицу действий Keep/Fix/Remove/Add. |
| [plan](references/plan.md) | `/seo-aeo-geo plan Запуск сайта Acme на русскоязычном рынке` | План работ по спросу, техническому фундаменту, контенту и замерам. |

Маршрут `content` принимает текст, HTML или URL и возвращает находки и точечные правки фрагментами. Полный текст статьи пишет соседний навык [seo-article-writer](../seo-article-writer/SKILL.md): `content` передаёт ему находки и реестр утверждений. Порядок публикации согласованного текста описан в [SKILL.md](SKILL.md#behaviour).

## Python CLI

Команды запускаются из корня репозитория. Утилиты используют стандартную библиотеку Python 3. У каждой команды есть `-h` и `--help`.

### `site_audit.py`

Проверяет одну страницу или выборку сайта. По умолчанию бюджет выборки составляет 20 URL, по два URL на шаблон. Опция `--score` рассчитывает ориентир `tech-v1` по правилам [технического справочника](references/technical.md).

```bash
python3 scripts/site_audit.py https://example.com/pricing
python3 scripts/site_audit.py --site https://example.com --score --out snapshot.json
python3 scripts/site_audit.py https://example.com --robots-file robots.txt --no-fetch --json
```

| Параметр | Назначение |
| --- | --- |
| `url`, `--site SITE` | Режим одной страницы или выборки сайта. |
| `--robots-file FILE`, `--no-fetch` | Локальный robots.txt и пропуск запросов к страницам. Для работы без сети используйте обе опции вместе. |
| `--limit N`, `--per-template N`, `--sample-file FILE` | Бюджет, предел на шаблон и файл URL по одному адресу в строке для повторного замера. |
| `--search-agent AGENT`, `--agents A,B` | Агент поисковой проверки (по умолчанию `Googlebot`) и список агентов для проверки пар URL и агента (по умолчанию весь реестр). |
| `--probe {none,home,sample}` | Диагностическая UA-проба. По умолчанию `home`, для главной или переданного URL. |
| `--exclude URL::причина`, `--intended-canonical URL::причина` | Намеренное исключение URL из целевого набора и подтверждённый canonical на другой адрес. Опции можно повторять. |
| `--render URL::файл` | HTML после рендеринга для проверки основного содержимого. Опцию можно повторять. |
| `--max-depth N`, `--delay SEC` | Глубина проверки внутренних переходов (по умолчанию 2) и пауза между запросами (от 1 секунды, по умолчанию 1). |
| `--score`, `--json`, `--out FILE` | Оценка `tech-v1`, JSON в stdout и запись JSON в файл. |

### `page_audit.py`

Проверяет исходный HTML одной страницы и возвращает наблюдения и эвристики. Аргумент `url` загружает страницу, `--file FILE` читает локальный HTML. `--brand BRAND` задаёт бренд для проверки, `--ua UA` задаёт User-Agent сетевого запроса (по умолчанию типичный клиент), `--json` включает JSON.

```bash
python3 scripts/page_audit.py --file page.html --brand Acme --json
```

### `log_bots.py`

Читает один или несколько файлов серверного лога, включая `.gz`, или stdin через `-`. `--top N` задаёт размер списка популярных путей (по умолчанию 10), `--json` включает JSON, `--verify-dns` включает обратную и прямую DNS-проверку для ботов с известными суффиксами.

```bash
python3 scripts/log_bots.py access.log access.log.1.gz --top 20 --json
```

### `visibility_tracker.py`

Ведёт журнал JSONL. Перед добавлением наблюдений создайте журнал через `init`. Используйте `add` для реально полученного ответа, `report` для сводки или сравнения периодов и `import` для прежних данных. Импортированные записи требуют подтверждения перед включением в метрики. [Справочник журнала](references/visibility.md) и [правила миграции](scripts/MIGRATION.md).

| Подкоманда | Обязательные параметры | Дополнительные параметры |
| --- | --- | --- |
| `init` | `--path`, `--brand` | |
| `add` | `--path`, `--brand`, `--surface`, `--scenario-id`, `--scenario-version`, `--prompt-id`, `--prompt-version`, `--prompt-text`, `--completed` | `--turn` (по умолчанию 1), `--run-id`, `--session-id`, `--branch`, `--cohort`, `--stage`, `--language`, `--geo`, `--mode`, `--time`, `--history-ref`, `--answer-ref`, `--attitude`, `--classification-version` (по умолчанию 1), `--shortlisted`, `--citation`, `--mention`, `--recommend-for`, `--recommend-against`, `--basis` (можно повторять), `--provenance {observed,demo}` (по умолчанию `observed`). |
| `report` | `--path` | `--since YYYY-MM-DD`, `--until YYYY-MM-DD`, `--period-a YYYY-MM-DD:YYYY-MM-DD`, `--period-b YYYY-MM-DD:YYYY-MM-DD`, `--json`. Для сравнения укажите оба периода. |
| `import` | `--path`, `--source` | `--format {auto,csv,citation-json}` (по умолчанию `auto`). |

Для `--completed` передайте `true` или `false`. Флаги цитаты, упоминания, рекомендации за и против принимают `true`, `false` или `unknown` (по умолчанию `unknown`). Основание рекомендации передаётся как `--basis 'for|условие|выдержка|позиция'` или с направлением `against`. Позиция может быть пустой.

```bash
python3 scripts/visibility_tracker.py init --path journal.jsonl --brand Acme
python3 scripts/visibility_tracker.py add --path journal.jsonl --brand Acme \
  --surface chatgpt --mode search --scenario-id crm --scenario-version 1 \
  --prompt-id p1 --prompt-version 1 --prompt-text "Как выбрать CRM?" \
  --completed true --citation true --mention true --provenance demo
python3 scripts/visibility_tracker.py report --path journal.jsonl --json
python3 scripts/visibility_tracker.py import --path journal.jsonl --source old.csv --format csv
```

Запись из примера помечена как демонстрационная и исключается из метрик. Для реального замера используйте полученный ответ и его контекст.

## Что вошло после аудита и Arena

Bain-аудит сопоставил четыре навыка по покрытию SEO и AEO/GEO, практичности, доказательности, структуре и объёму инструкций. В Arena 16 участников независимо предложили архитектуру единого навыка. Победитель прошёл четыре раунда критики, доработок и судейской оценки. В финальном матче он получил **86 против 79,5**, а в отдельном сравнении с исходным `aeo-skill` как базовым вариантом - **79,5 против 40**. Это оценки спецификации по рубрике турнира.

| Исходник | Что вошло в единый навык |
| --- | --- |
| [aeo-skill](https://github.com/Asmadey/skills/tree/eb4a46521005c2ab0ff93ee8b3934ac378ddf052/skills/marketing/aeo-skill) | Модульная архитектура с 11 маршрутами, справочники по локальному поиску и ecommerce, реестр тезисов и источников. |
| [ai-seo](https://github.com/Asmadey/skills/tree/eb4a46521005c2ab0ff93ee8b3934ac378ddf052/skills/marketing/ai-seo) | Разделение ботов по назначению, портфель запросов, журнал утверждений о бренде и подход к атрибуции. |
| [geo-aeo-audit](https://github.com/Asmadey/skills/tree/eb4a46521005c2ab0ff93ee8b3934ac378ddf052/skills/marketing/geo-aeo-audit) | Технический краулер, переработанный разбор robots.txt, бюджет выборки и подсчёт оценки с учётом охвата. |
| [aeo-geo-skill-ru](https://github.com/Asmadey/skills/tree/eb4a46521005c2ab0ff93ee8b3934ac378ddf052/skills/marketing/aeo-geo-skill-ru) | План запуска с нуля, матрица Keep/Fix/Remove/Add, паттерны извлекаемого контента и учёт цитирования. |

В техническом аудите проба с User-Agent бота служит диагностикой. Подтверждённую блокировку реального бота фиксируют по проверенным данным. При сравнении видимости используются сопоставимые запросы и условия замера. [Правила технического аудита](references/technical.md) и [правила сравнения замеров](references/visibility.md).

Статусы платформ и их ограничения хранятся в [platforms.md](references/platforms.md). Спорные тезисы, источники и статус их проверки перечислены в [evidence.md](references/evidence.md).

## Проверка и предыдущая версия

```bash
(cd scripts && python3 -m unittest discover -s tests -v)
```

Поведенческие сценарии для агента находятся в [evals/evals.json](evals/evals.json).

Англоязычный навык с Playbook V2 доступен в [legacy/aeo](../../legacy/aeo/README.md). История его версий находится в [CHANGELOG.md](../../CHANGELOG.md).
