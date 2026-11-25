# seo-aeo-geo

Навык для органического SEO, AEO и GEO. Точка входа и таблица маршрутов находятся в [SKILL.md](SKILL.md).

Прежний англоязычный навык с Playbook V2 доступен в [legacy/aeo](legacy/aeo/README.md). Его история версий находится в [CHANGELOG.md](CHANGELOG.md).

Запасной вызов: `/seo-aeo-geo <маршрут> <объект>` — если `/aeo` из `commands/aeo.md` не работает в оболочке.

## Структура

- `SKILL.md` — маршрутизация, доказательства, проверки, формат выдачи.
- `references/` — по справочнику на маршрут (`<маршрут>.md`), плюс `platforms.md` (карточки поверхностей) и `evidence.md` (реестр тезисов и источников).
- `scripts/` — утилиты проверки доступа, страниц, логов и журнала видимости; `scripts/tests/` — fixtures и тесты.
- `commands/aeo.md` — пересылка старого вызова `/aeo` в навык, без логики.
- `evals/evals.json` — eval-кейсы и регрессии, включая перенесённые сюжеты `ai-seo`.

## Откуда собран

- `aeo-geo-skill-ru` — `skills/public/marketing/aeo-geo-skill-ru`
- `aeo-skill` — GitHub `Asmadey/skills`, `skills/marketing/aeo-skill`
- `ai-seo` — `skills/public/marketing/ai-seo`
- `geo-aeo-audit` — GitHub `Asmadey/skills`, `skills/marketing/geo-aeo-audit`

## Тесты скриптов

```bash
cd scripts && python3 -m unittest discover -s tests -v
```

## Открытые вопросы

- Режим переписывания текста: по умолчанию B («правки и черновик в ответе»); при выборе A («только находки и правки фрагментами») меняются справочник content и eval 5.
- Целевой рынок: по умолчанию глобальный и RU-first равноправны; выбор приоритета не сделан.
